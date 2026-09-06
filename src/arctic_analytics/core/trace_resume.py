"""Validation and reconstruction helpers for resumable analysis traces."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import pandas as pd
from jsonschema import Draft202012Validator


MAX_TRACE_BYTES = 10 * 1024 * 1024
SUPPORTED_TRACE_VERSIONS = {"0.3.0"}
IMPORT_TRACE_SCHEMA = {
    "type": "object",
    "required": [
        "trace_schema_version", "package_version", "timestamp", "session_id", "model", "cost",
        "context_window_usage", "system_message", "prompt_str", "messages", "events", "tool_calls",
        "outputs", "dataset_metadata", "errors", "limitations",
    ],
    "properties": {
        "trace_schema_version": {"enum": sorted(SUPPORTED_TRACE_VERSIONS)},
        "package_version": {"type": "string"},
        "timestamp": {"type": "string"},
        "session_id": {"type": ["string", "null"]},
        "model": {"type": ["string", "null"]},
        "cost": {"type": ["number", "null"]},
        "context_window_usage": {"type": ["number", "null"]},
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
        trace = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TraceResumeError("Upload a valid UTF-8 Arctic Analytics trace JSON file.") from exc

    if not isinstance(trace, dict):
        raise TraceResumeError("The trace JSON must contain an object.")
    errors = sorted(Draft202012Validator(IMPORT_TRACE_SCHEMA).iter_errors(trace), key=lambda error: list(error.path))
    if errors:
        raise TraceResumeError(f"The trace does not match the supported import format: {errors[0].message}")
    return trace


def prepare_resume(trace: dict[str, Any], uploaded_vetted_files: dict[str, dict[str, Any]]) -> ResumePreparation:
    """Match fresh CSV data to a trace and restore only reviewable metadata."""
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
    return [_sanitize_resumed_message(message) for message in messages]


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
        if image_url is not None and not _is_base64_image_data_url(image_url):
            restored["output"] = "Historical chart output is unavailable in this exported trace."
            break
    return restored


def _is_base64_image_data_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("data:image/") and ";base64," in value


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
            if info.get("source_filename") == filename and _columns_match(info, columns) and key not in used
        ]
        if len(candidates) != 1:
            raise TraceResumeError(
                f"Upload the original file '{filename}' with the same ordered columns to resume this trace."
            )
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
    file_info["dataset_description"] = saved.get("dataset_description") or ""
    primary_key = saved.get("primary_key")
    file_info["primary_key"] = primary_key if isinstance(primary_key, list) else []
    data_types = saved.get("data_types")
    if isinstance(data_types, dict):
        file_info["data_types"] = pd.Series(
            {column: data_types.get(column, str(dtype)) for column, dtype in file_info["data_types"].items()}
        )
    data_dictionary = saved.get("data_dictionary")
    if isinstance(data_dictionary, (dict, list)):
        file_info["data_dictionary_json"] = json.dumps(data_dictionary)
