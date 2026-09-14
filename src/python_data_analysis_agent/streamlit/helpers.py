import streamlit as st
import uuid
import logging
import json
import hashlib
import math
from collections.abc import Mapping
from datetime import datetime, timezone
import pandas as pd
import matplotlib.figure as mfigure
import os
import tempfile
from pathlib import Path

from python_data_analysis_agent import __version__
from python_data_analysis_agent.config import (
    MAX_MODEL_CONTEXT_TOKENS,
)
from python_data_analysis_agent.artifacts import (
    AnalysisTrace,
    ContextBundle,
    ResearchSession,
    build_research_bundle_zip,
)
from python_data_analysis_agent.core.trace_resume import MAX_TRACE_BYTES, messages_for_resume
from python_data_analysis_agent.core.output_metadata import DISPLAY_OUTPUT_FIELDS

MAX_TRACE_STRING_CHARS = 10000
TRACE_STRING_PREVIEW_CHARS = 1000
MAX_RENDERED_TOOL_RESPONSE_CHARS = 50_000
MAX_RETAINED_TOOL_OUTPUT_BYTES = 10 * 1024 * 1024
MAX_RETAINED_TOOL_OUTPUT_SESSION_BYTES = 25 * 1024 * 1024
LARGE_PYTHON_OUTPUT_USER_NOTICE = (
    "Unlike other Python execution outputs, this result is too large for the agent to see "
    "and reason about. The agent cannot reason about this table in its final response."
)
TOOL_OUTPUT_NOT_RETAINED_NOTICE = (
    "This large tool result was displayed live but could not be retained. "
    "It will not appear after a rerun or in an exported trace."
)
REDACTED_SECRET_VALUE = "[redacted]"
SENSITIVE_SESSION_KEY_MARKERS = ("api_key", "token", "password", "secret")
RESEARCHER_NOTES_WIDGET_KEY = "researcher_notes_widget"
RETAINED_TOOL_OUTPUTS_KEY = "retained_tool_outputs"
RETAINED_TOOL_OUTPUT_DIRECTORY_KEY = "retained_tool_output_directory"
class TraceExportError(ValueError):
    """Raised when an exported trace cannot be imported by the resume flow."""

def setup_session_state():
    logging.info(f'###############################')
    logging.info(f'setup_session_state')
    logging.info(f'###############################')
    session_page = {}
    session_page['session_id'] = str(uuid.uuid4())
    return session_page

def reset_app():
    logging.info(f'reset_app - {st.session_state["session_id"]}')
    clear_retained_tool_outputs()
    # Clear all keys in st.session_state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    # Re-initialize session_id
    st.session_state['session_id'] = str(uuid.uuid4())
    print('###############################')
    print('reset_app')
    print('###############################')

def goto_data_dictionary_widget():
    logging.info(f'goto_data_dictionary_widget - {st.session_state["session_id"]}')
    st.session_state['data_dictionaries_loaded'] = False

def goto_data_analysis_widget():
    logging.info(f'goto_data_analysis_widget - {st.session_state["session_id"]}')
    st.session_state['datasets_vetted'] = True
    if 'uploaded_files' in st.session_state.keys():
        st.session_state['uploaded_file_names'] = _uploaded_file_names()
        del st.session_state['uploaded_files']

def reset_analysis():
    logging.info(f'reset_analysis - {st.session_state["session_id"]}')
    clear_retained_tool_outputs()
    st.session_state['messages'] = []
    st.session_state['count'] = 0
    st.session_state['cost'] = 0
    st.session_state['show_sample'] = True
    st.session_state['disable_sample_button'] = False
    st.session_state['context_window_usage'] = 0
    st.session_state['context_window_tokens'] = 0
    st.session_state['agent_turn_state'] = 'idle'
    st.session_state.pop('pending_agent_prompt', None)
    st.session_state.pop('pending_sample_prompt', None)
    st.session_state['session_id'] = str(uuid.uuid4())
    print('###############################')
    print('reset_analysis')
    print('###############################')

def render_reset():
    logging.info(f'render_reset - {st.session_state["session_id"]}')
    st.sidebar.button(':red[Reset App]', on_click=reset_app)

def render_reset_analysis():
    logging.info(f'render_reset_analysis - {st.session_state["session_id"]}')
    st.sidebar.button(':red[Reset Analysis]', on_click=reset_analysis, key='reset_analysis_sidebar')

def render_session_state():
    logging.info(f'render_session_state - {st.session_state["session_id"]}')
    st.sidebar.write(redact_sensitive_session_state(st.session_state))

