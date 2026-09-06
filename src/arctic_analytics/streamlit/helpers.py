import streamlit as st
import uuid
import logging
import json
import hashlib
from collections.abc import Mapping
from datetime import datetime, timezone
import pandas as pd
import matplotlib.figure as mfigure
import os

from arctic_analytics import __version__
from arctic_analytics.artifacts import (
    AnalysisTrace,
    ContextBundle,
    ResearchSession,
    build_research_bundle_zip,
)

MAX_TRACE_STRING_CHARS = 10000
TRACE_STRING_PREVIEW_CHARS = 1000
REDACTED_SECRET_VALUE = "[redacted]"
SENSITIVE_SESSION_KEY_MARKERS = ("api_key", "token", "password", "secret")

def setup_session_state():
    logging.info(f'###############################')
    logging.info(f'setup_session_state')
    logging.info(f'###############################')
    session_page = {}
    session_page['session_id'] = str(uuid.uuid4())
    return session_page

def reset_app():
    logging.info(f'reset_app - {st.session_state["session_id"]}')
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
    st.session_state['messages'] = []
    st.session_state['count'] = 0
    st.session_state['cost'] = 0
    st.session_state['show_sample'] = True
    st.session_state['disable_sample_button'] = False
    st.session_state['context_window_usage'] = 0
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

def disable_sample_button():
    st.session_state['disable_sample_button'] = True

def render_ai_prompt():
    logging.info(f'render_ai_prompt - {st.session_state["session_id"]}')
    with st.sidebar.expander('What does the AI see?', expanded=True):
        if 'system_message' in st.session_state.keys():
            st.subheader(':blue[System Message]')
            st.write(st.session_state['system_message'])
        if 'messages' in st.session_state.keys():
            st.subheader(':blue[Messages]')
            messages_wo_system_message = st.session_state['messages'][1:]
            st.write(messages_wo_system_message)
    render_trace_export()


def render_researcher_notes():
    st.sidebar.text_area(
        "Researcher notes / analysis context",
        key="researcher_notes",
        help="Optional human context to include in context_bundle.json when exporting a research bundle.",
        placeholder="Add assumptions, domain context, data caveats, or review notes to export with the bundle.",
        height=180,
    )
    st.sidebar.caption("These notes are exported into the research bundle.")

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
            outputs.append(message)
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
    return {
        "trace_schema_version": "0.2.0",
        "package_version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": st.session_state.get("session_id"),
        "model": st.session_state.get("model"),
        "cost": st.session_state.get("cost"),
        "context_window_usage": st.session_state.get("context_window_usage"),
        "system_message": _json_safe(_system_message_from_messages(messages)),
        "prompt_str": _json_safe(st.session_state.get("prompt_str") or _latest_user_prompt(messages)),
        "messages": _json_safe(messages),
        "events": _readable_events(messages),
        "tool_calls": _extract_tool_calls(messages),
        "outputs": _extract_outputs(messages),
        "dataset_metadata": _dataset_metadata_for_trace(),
        "errors": _extract_errors(messages),
        "limitations": [
            "Execution uses Python-level validation and runtime constraints, not isolated container or OS-level sandboxing.",
            "Trace export is a snapshot of current Streamlit session state, not a durable audit log.",
            "The trace is not replayable and does not include full dataset provenance records.",
        ],
    }


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

    with st.sidebar.expander("Analysis Trace", expanded=False):
        st.caption("Prepare a JSON snapshot of the current analysis session when you need to export it.")
        if st.button("Prepare Trace Export", key="prepare_trace_export"):
            trace = build_analysis_trace()
            st.session_state["trace_export_json"] = json.dumps(trace, indent=2, default=str)
            st.session_state["trace_export_session_id"] = trace.get("session_id", "session")

        if "trace_export_json" in st.session_state:
            st.download_button(
                label="Export Analysis Trace",
                data=st.session_state["trace_export_json"],
                file_name=f"arctic_analytics_trace_{st.session_state.get('trace_export_session_id', 'session')}.json",
                mime="application/json",
                key="download_trace_export",
            )

        if st.button("Prepare Research Bundle", key="prepare_research_bundle"):
            trace = build_analysis_trace()
            session = build_research_session_from_streamlit(trace)
            st.session_state["research_bundle_zip"] = build_research_bundle_zip(session)
            st.session_state["research_bundle_session_id"] = trace.get("session_id", "session")
            st.session_state["research_bundle_fingerprint"] = _research_bundle_fingerprint(trace)

        if "research_bundle_zip" in st.session_state:
            if _research_bundle_cache_is_current():
                st.download_button(
                    label="Export Research Bundle",
                    data=st.session_state["research_bundle_zip"],
                    file_name=f"arctic_analytics_research_bundle_{st.session_state.get('research_bundle_session_id', 'session')}.zip",
                    mime="application/zip",
                    key="download_research_bundle",
                )
            else:
                _clear_research_bundle_cache()
                st.info("Analysis inputs changed. Prepare the research bundle again before exporting.")

def _research_bundle_fingerprint(trace=None):
    if trace is None:
        trace = build_analysis_trace()
    trace_for_hash = dict(trace)
    trace_for_hash.pop("timestamp", None)
    payload = {
        "trace": trace_for_hash,
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
    return st.session_state.get("research_bundle_fingerprint") == _research_bundle_fingerprint()

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
        analysis_trace=AnalysisTrace(trace),
        context_bundle=ContextBundle(context_bundle),
        source_files=context_bundle["uploaded_context"],
        researcher_notes=st.session_state.get("researcher_notes", ""),
        assumptions=[],
        command="streamlit research bundle export",
        raw_outputs=_extract_raw_outputs(st.session_state.get("messages", [])),
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

def render_tool_response(tool_response):
    """
    Renders a tool response in the Streamlit UI
    
    Args:
        tool_response: The tool response to render
    """
    if tool_response.startswith('data:image/png;base64,'):
        st.image(tool_response)
        return

    if tool_response.startswith('Error'):
        st.error('Tool execution failed. Expand the response below for details.')
        # Keep error details collapsed by design so successful results remain the primary focus.
        with st.expander('🛠️ See Tool Response', expanded=False):
            st.write(tool_response)
        return

    try:
        # Try parsing the response
        data = json.loads(tool_response)

        # Handle double-encoded JSON
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                pass

        # Try converting to DataFrame
        df = try_convert_to_dataframe(data)

        if df is not None:
            st.dataframe(df, width='stretch')
        else:
            st.write(data)

    except json.JSONDecodeError:
        # Not JSON, display as plain text
        st.write(tool_response)

def is_dev_environment():
    try:
        return st.secrets.get('ENV', os.environ.get('ENV', '')) == 'dev'
    except FileNotFoundError:
        return os.environ.get('ENV', '') == 'dev'
