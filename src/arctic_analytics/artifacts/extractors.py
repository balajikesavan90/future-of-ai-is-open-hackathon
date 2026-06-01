"""Extract artifact-friendly records from traces and context metadata."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from arctic_analytics.artifacts.models import ResearchSession


def json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(key): json_safe(val) for key, val in value.items()}
        if isinstance(value, (list, tuple)):
            return [json_safe(item) for item in value]
        return str(value)


def extract_prompts(session: ResearchSession) -> dict[str, Any]:
    trace = session.analysis_trace.data or {}
    messages = trace.get("messages", [])
    user_prompts = []
    assistant_messages = []

    for message in messages:
        if not isinstance(message, dict) or message.get("type") != "message":
            continue
        text = _message_text(message)
        if message.get("role") == "user" and text:
            user_prompts.append(text)
        elif message.get("role") == "assistant" and text:
            assistant_messages.append(text)

    return {
        "primary_prompt": session.prompt or trace.get("prompt_str"),
        "system_message": trace.get("system_message"),
        "user_prompts": user_prompts,
        "assistant_messages": assistant_messages,
        "note": "Prompts are exported for review. Model outputs may vary across runs and model versions.",
    }


def extract_generated_code(trace: dict[str, Any] | None) -> list[dict[str, str]]:
    if not trace:
        return []

    snippets = []
    for index, tool_call in enumerate(trace.get("tool_calls", []), start=1):
        if not isinstance(tool_call, dict):
            continue
        arguments = _parse_arguments(tool_call.get("arguments") or tool_call.get("function", {}).get("arguments"))
        code = arguments.get("python_expression") or arguments.get("function_definition")
        if not code:
            continue
        tool_name = str(tool_call.get("name") or tool_call.get("function", {}).get("name") or "tool")
        snippets.append(
            {
                "filename": f"{index:03d}_{_safe_name(tool_name)}.py",
                "tool_name": tool_name,
                "reason": str(arguments.get("reason", "")),
                "code": str(code),
            }
        )
    return snippets


def write_outputs_and_figures(
    trace: dict[str, Any] | None,
    outputs_dir: Path,
    figures_dir: Path,
    raw_outputs: list[Any] | None = None,
) -> list[Path]:
    written = []
    outputs_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    if not trace:
        path = outputs_dir / "outputs_unavailable.md"
        path.write_text("No analysis trace was provided, so tool outputs are unavailable.\n")
        return [path]

    outputs = trace.get("outputs", [])
    figure_outputs = raw_outputs or outputs

    written_figure_indexes = set()
    for index, output in enumerate(figure_outputs, start=1):
        payload = output.get("output") if isinstance(output, dict) else output
        image_path = _write_image_payload(payload, figures_dir, index)
        if image_path is not None:
            written.append(image_path)
            written_figure_indexes.add(index)

    for index, output in enumerate(outputs, start=1):
        if index in written_figure_indexes:
            continue

        path = outputs_dir / f"{index:03d}_output.json"
        path.write_text(json.dumps(json_safe(output), indent=2, default=str) + "\n")
        written.append(path)

    if not outputs:
        path = outputs_dir / "outputs_empty.md"
        path.write_text("The analysis trace did not contain exported tool outputs.\n")
        written.append(path)

    return written


def final_answer_markdown(trace: dict[str, Any] | None) -> str:
    if not trace:
        return "No analysis trace was provided, so no final answer is available.\n"

    messages = trace.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("type") == "message" and message.get("role") == "assistant":
            text = _message_text(message)
            if text:
                return text.strip() + "\n"
    return "No assistant final answer was found in the trace.\n"


def _message_text(message: dict[str, Any]) -> str | None:
    content = message.get("content")
    if not isinstance(content, list) or not content:
        return None
    texts = [
        str(item["text"])
        for item in content
        if isinstance(item, dict) and item.get("text")
    ]
    return "\n".join(texts) if texts else None


def _parse_arguments(raw_arguments: Any) -> dict[str, Any]:
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not isinstance(raw_arguments, str):
        return {}
    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_name(name: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in name).strip("_") or "tool"


def _write_image_payload(payload: Any, figures_dir: Path, index: int) -> Path | None:
    if isinstance(payload, str) and payload.startswith("data:image/") and ";base64," in payload:
        header, _, encoded = payload.partition(",")
        extension = header.split("/")[1].split(";")[0] or "png"
        path = figures_dir / f"{index:03d}_figure.{extension}"
        path.write_bytes(base64.b64decode(encoded))
        return path

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                path = _write_image_payload(item.get("image_url"), figures_dir, index)
                if path is not None:
                    return path

    return None