def redact_sensitive_session_state(session_state):
    return {
        key: _redact_sensitive_value(key, value)
        for key, value in session_state.items()
    }

def _redact_sensitive_value(key, value):
    if _is_sensitive_session_key(key):
        return REDACTED_SECRET_VALUE
    if isinstance(value, Mapping):
        return {
            nested_key: _redact_sensitive_value(nested_key, nested_value)
            for nested_key, nested_value in value.items()
        }
    if isinstance(value, list):
        return [_redact_sensitive_value(key, item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_sensitive_value(key, item) for item in value)
    return value

def _is_sensitive_session_key(key):
    normalized_key = str(key).lower()
    return any(marker in normalized_key for marker in SENSITIVE_SESSION_KEY_MARKERS)

def select_sample_prompt(prompt):
    """Queue a sample prompt from a button callback for the next script run."""
    st.session_state['pending_sample_prompt'] = prompt
    st.session_state['agent_turn_state'] = 'queued'
    st.session_state['show_sample'] = False
    st.session_state['disable_sample_button'] = True

def render_ai_prompt():
    logging.info(f'render_ai_prompt - {st.session_state["session_id"]}')
    render_trace_export()
    with st.sidebar.expander('What does the AI see?', expanded=False):
        if 'system_message' in st.session_state.keys():
            st.subheader(':blue[System Message]')
            st.write(st.session_state['system_message'])
        if 'messages' in st.session_state.keys():
            st.subheader(':blue[Messages]')
            messages_wo_system_message = _messages_without_display_output(
                st.session_state['messages'][1:]
            )
            st.write(messages_wo_system_message)


def render_researcher_notes(disabled=False):
    # Keep the persisted value separate from the widget key.  On a trace
    # restore, Streamlit can otherwise reconcile a prior browser-side empty
    # textarea value over the newly restored ``researcher_notes`` state.
    notes = st.session_state.get("researcher_notes", "")
    if not isinstance(notes, str):
        notes = ""
        st.session_state["researcher_notes"] = notes
    st.session_state[RESEARCHER_NOTES_WIDGET_KEY] = notes

    st.sidebar.text_area(
        "Researcher notes / analysis context",
        key=RESEARCHER_NOTES_WIDGET_KEY,
        on_change=_sync_researcher_notes,
        help="Optional human context to include in context_bundle.json when exporting a research bundle.",
        placeholder="Add assumptions, domain context, data caveats, or review notes to export with the bundle.",
        height=180,
        disabled=disabled,
    )
    st.sidebar.caption("These notes are exported into the research bundle.")


def _sync_researcher_notes():
    """Copy textarea edits into the trace and research-bundle state."""
    st.session_state["researcher_notes"] = st.session_state.get(
        RESEARCHER_NOTES_WIDGET_KEY, ""
    )


def _json_safe(value):
    if isinstance(value, str):
        if value.startswith("data:image/") and ";base64," in value:
            header, _, payload = value.partition(",")
            return {
                "type": "image_base64",
                "media_type": header.replace("data:", "").replace(";base64", ""),
                "length_chars": len(value),
                "payload_length_chars": len(payload),
                "truncated": True,
            }
        if len(value) > MAX_TRACE_STRING_CHARS:
            return {
                "type": "text",
                "length_chars": len(value),
                "preview": value[:TRACE_STRING_PREVIEW_CHARS],
                "truncated": True,
            }
        return value
    if isinstance(value, pd.DataFrame):
        preview = value.head(100)
        return {
            "type": "pandas.DataFrame",
            "shape": list(value.shape),
            "columns": [str(column) for column in value.columns],
            "data": json.loads(preview.to_json(orient="records", date_format="iso")),
            "truncated": len(value) > 100,
        }
    if isinstance(value, pd.Series):
        preview = value.head(100)
        return {
            "type": "pandas.Series",
            "name": str(value.name),
            "data": json.loads(preview.to_json(date_format="iso")),
            "truncated": len(value) > 100,
        }
    if isinstance(value, mfigure.Figure):
        return {"type": "matplotlib.figure.Figure"}
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)

def _parse_json_if_possible(value):
    if not isinstance(value, str):
        return _json_safe(value)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value

