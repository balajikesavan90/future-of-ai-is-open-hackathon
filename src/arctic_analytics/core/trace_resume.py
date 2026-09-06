"""Validation and reconstruction helpers for resumable analysis traces."""

from __future__ import annotations

from dataclasses import dataclass
import base64
import binascii
import io
import json
import math
from typing import Any

import pandas as pd
from jsonschema import Draft202012Validator
from PIL import Image, UnidentifiedImageError


MAX_TRACE_BYTES = 10 * 1024 * 1024
SUPPORTED_TRACE_VERSIONS = {"0.3.0"}
IMPORT_TRACE_SCHEMA = {
    "type": "object",
    "required": [
        "trace_schema_version", "package_version", "timestamp", "session_id", "cost",
        "context_window_usage", "system_message", "prompt_str", "messages", "events", "tool_calls",
        "outputs", "dataset_metadata", "errors", "limitations",
    ],
    "properties": {
        "trace_schema_version": {"enum": sorted(SUPPORTED_TRACE_VERSIONS)},
        "package_version": {"type": "string"},
        "timestamp": {"type": "string"},
        "session_id": {"type": ["string", "null"]},
        "cost": {"type": ["number", "null"]},
        "context_window_usage": {"type": ["number", "null"]},
        # Exported values are normally strings or null; long strings are
        # replaced with JSON-safe truncation descriptors.
        "system_message": {"type": ["string", "object", "null"]},
        "prompt_str": {"type": ["string", "object", "null"]},
        "researcher_notes": {"type": "string"},
        "messages": {"type": "array"},
        "events": {"type": "array"},
        "tool_calls": {"type": "array"},
        "outputs": {"type": "array"},
        "dataset_metadata": {"type": "object"},
        "errors": {"type": "array"},
        "limitations": {"type": "array"},
        "resume": {
            "type": "object",
            "required": ["resume_schema_version", "source", "datasets"],
            "properties": {
                "resume_schema_version": {"const": "1.0"},
                "source": {"const": "uploader"},
                "datasets": {"type": "array"},
                "context_window_usage": {"type": "number"},
                "context_window_tokens": {"type": "integer", "minimum": 0},
                "researcher_notes": {"type": "string"},
            },
        },
    },
}


class TraceResumeError(ValueError):
    """Raised when an uploaded trace cannot safely be resumed."""


@dataclass
class ResumePreparation:
    vetted_files: dict[str, dict[str, Any]]