def _dataset_metadata_for_trace():
    dataset_metadata = {}
    for filename, file_info in st.session_state.get("vetted_files", {}).items():
        dataframe = file_info.get("dataframe")
        column_names = [str(column) for column in file_info.get("columns_names", [])]
        metadata = {
            "dataset_description": file_info.get("dataset_description"),
            "column_names": column_names,
            "columns_names": column_names,
            "data_types": {str(key): str(value) for key, value in getattr(file_info.get("data_types"), "items", lambda: [])()},
            "primary_key": _json_safe(file_info.get("primary_key", [])),
            "data_dictionary": _parse_json_if_possible(file_info.get("data_dictionary_json")),
        }
        if dataframe is not None:
            metadata["shape"] = list(dataframe.shape)
            metadata["columns"] = [str(column) for column in dataframe.columns]
        if "pandas_describe" in file_info:
            metadata["pandas_describe"] = _json_safe(file_info["pandas_describe"])
        dataset_metadata[filename] = metadata
    return dataset_metadata

def _extract_tool_calls(messages):
    tool_calls = []
    for message in messages:
        if isinstance(message, dict):
            if message.get("type") == "function_call":
                tool_calls.append(_json_safe(message))
            for tool_call in message.get("tool_calls", []) or []:
                tool_calls.append(_json_safe(tool_call))
    return tool_calls

def _extract_outputs(messages):
    outputs = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("type") == "function_call_output":
            outputs.append(_json_safe(message))
            continue
        if "output" in message:
            outputs.append(
                {
                    "role": message.get("role"),
                    "type": message.get("type"),
                    "output": _json_safe(message.get("output")),
                }
            )
    return outputs

def _extract_raw_outputs(messages):
    outputs = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("type") == "function_call_output":
            output = dict(message)
            # Paths are session-local implementation details. The artifact API
            # receives retained bytes separately, never a caller-provided path.
            output.pop("_retained_output_path", None)
            outputs.append(output)
            continue
        if "output" in message:
            outputs.append(
                {
                    "role": message.get("role"),
                    "type": message.get("type"),
                    "output": message.get("output"),
                }
            )
    return outputs


def _extract_retained_output_bytes(messages):
    retained_outputs = {}
    for message in messages:
        if not isinstance(message, dict) or message.get("type") != "function_call_output":
            continue
        output_ref = message.get("display_output_ref")
        retained_path = retained_tool_output_path(output_ref)
        if not retained_path:
            continue
        try:
            retained_outputs[output_ref] = Path(retained_path).read_bytes()
        except OSError:
            logging.warning("Unable to read retained tool output for artifact export")
    return retained_outputs

def _uploaded_file_names():
    uploaded_files = st.session_state.get("uploaded_files", [])
    if uploaded_files:
        return [getattr(file_obj, "name", str(file_obj)) for file_obj in uploaded_files]

    uploaded_file_names = st.session_state.get("uploaded_file_names")
    if uploaded_file_names and st.session_state.get("source") == "uploader":
        return [str(name) for name in uploaded_file_names]

    source_filenames = []
    for filename, file_info in st.session_state.get("vetted_files", {}).items():
        if isinstance(file_info, dict):
            source_filenames.append(str(file_info.get("source_filename") or filename))
        else:
            source_filenames.append(str(filename))
    return source_filenames

def _extract_errors(messages):
    errors = []
    for message in messages:
        if isinstance(message, dict) and message.get("error"):
            errors.append(_json_safe(message))
    return errors

def _system_message_from_messages(messages):
    if not messages:
        return st.session_state.get("system_message")
    try:
        return messages[0]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return st.session_state.get("system_message")

def _latest_user_prompt(messages):
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
        if not isinstance(content, list):
            continue
        texts = [
            item["text"]
            for item in content
            if isinstance(item, dict)
            and isinstance(item.get("text"), str)
            and item["text"].strip()
        ]
        if texts:
            return "\n".join(texts)
    return None


def build_analysis_trace():
    messages = st.session_state.get("messages", [])
    # The resumable manifest is the only copy that needs user-visible tool
    # output. Keeping those payloads out of the top-level audit summaries
    # avoids spending the 10 MiB import budget on duplicate data.
    trace_messages = (
        _messages_without_display_output(messages)
        if st.session_state.get("source") == "uploader"
        else messages
    )
    trace = {
        "trace_schema_version": "0.4.0",
        "package_version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": st.session_state.get("session_id"),
        "cost": st.session_state.get("cost"),
        "context_window_usage": st.session_state.get("context_window_usage"),
        "researcher_notes": st.session_state.get("researcher_notes", "")
        if isinstance(st.session_state.get("researcher_notes", ""), str) else "",
        "system_message": _json_safe(_system_message_from_messages(messages)),
        "prompt_str": _json_safe(st.session_state.get("prompt_str") or _latest_user_prompt(messages)),
        "messages": _json_safe(trace_messages),
        "events": _readable_events(messages),
        "tool_calls": _extract_tool_calls(messages),
        "outputs": _extract_outputs(trace_messages),
        "dataset_metadata": _dataset_metadata_for_trace(),
        "errors": _extract_errors(messages),
        "limitations": [
            "Execution uses Python-level validation and runtime constraints, not isolated container or OS-level sandboxing.",
            "Trace export is a snapshot of current Streamlit session state, not a durable audit log.",
            "The trace is not replayable and does not include full dataset provenance records.",
        ],
    }
    if st.session_state.get("source") == "uploader":
        trace["resume"] = _build_resume_manifest()
    return trace