def load_analysis_trace(raw_bytes: bytes) -> dict[str, Any]:
    """Decode and minimally validate a trace before any session state changes."""
    if len(raw_bytes) > MAX_TRACE_BYTES:
        raise TraceResumeError("Trace files must be 10 MiB or smaller.")
    try:
        trace = json.loads(raw_bytes.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise TraceResumeError("Upload a valid UTF-8 Arctic Analytics trace JSON file.") from exc

    if not isinstance(trace, dict):
        raise TraceResumeError("The trace JSON must contain an object.")
    if _contains_nonfinite_number(trace):
        raise TraceResumeError("The trace JSON must not contain non-finite numbers.")
    errors = sorted(Draft202012Validator(IMPORT_TRACE_SCHEMA).iter_errors(trace), key=lambda error: list(error.path))
    if errors:
        raise TraceResumeError(f"The trace does not match the supported import format: {errors[0].message}")
    return trace


def _reject_json_constant(value: str) -> None:
    """Reject JSON extensions such as NaN and Infinity."""
    raise ValueError(f"Non-finite JSON constant: {value}")


def _contains_nonfinite_number(value: Any) -> bool:
    """Catch non-finite floats produced by numeric overflow during decoding."""
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(_contains_nonfinite_number(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_nonfinite_number(item) for item in value)
    return False


def prepare_resume(trace: dict[str, Any], uploaded_vetted_files: dict[str, dict[str, Any]]) -> ResumePreparation:
    """Match compatible CSVs to a trace and restore its reviewable metadata.

    Resume deliberately accepts refreshed data: datasets are identified by their
    source filename and ordered columns, not by a content hash. Historical
    conversation and outputs remain available as context, but callers must warn
    users to re-run findings that may have changed with the refreshed rows.
    """
    if not uploaded_vetted_files:
        raise TraceResumeError("Upload the CSV files used by this analysis.")

    resume = trace.get("resume")
    if not isinstance(resume, dict):
        raise TraceResumeError("The trace requires a resume manifest.")
    if resume.get("resume_schema_version") != "1.0":
        raise TraceResumeError("The trace resume manifest must use schema version 1.0.")
    if resume.get("source") != "uploader":
        raise TraceResumeError("The trace resume manifest must declare uploader as its source.")
    datasets = resume.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise TraceResumeError("The trace resume manifest has no datasets.")
    mapping = _match_manifest_datasets(datasets, uploaded_vetted_files)

    metadata = trace.get("dataset_metadata", {})
    restored: dict[str, dict[str, Any]] = {}
    for trace_key, uploaded_key in mapping.items():
        file_info = dict(uploaded_vetted_files[uploaded_key])
        saved = metadata.get(trace_key, {})
        if isinstance(saved, dict):
            _restore_metadata(file_info, saved)
        restored[trace_key] = file_info
    return ResumePreparation(vetted_files=restored)


def messages_for_resume(trace: dict[str, Any]) -> list[Any]:
    """Return API-safe history, preferring the full-fidelity resume copy when present.

    Earlier trace exports deliberately replaced base64 chart URLs with descriptive
    objects. Those objects are useful for audit exports but invalid as Responses
    API image inputs, so convert them to a textual placeholder on import.
    """
    resume = trace.get("resume")
    if isinstance(resume, dict) and isinstance(resume.get("messages"), list):
        messages = resume["messages"]
    else:
        messages = trace.get("messages", [])
    if not _has_resumable_system_message(messages):
        return []
    # A resumed history is passed both to the UI renderer and the Responses
    # API. Keeping only valid entries can orphan tool outputs or calls, so
    # discard the complete history when any item is not a supported shape.
    if not all(_is_supported_resumed_message(message) for message in messages):
        return []
    if not _has_valid_tool_call_sequence(messages):
        return []
    return [_sanitize_resumed_message(message) for message in messages]


def replace_resumed_system_message(messages: list[Any], system_message: str) -> list[Any]:
    """Replace only restored system context while preserving the conversation."""
    return [{
        "role": "system",
        "content": [{"text": system_message, "type": "input_text"}],
        "type": "message",
    }, *messages[1:]]


def _has_resumable_system_message(messages: Any) -> bool:
    if not isinstance(messages, list) or not messages:
        return False
    system_message = messages[0]
    if not isinstance(system_message, dict):
        return False
    return _is_supported_resumed_message(system_message) and system_message.get("role") == "system"


def _is_supported_resumed_message(message: Any) -> bool:
    if not isinstance(message, dict):
        return False
    message_type = message.get("type")
    if message_type == "message":
        content = message.get("content")
        return (
            message.get("role") in {"system", "user", "assistant"}
            and _has_valid_message_content(message["role"], content)
        )
    if message_type == "reasoning":
        summary = message.get("summary")
        return isinstance(summary, list) and all(
            isinstance(item, dict) and isinstance(item.get("text"), str)
            for item in summary
        )
    if message_type == "function_call":
        return (
            _valid_call_id(message.get("call_id"))
            and isinstance(message.get("name"), str)
            and isinstance(message.get("arguments"), str)
        )
    if message_type == "function_call_output":
        return _valid_call_id(message.get("call_id")) and isinstance(message.get("output"), (str, list, dict))
    return False


def _has_valid_message_content(role: str, content: Any) -> bool:
    """Accept only the role-specific text content emitted by this application."""
    expected_type = "output_text" if role == "assistant" else "input_text"
    return (
        isinstance(content, list)
        and bool(content)
        and all(
            isinstance(item, dict)
            and item.get("type") == expected_type
            and isinstance(item.get("text"), str)
            for item in content
        )
    )


def _valid_call_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_valid_tool_call_sequence(messages: list[Any]) -> bool:
    """Ensure every tool output resolves an earlier, unique function call."""
    pending_call_ids: set[str] = set()
    seen_call_ids: set[str] = set()
    for message in messages:
        message_type = message.get("type")
        if message_type == "function_call":
            call_id = message["call_id"]
            if call_id in seen_call_ids:
                return False
            seen_call_ids.add(call_id)
            pending_call_ids.add(call_id)
        elif message_type == "function_call_output":
            call_id = message["call_id"]
            if call_id not in pending_call_ids:
                return False
            pending_call_ids.remove(call_id)
        elif pending_call_ids:
            return False
    return not pending_call_ids


def _sanitize_resumed_message(message: Any) -> Any:
    if not isinstance(message, dict):
        return message
    restored = dict(message)
    if restored.get("type") != "function_call_output":
        return restored
    output = restored.get("output")
    if isinstance(output, dict) and output.get("type") == "image_base64":
        restored["output"] = "Historical chart output is unavailable in this exported trace."
        return restored
    if not isinstance(output, list):
        return restored
    for output_item in output:
        if not isinstance(output_item, dict):
            continue
        image_url = output_item.get("image_url")
        if image_url is not None and not _is_valid_base64_image_data_url(image_url):
            restored["output"] = "Historical chart output is unavailable in this exported trace."
            break
    return restored


def _is_valid_base64_image_data_url(value: Any) -> bool:
    """Validate a supported image data URL before it is sent to Responses."""
    if not isinstance(value, str) or not value.startswith("data:"):
        return False
    header, separator, payload = value.partition(",")
    if separator != "," or not header.endswith(";base64"):
        return False
    mime_type = header.removeprefix("data:").removesuffix(";base64")
    expected_format = {
        "image/png": "PNG",
        "image/jpeg": "JPEG",
        "image/gif": "GIF",
        "image/webp": "WEBP",
    }.get(mime_type)
    if expected_format is None:
        return False
    try:
        image_bytes = base64.b64decode(payload, validate=True)
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.verify()
            return image.format == expected_format
    except (binascii.Error, UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return False


def _match_manifest_datasets(datasets: list[Any], uploaded: dict[str, dict[str, Any]]) -> dict[str, str]:
    if len(datasets) != len(uploaded):
        raise TraceResumeError("Upload exactly the CSV files recorded in this trace.")
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for item in datasets:
        if not isinstance(item, dict):
            raise TraceResumeError("The trace resume manifest contains an invalid dataset.")
        trace_key = item.get("dataset_key")
        filename = item.get("source_filename")
        columns = item.get("column_names")
        if not isinstance(trace_key, str) or not isinstance(filename, str) or not _valid_columns(columns):
            raise TraceResumeError("The trace resume manifest is incomplete.")
        candidates = [
            key for key, info in uploaded.items()
            if (
                info.get("source_filename") == filename
                and _columns_match(info, columns)
                and key not in used
            )
        ]
        if not candidates:
            raise TraceResumeError(
                f"Upload a file named '{filename}' with the same ordered columns to resume this trace."
            )
        # Intentional refreshed-data behavior: filename plus ordered columns is
        # sufficient; row values may have changed. Multiple same-named uploads
        # are consumed deterministically in manifest/upload order.
        mapping[trace_key] = candidates[0]
        used.add(candidates[0])
    if len(mapping) != len(uploaded):
        raise TraceResumeError("The uploaded CSV files do not match this trace.")
    return mapping


def _valid_columns(columns: Any) -> bool:
    return isinstance(columns, list) and all(isinstance(column, str) for column in columns)


def _columns_match(file_info: dict[str, Any], columns: list[str]) -> bool:
    return [str(column) for column in file_info.get("columns_names", [])] == columns


def _restore_metadata(file_info: dict[str, Any], saved: dict[str, Any]) -> None:
    dataset_description = saved.get("dataset_description")
    file_info["dataset_description"] = dataset_description if isinstance(dataset_description, str) else ""
    primary_key = saved.get("primary_key")
    file_info["primary_key"] = primary_key if _valid_columns(primary_key) else []
    data_types = saved.get("data_types")
    if isinstance(data_types, dict):
        file_info["data_types"] = pd.Series(
            {column: data_types.get(column, str(dtype)) for column, dtype in file_info["data_types"].items()}
        )
    data_dictionary = saved.get("data_dictionary")
    if _data_dictionary_matches_columns(data_dictionary, file_info.get("columns_names", [])):
        file_info["data_dictionary_json"] = json.dumps(data_dictionary)


def _data_dictionary_matches_columns(data_dictionary: Any, columns: Any) -> bool:
    if not isinstance(data_dictionary, (dict, list)):
        return False
    try:
        frame = (
            pd.DataFrame.from_dict(data_dictionary, orient="index")
            if isinstance(data_dictionary, dict)
            else pd.DataFrame(data_dictionary)
        )
    except (TypeError, ValueError):
        return False
    return (
        "Column Name" in frame
        and list(frame["Column Name"]) == [str(column) for column in columns]
    )