def _messages_without_display_output(messages):
    return [
        {key: value for key, value in message.items() if key not in DISPLAY_OUTPUT_FIELDS}
        if isinstance(message, dict) else message
        for message in messages
    ]


def serialize_analysis_trace(trace):
    """Serialize a trace only when it meets the resume import size limit."""
    payload = json.dumps(trace, separators=(",", ":"), default=str).encode("utf-8")
    if len(payload) > MAX_TRACE_BYTES:
        retained_output_guidance = ""
        if _trace_has_retained_output_reference(trace):
            retained_output_guidance = (
                " Retained tool output may be contributing to the size; reduce it before exporting."
            )
        raise TraceExportError(
            "This trace is larger than 10 MiB and cannot be resumed. "
            "Reduce the analysis history or chart outputs, then export again."
            + retained_output_guidance
        )
    return payload.decode("utf-8")


def _trace_has_retained_output_reference(value):
    """Identify trace metadata pointing to session-retained tool output."""
    if isinstance(value, dict):
        if isinstance(value.get("display_output_ref"), str):
            return True
        return any(_trace_has_retained_output_reference(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_trace_has_retained_output_reference(item) for item in value)
    return False


def _build_resume_manifest():
    datasets = []
    for dataset_key, file_info in st.session_state.get("vetted_files", {}).items():
        datasets.append(
            {
                "dataset_key": str(dataset_key),
                "source_filename": str(file_info.get("source_filename") or dataset_key),
                "column_names": [str(column) for column in file_info.get("columns_names", [])],
            }
        )
    return {
        "resume_schema_version": "1.0",
        "source": "uploader",
        "datasets": datasets,
        "context_window_usage": (
            st.session_state.get("context_window_usage")
            if isinstance(st.session_state.get("context_window_usage"), (int, float))
            and not isinstance(st.session_state.get("context_window_usage"), bool)
            else 0
        ),
        "context_window_tokens": (
            st.session_state.get("context_window_tokens")
            if isinstance(st.session_state.get("context_window_tokens"), int)
            and not isinstance(st.session_state.get("context_window_tokens"), bool)
            and st.session_state.get("context_window_tokens") >= 0
            else 0
        ),
        "researcher_notes": st.session_state.get("researcher_notes", "")
        if isinstance(st.session_state.get("researcher_notes", ""), str) else "",
        "resumed_from_session_id": st.session_state.get("resumed_from_session_id"),
        "messages": _resume_json_safe(st.session_state.get("messages", [])),
    }


def _resume_json_safe(value):
    """JSON-safe resume data that intentionally preserves chart data URLs."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return {str(key): _resume_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_resume_json_safe(item) for item in value]
    if isinstance(value, (pd.DataFrame, pd.Series, mfigure.Figure)):
        return _json_safe(value)
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def restore_trace_session(trace, preparation):
    """Replace analysis state with an explicitly selected subset of an imported trace."""
    api_key = st.session_state.get("OPENAI_API_KEY")
    clear_retained_tool_outputs()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    if api_key:
        st.session_state["OPENAI_API_KEY"] = api_key

    resume = trace.get("resume") if isinstance(trace.get("resume"), dict) else {}
    researcher_notes = resume.get("researcher_notes")
    if not isinstance(researcher_notes, str):
        researcher_notes = trace.get("researcher_notes", "")
    if not isinstance(researcher_notes, str):
        researcher_notes = ""
    context_window_usage = resume.get("context_window_usage")
    if not isinstance(context_window_usage, (int, float)) or isinstance(context_window_usage, bool):
        context_window_usage = trace.get("context_window_usage", 0)
    if (
        not isinstance(context_window_usage, (int, float))
        or isinstance(context_window_usage, bool)
        or not 0 <= context_window_usage <= 1
    ):
        context_window_usage = 0
    context_window_tokens = resume.get("context_window_tokens")
    if (
        not isinstance(context_window_tokens, int)
        or isinstance(context_window_tokens, bool)
        or context_window_tokens < 0
        or context_window_tokens > MAX_MODEL_CONTEXT_TOKENS
    ):
        # Traces produced before context token counts were persisted retain the
        # percentage, which was calculated using this configured limit.
        context_window_tokens = round(context_window_usage * MAX_MODEL_CONTEXT_TOKENS)
    cost = trace.get("cost")
    if (
        not isinstance(cost, (int, float))
        or isinstance(cost, bool)
        or (isinstance(cost, float) and not math.isfinite(cost))
        or cost < 0
    ):
        cost = 0
    resumed_messages = messages_for_resume(trace)
    original_session_id = trace.get("session_id")
    st.session_state.update(
        {
            "session_id": str(uuid.uuid4()),
            "resumed_from_session_id": original_session_id,
            "source": "uploader",
            "uploaded_file_names": [
                info.get("source_filename") or dataset_key
                for dataset_key, info in preparation.vetted_files.items()
            ],
            "vetted_files": preparation.vetted_files,
            "messages": resumed_messages,
            "rebuild_system_message": bool(resumed_messages),
            "cost": cost,
            "context_window_usage": context_window_usage,
            "context_window_tokens": context_window_tokens,
            "count": sum(
                1 for message in resumed_messages
                if isinstance(message, dict) and message.get("role") == "user"
            ),
            "show_sample": False,
            "disable_sample_button": False,
            "researcher_notes": researcher_notes,
            RESEARCHER_NOTES_WIDGET_KEY: researcher_notes,
            "data_dictionaries_loaded": False,
            "datasets_vetted": False,
        }
    )
    if preparation.vetted_files:
        # Resume intentionally permits refreshed rows. Keep the history for
        # continuity, but make its earlier-data scope clear before analysis.
        st.session_state["resume_warning"] = (
            "This analysis was resumed with uploaded data that may have been refreshed. "
            "Historical outputs and charts describe the earlier data; re-run important findings before relying on them."
        )


def _readable_events(messages):
    events = []
    for index, message in enumerate(messages, start=1):
        if not isinstance(message, dict):
            continue
        event = {
            "step_index": index,
            "event_type": str(message.get("type") or message.get("role") or "unknown"),
        }
        if message.get("role"):
            event["role"] = str(message["role"])
        if message.get("name"):
            event["tool_name"] = str(message["name"])
        elif isinstance(message.get("function"), dict) and message["function"].get("name"):
            event["tool_name"] = str(message["function"]["name"])
        summary = _event_summary(message)
        if summary:
            event["summary"] = summary
        events.append(event)
    return events


def _event_summary(message):
    if message.get("type") == "function_call":
        raw_arguments = message.get("arguments") or message.get("function", {}).get("arguments")
        parsed = _parse_json_if_possible(raw_arguments)
        if isinstance(parsed, dict):
            return str(parsed.get("reason") or parsed.get("python_expression") or parsed.get("function_definition") or "")[:300]
    if message.get("type") == "function_call_output":
        output = message.get("output")
        if isinstance(output, str):
            return output[:300]
        if isinstance(output, list):
            return f"{len(output)} output item(s)"
    if message.get("type") == "message":
        try:
            return str(message["content"][0]["text"])[:300]
        except (KeyError, IndexError, TypeError):
            return None
    return None

def render_trace_export():
    if "messages" not in st.session_state and "vetted_files" not in st.session_state:
        return

    export_actions_disabled = st.session_state.get("agent_turn_state", "idle") != "idle"
    st.sidebar.write("Analysis Trace")
    st.sidebar.caption("Prepare a JSON snapshot of the current analysis session when you need to export it.")
    if st.sidebar.button(
        "Prepare Trace Export",
        key="prepare_trace_export",
        width='stretch',
        disabled=export_actions_disabled,
    ):
        trace = build_analysis_trace()
        try:
            st.session_state["trace_export_json"] = serialize_analysis_trace(trace)
        except TraceExportError as exc:
            st.session_state.pop("trace_export_json", None)
            st.session_state.pop("trace_export_session_id", None)
            st.session_state.pop("trace_export_fingerprint", None)
            st.sidebar.error(str(exc))
        else:
            st.session_state["trace_export_session_id"] = trace.get("session_id", "session")
            st.session_state["trace_export_fingerprint"] = _trace_export_fingerprint(trace)

    if "trace_export_json" in st.session_state:
        if _trace_export_cache_is_current():
            st.sidebar.download_button(
                label=":green[Download Analysis Trace]",
                data=st.session_state["trace_export_json"],
                file_name=f"python_data_analysis_agent_trace_{st.session_state.get('trace_export_session_id', 'session')}.json",
                mime="application/json",
                key="download_trace_export",
                width='stretch',
            )
        else:
            _clear_trace_export_cache()
            st.sidebar.info(_export_cache_stale_message())

    if st.sidebar.button(
        "Prepare Research Bundle",
        key="prepare_research_bundle",
        width='stretch',
        disabled=export_actions_disabled,
    ):
        trace = build_analysis_trace()
        session = build_research_session_from_streamlit(trace)
        st.session_state["research_bundle_zip"] = build_research_bundle_zip(session)
        st.session_state["research_bundle_session_id"] = trace.get("session_id", "session")
        st.session_state["research_bundle_fingerprint"] = _research_bundle_fingerprint(trace)

    if "research_bundle_zip" in st.session_state:
        if _research_bundle_cache_is_current():
            st.sidebar.download_button(
                label=":green[Download Research Bundle]",
                data=st.session_state["research_bundle_zip"],
                file_name=f"python_data_analysis_agent_research_bundle_{st.session_state.get('research_bundle_session_id', 'session')}.zip",
                mime="application/zip",
                key="download_research_bundle",
                width='stretch',
            )
        else:
            _clear_research_bundle_cache()
            st.sidebar.info(_export_cache_stale_message())


def _export_cache_stale_message():
    if st.session_state.get("agent_turn_state", "idle") != "idle":
        return "Analysis is running. Prepare the export after it finishes."
    return "Analysis inputs changed. Prepare the export again before downloading."


def _trace_export_fingerprint(trace=None):
    if trace is None:
        trace = build_analysis_trace()
    trace_for_hash = dict(trace)
    trace_for_hash.pop("timestamp", None)
    encoded = json.dumps(trace_for_hash, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _trace_export_cache_is_current():
    return (
        st.session_state.get("agent_turn_state", "idle") == "idle"
        and st.session_state.get("trace_export_fingerprint") == _trace_export_fingerprint()
    )


def _clear_trace_export_cache():
    for key in ("trace_export_json", "trace_export_session_id", "trace_export_fingerprint"):
        st.session_state.pop(key, None)

def _research_bundle_fingerprint(trace=None):
    if trace is None:
        trace = build_analysis_trace()
    trace_for_hash = dict(trace)
    trace_for_hash.pop("timestamp", None)
    payload = {
        "trace": trace_for_hash,
        "model": st.session_state.get("model"),
        "researcher_notes": st.session_state.get("researcher_notes", ""),
        "uploaded_context": {
            "source": st.session_state.get("source"),
            "uploaded_files": _uploaded_file_names(),
        },
        "raw_outputs": _extract_raw_outputs(st.session_state.get("messages", [])),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def _research_bundle_cache_is_current():
    return (
        st.session_state.get("agent_turn_state", "idle") == "idle"
        and st.session_state.get("research_bundle_fingerprint") == _research_bundle_fingerprint()
    )

def _clear_research_bundle_cache():
    for key in ("research_bundle_zip", "research_bundle_session_id", "research_bundle_fingerprint"):
        if key in st.session_state:
            del st.session_state[key]

def build_research_session_from_streamlit(trace=None):
    if trace is None:
        trace = build_analysis_trace()
    context_bundle = {
        "context_bundle_version": "0.1.0",
        "prompt": st.session_state.get("prompt_str") or trace.get("prompt_str"),
        "dataset_metadata": trace.get("dataset_metadata", {}),
        "researcher_notes": st.session_state.get("researcher_notes", ""),
        "uploaded_context": {
            "source": st.session_state.get("source"),
            "uploaded_files": _uploaded_file_names(),
        },
        "assumptions": [],
        "limitations": [
            "This context bundle is derived from the current Streamlit session state.",
            "The bundle is intended for review and publication support, not deterministic replay.",
        ],
    }
    return ResearchSession(
        prompt=st.session_state.get("prompt_str") or trace.get("prompt_str"),
        model=st.session_state.get("model"),
        analysis_trace=AnalysisTrace(trace),
        context_bundle=ContextBundle(context_bundle),
        source_files=context_bundle["uploaded_context"],
        researcher_notes=st.session_state.get("researcher_notes", ""),
        assumptions=[],
        command="streamlit research bundle export",
        raw_outputs=_extract_raw_outputs(st.session_state.get("messages", [])),
        retained_output_bytes=_extract_retained_output_bytes(st.session_state.get("messages", [])),
    )

def safely_escape_dollars(text):
    """
    Escapes dollar signs in text only if they don't appear to be already escaped.
    """
    if not text:
        return text
    if '\\$' in text:  # Check for already escaped dollars
        return text
    else:
        return text.replace('$', '\\$')

def try_convert_to_dataframe(data):
    """Helper function to attempt converting various data types to DataFrames"""
    try:
        if isinstance(data, dict):
            return pd.DataFrame.from_dict(data, orient='index')
        elif isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
            return pd.DataFrame(data)
        return None
    except Exception:
        return None


def _parse_truncated_table_json(value):
    """Recover complete rows from a truncated pandas ``orient='index'`` payload."""
    if not isinstance(value, str):
        return None
    payload = value.lstrip()
    if not payload.startswith("{"):
        return None

    decoder = json.JSONDecoder()
    position = 1
    rows = {}

    def skip_whitespace(index):
        while index < len(payload) and payload[index].isspace():
            index += 1
        return index

    while True:
        position = skip_whitespace(position)
        if position >= len(payload) or payload[position] == "}":
            break
        try:
            key, position = decoder.raw_decode(payload, position)
            position = skip_whitespace(position)
            if not isinstance(key, str) or position >= len(payload) or payload[position] != ":":
                return None
            row, position = decoder.raw_decode(payload, skip_whitespace(position + 1))
        except json.JSONDecodeError:
            break
        if not isinstance(row, dict):
            return None
        rows[key] = row
        position = skip_whitespace(position)
        if position >= len(payload) or payload[position] == "}":
            break
        if payload[position] != ",":
            return None
        position += 1

    return rows or None


def render_tool_call(tool_call):
    """
    Renders a tool call in the Streamlit UI
    
    Args:
        tool_call: The tool call to render
    """
    if not isinstance(tool_call, dict):
        logging.warning(f'Unexpected tool call shape: {tool_call}')
        tool_call = {}

    function = tool_call.get('function', {})
    tool_name = tool_call.get('name') or function.get('name') or 'unknown'
    raw_arguments = tool_call.get('arguments') or function.get('arguments') or '{}'

    if isinstance(raw_arguments, dict):
        arguments = raw_arguments
    else:
        try:
            arguments = json.loads(raw_arguments)
        except (TypeError, json.JSONDecodeError):
            logging.warning(f'Unable to parse tool call arguments for {tool_name}: {raw_arguments}')
            arguments = {}

    if 'reason' in arguments:
        st.write(f"Reason: {safely_escape_dollars(str(arguments['reason']))}")
    with st.expander(f"🛠️ See Tool Call - Tool Name: {tool_name}", expanded=False):
        if 'python_expression' in arguments:
            st.code(arguments['python_expression'], language='python')
        if 'function_definition' in arguments:
            st.code(arguments['function_definition'], language='python')
        if not arguments:
            st.code(str(raw_arguments), language='json')

def retain_tool_output(output_id, tool_response):
    """Persist an oversized result outside conversation state for this session only."""
    if not isinstance(output_id, str):
        logging.warning("Refusing to retain tool output with a non-string ID")
        return None

    output_bytes = tool_response.encode("utf-8")
    if len(output_bytes) > MAX_RETAINED_TOOL_OUTPUT_BYTES:
        logging.warning("Tool output exceeds the per-output retention limit")
        return None

    directory = st.session_state.get(RETAINED_TOOL_OUTPUT_DIRECTORY_KEY)
    if directory is None:
        try:
            directory = tempfile.TemporaryDirectory(prefix="python-data-analysis-agent-tool-output-")
        except OSError:
            logging.exception("Unable to create temporary storage for tool output")
            return None
        st.session_state[RETAINED_TOOL_OUTPUT_DIRECTORY_KEY] = directory

    retained_outputs = st.session_state.setdefault(RETAINED_TOOL_OUTPUTS_KEY, {})
    retained_bytes = 0
    for retained_path in retained_outputs.values():
        if not isinstance(retained_path, str):
            continue
        try:
            retained_bytes += Path(retained_path).stat().st_size
        except OSError:
            continue
    if retained_bytes + len(output_bytes) > MAX_RETAINED_TOOL_OUTPUT_SESSION_BYTES:
        logging.warning("Tool output exceeds the session retention limit")
        return None

    # Never derive a filesystem path from the model/API-provided call ID.
    path = Path(directory.name) / f"{uuid.uuid4().hex}.txt"
    try:
        path.write_bytes(output_bytes)
    except OSError:
        logging.exception("Unable to retain tool output")
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    retained_outputs[output_id] = str(path)
    return str(path)


def retained_tool_output_path(output_id):
    if not isinstance(output_id, str):
        return None
    path = st.session_state.get(RETAINED_TOOL_OUTPUTS_KEY, {}).get(output_id)
    return path if isinstance(path, str) and Path(path).is_file() else None


def clear_retained_tool_outputs():
    directory = st.session_state.pop(RETAINED_TOOL_OUTPUT_DIRECTORY_KEY, None)
    if directory is not None:
        directory.cleanup()
    st.session_state.pop(RETAINED_TOOL_OUTPUTS_KEY, None)


def render_tool_response(tool_response, output_id=None, full_output_path=None, allow_full_download=True):
    """
    Renders a tool response in the Streamlit UI
    
    Args:
        tool_response: The tool response to render.
        output_id: Stable identifier used to avoid duplicate download-widget keys.
    Returns:
        True when the response was rendered as a dataframe, otherwise False.
    """
    if tool_response.startswith((
        'data:image/png;base64,',
        'data:image/jpeg;base64,',
        'data:image/gif;base64,',
        'data:image/webp;base64,',
    )):
        st.image(tool_response)
        return False

    # On a rerun, ``tool_response`` can be a bounded preview while the full
    # result remains in the retained file. Prefer that complete payload for
    # table detection so a dataframe does not revert to partial JSON text.
    full_tool_response = None
    full_output_bytes = None
    if full_output_path:
        try:
            full_output_bytes = Path(full_output_path).read_bytes()
            full_tool_response = full_output_bytes.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            logging.warning("Unable to read retained tool output for rendering")

    renderable_response = full_tool_response or tool_response

    # Parse tabular JSON before applying the text-size fallback. A dataframe
    # remains usable in Streamlit's virtualized table UI even when its JSON
    # serialization would be too large to show as plain text in a chat message.
    parsed_response = None
    stripped_response = renderable_response.lstrip()
    looks_like_tabular_json = (
        stripped_response.startswith('{"')
        or stripped_response.startswith('[{')
    )
    if len(renderable_response) <= MAX_RENDERED_TOOL_RESPONSE_CHARS or looks_like_tabular_json:
        try:
            parsed_response = json.loads(renderable_response)

            # Handle double-encoded JSON.
            if isinstance(parsed_response, str):
                try:
                    parsed_response = json.loads(parsed_response)
                except json.JSONDecodeError:
                    pass
        except json.JSONDecodeError:
            parsed_response = _parse_truncated_table_json(renderable_response)

        dataframe = try_convert_to_dataframe(parsed_response)
        if dataframe is not None:
            st.dataframe(dataframe, width="stretch")
            if full_output_path and full_output_bytes is None:
                st.warning("The complete tool output was not retained and cannot be downloaded.")
            elif allow_full_download and full_output_bytes is not None:
                st.download_button(
                    "Download full tool output",
                    data=full_output_bytes,
                    file_name="tool-output.txt",
                    mime="text/plain",
                    key=(
                        f"tool-output-{output_id}"
                        if output_id is not None
                        else f"tool-output-{hashlib.sha256(tool_response.encode('utf-8')).hexdigest()}"
                    ),
                    icon=":material/download:",
                    on_click="ignore",
                )
            return True

    if len(tool_response) > MAX_RENDERED_TOOL_RESPONSE_CHARS or full_output_path:
        preview = tool_response[:MAX_RENDERED_TOOL_RESPONSE_CHARS]
        if len(renderable_response) > MAX_RENDERED_TOOL_RESPONSE_CHARS:
            st.warning(
                f"Tool output is {len(renderable_response):,} characters. "
                "Showing a preview to keep the app responsive."
            )
        st.code(preview, language="json" if preview.lstrip().startswith(("{", "[")) else None)
        if allow_full_download and (not full_output_path or full_output_bytes is not None):
            st.download_button(
                "Download full tool output",
                data=full_output_bytes if full_output_path else tool_response,
                file_name="tool-output.txt",
                mime="text/plain",
                key=(
                    f"tool-output-{output_id}"
                    if output_id is not None
                    else f"tool-output-{hashlib.sha256(tool_response.encode('utf-8')).hexdigest()}"
                ),
                icon=":material/download:",
                on_click="ignore",
            )
        else:
            st.warning("The complete tool output was not retained and cannot be downloaded.")
        return False

    if tool_response.startswith('Error'):
        # Keep failed-tool details available without interrupting the analysis flow.
        with st.expander('⚠️ Tool execution failed — see details', expanded=False):
            st.error(tool_response)
        return False

    if parsed_response is not None:
        st.write(parsed_response)
    else:
        # Not JSON, display as plain text.
        st.write(tool_response)
    return False

def is_dev_environment():
    try:
        return st.secrets.get('ENV', os.environ.get('ENV', '')) == 'dev'
    except FileNotFoundError:
        return os.environ.get('ENV', '') == 'dev'
