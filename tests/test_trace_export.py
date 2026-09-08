import json
import re
import zipfile
from io import BytesIO
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from streamlit.testing.v1 import AppTest

from arctic_analytics.streamlit.helpers import (
    _clear_research_bundle_cache,
    _research_bundle_cache_is_current,
    _research_bundle_fingerprint,
    build_analysis_trace,
    build_research_session_from_streamlit,
    goto_data_analysis_widget,
    redact_sensitive_session_state,
    restore_trace_session,
    serialize_analysis_trace,
    TraceExportError,
)
from arctic_analytics.config import MAX_MODEL_CONTEXT_TOKENS
from arctic_analytics.core.trace_resume import MAX_TRACE_BYTES, ResumePreparation, load_analysis_trace
from arctic_analytics.artifacts import build_research_bundle_zip


ROOT = Path(__file__).resolve().parents[1]
RFC3339_DATE_TIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


@lru_cache(maxsize=1)
def load_trace_schema():
    return json.loads((ROOT / "schemas" / "analysis_trace.schema.json").read_text())


@lru_cache(maxsize=1)
def trace_format_checker():
    format_checker = FormatChecker()
    if "date-time" not in format_checker.checkers:

        @format_checker.checks("date-time")
        def is_date_time(value):
            if not isinstance(value, str):
                return True
            if not RFC3339_DATE_TIME_PATTERN.match(value):
                return False
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True

    return format_checker


def validate_trace_schema(trace):
    Draft202012Validator(load_trace_schema(), format_checker=trace_format_checker()).validate(trace)


def test_build_analysis_trace_is_json_safe_and_truncates_large_payloads():
    st.session_state.clear()
    long_text = "x" * 12000
    image_payload = "data:image/png;base64," + ("a" * 12000)

    st.session_state["session_id"] = "trace-test-session"
    st.session_state["model"] = "gpt-test"
    st.session_state["cost"] = 0.123
    st.session_state["system_message"] = long_text
    st.session_state["prompt_str"] = long_text
    st.session_state["messages"] = [
        {
            "type": "function_call",
            "name": "generate_plot",
            "arguments": json.dumps({"function_definition": "def generate_plot(): pass"}),
        },
        {
            "type": "function_call_output",
            "output": image_payload,
        },
        {
            "role": "assistant",
            "output": pd.DataFrame(
                {
                    "count": [1, 2],
                    "created_at": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                }
            ),
        },
        {
            "role": "assistant",
            "error": True,
            "content": "example error",
        },
    ]
    st.session_state["vetted_files"] = {
        "sales": {
            "dataset_description": "Sales data.",
            "columns_names": pd.Index(["count", "created_at"]),
            "data_types": pd.Series({"count": "Int64", "created_at": "datetime64[ns]"}),
            "primary_key": [],
            "data_dictionary_json": '{"0":{"Column Name":"count","Data Type":"Int64"}}',
            "dataframe": pd.DataFrame({"count": [1, 2]}),
        }
    }

    trace = build_analysis_trace()
    dumped = json.dumps(trace)
    validate_trace_schema(trace)

    assert dumped
    assert trace["trace_schema_version"] == "0.3.0"
    assert trace["package_version"]
    assert trace["timestamp"]
    assert "model" not in trace
    assert trace["system_message"]["truncated"] is True
    assert trace["system_message"]["length_chars"] == 12000
    assert trace["prompt_str"]["truncated"] is True
    assert trace["events"][0]["step_index"] == 1
    assert trace["events"][0]["event_type"] == "function_call"
    assert trace["events"][0]["tool_name"] == "generate_plot"
    assert trace["outputs"][0]["output"]["type"] == "image_base64"
    assert trace["outputs"][0]["output"]["payload_length_chars"] == 12000
    assert trace["outputs"][1]["output"]["data"][0]["count"] == 1
    assert isinstance(trace["outputs"][1]["output"]["data"][0]["count"], int)
    assert trace["outputs"][1]["output"]["data"][0]["created_at"].startswith("2026-01-01")
    assert trace["dataset_metadata"]["sales"]["column_names"] == ["count", "created_at"]
    assert trace["dataset_metadata"]["sales"]["columns_names"] == ["count", "created_at"]
    assert trace["errors"][0]["content"] == "example error"


@pytest.mark.parametrize("stored_prompt", [None, "", "Explicit prompt"])
def test_trace_and_research_session_use_latest_user_prompt_as_fallback(stored_prompt):
    st.session_state.clear()
    if stored_prompt is not None:
        st.session_state["prompt_str"] = stored_prompt
    st.session_state["messages"] = [
        {"type": "message", "role": "user", "content": [{"text": "First request"}]},
        {
            "type": "message",
            "role": "user",
            "content": [{"text": "Latest request"}, {"type": "input_image"}, {"text": "More detail"}],
        },
        {"type": "message", "role": "assistant", "content": [{"text": "The answer"}]},
    ]

    trace = build_analysis_trace()
    session = build_research_session_from_streamlit(trace)
    expected = stored_prompt or "Latest request\nMore detail"

    assert trace["prompt_str"] == expected
    assert session.prompt == expected
    assert session.context_bundle.data["prompt"] == expected
    assert st.session_state.get("prompt_str") == stored_prompt
    validate_trace_schema(trace)


def test_trace_without_user_messages_has_no_prompt():
    st.session_state.clear()
    st.session_state["messages"] = [
        {"type": "message", "role": "assistant", "content": [{"text": "Welcome"}]},
    ]

    assert build_analysis_trace()["prompt_str"] is None


def test_sample_trace_export_matches_schema():
    trace = json.loads((ROOT / "examples" / "sample_trace_export.json").read_text())

    validate_trace_schema(trace)


def test_trace_schema_rejects_invalid_event_records():
    trace = json.loads((ROOT / "examples" / "sample_trace_export.json").read_text())
    trace["events"] = [{"summary": "missing required event fields"}]

    with pytest.raises(ValidationError):
        validate_trace_schema(trace)


def test_trace_schema_preserves_the_legacy_model_requirement_for_version_0_2_0():
    trace = json.loads((ROOT / "examples" / "sample_trace_export.json").read_text())
    trace["trace_schema_version"] = "0.2.0"
    trace.pop("model", None)

    with pytest.raises(ValidationError):
        validate_trace_schema(trace)

    trace["model"] = "gpt-test"
    validate_trace_schema(trace)


def test_upload_trace_includes_resume_manifest_for_uploaded_csvs():
    st.session_state.clear()
    st.session_state["session_id"] = "resume-export-session"
    st.session_state["source"] = "uploader"
    st.session_state["researcher_notes"] = "Recheck the outliers."
    st.session_state["context_window_usage"] = 0.125
    st.session_state["context_window_tokens"] = 34_000
    st.session_state["messages"] = []
    st.session_state["vetted_files"] = {
        "sales": {
            "source_filename": "Sales 2026.csv",
            "columns_names": pd.Index(["amount", "region"]),
        }
    }

    trace = build_analysis_trace()

    assert trace["researcher_notes"] == "Recheck the outliers."
    assert trace["resume"] == {
        "resume_schema_version": "1.0",
        "source": "uploader",
        "context_window_usage": 0.125,
        "context_window_tokens": 34_000,
        "datasets": [{
            "dataset_key": "sales",
            "source_filename": "Sales 2026.csv",
            "column_names": ["amount", "region"],
        }],
        "researcher_notes": "Recheck the outliers.",
        "resumed_from_session_id": None,
        "messages": [],
    }
    validate_trace_schema(trace)


def test_resume_manifest_preserves_chart_data_urls():
    st.session_state.clear()
    chart_url = "data:image/png;base64,iVBORw0KGgo="
    st.session_state.update({
        "session_id": "chart-export-session",
        "source": "uploader",
        "messages": [{
            "type": "function_call_output",
            "output": [{"type": "input_image", "image_url": chart_url}],
        }],
        "vetted_files": {"sales": {"source_filename": "sales.csv", "columns_names": pd.Index(["amount"])}},
    })

    trace = build_analysis_trace()

    assert trace["messages"][0]["output"][0]["image_url"]["type"] == "image_base64"
    assert trace["resume"]["messages"][0]["output"][0]["image_url"] == chart_url


def test_resume_trace_export_rejects_payloads_larger_than_import_limit():
    st.session_state.clear()
    st.session_state.update({
        "session_id": "oversized-chart-export-session",
        "source": "uploader",
        "messages": [{
            "type": "function_call_output",
            "output": [{
                "type": "input_image",
                "image_url": "data:image/png;base64," + ("a" * (10 * 1024 * 1024)),
            }],
        }],
        "vetted_files": {"sales": {"source_filename": "sales.csv", "columns_names": pd.Index(["amount"])}},
    })

    trace = build_analysis_trace()

    with pytest.raises(TraceExportError, match="larger than 10 MiB and cannot be resumed"):
        serialize_analysis_trace(trace)


def test_trace_export_uses_compact_json_to_maximize_resumable_size():
    st.session_state.clear()
    st.session_state["messages"] = [0] * 2_700_000
    st.session_state["vetted_files"] = {}
    trace = build_analysis_trace()
    compact_payload = json.dumps(trace, separators=(",", ":"), default=str).encode("utf-8")
    indented_payload = json.dumps(trace, indent=2, default=str).encode("utf-8")

    exported_payload = serialize_analysis_trace(trace)

    assert len(compact_payload) <= MAX_TRACE_BYTES < len(indented_payload)
    assert exported_payload.encode("utf-8") == compact_payload
    assert load_analysis_trace(exported_payload.encode("utf-8"))["messages"] == trace["messages"]


def test_trace_schema_accepts_dataset_metadata_without_legacy_columns_names():
    trace = json.loads((ROOT / "examples" / "sample_trace_export.json").read_text())
    del trace["dataset_metadata"]["tips"]["columns_names"]

    validate_trace_schema(trace)


def test_trace_schema_rejects_invalid_timestamp_format():
    trace = json.loads((ROOT / "examples" / "sample_trace_export.json").read_text())
    trace["timestamp"] = "not-a-date-time"

    with pytest.raises(ValidationError):
        validate_trace_schema(trace)


def test_trace_schema_rejects_resume_manifest_for_legacy_trace_version():
    trace = build_analysis_trace()
    trace["trace_schema_version"] = "0.2.0"
    trace["model"] = None
    trace["resume"] = {
        "resume_schema_version": "1.0",
        "source": "uploader",
        "datasets": [{
            "dataset_key": "sales",
            "source_filename": "sales.csv",
            "column_names": ["amount"],
        }],
    }

    with pytest.raises(ValidationError):
        validate_trace_schema(trace)


def test_research_session_from_streamlit_includes_researcher_notes():
    st.session_state.clear()
    st.session_state["session_id"] = "notes-test-session"
    st.session_state["researcher_notes"] = "Assume measurements were reviewed for obvious data entry errors."
    st.session_state["messages"] = []
    st.session_state["vetted_files"] = {}

    session = build_research_session_from_streamlit()

    assert session.context_bundle.data["researcher_notes"] == "Assume measurements were reviewed for obvious data entry errors."
    assert build_analysis_trace()["researcher_notes"] == "Assume measurements were reviewed for obvious data entry errors."


def test_streamlit_research_bundle_records_model_without_exporting_it_in_trace():
    st.session_state.clear()
    st.session_state.update({
        "session_id": "model-provenance-test-session",
        "model": "gpt-5.6-luna",
        "messages": [],
        "vetted_files": {},
    })

    trace = build_analysis_trace()
    session = build_research_session_from_streamlit(trace)
    with zipfile.ZipFile(BytesIO(build_research_bundle_zip(session))) as archive:
        manifest = json.loads(archive.read("research_bundle/run_manifest.json"))

    assert "model" not in trace
    assert session.model == "gpt-5.6-luna"
    assert manifest["model"] == "gpt-5.6-luna"
    assert manifest["provider"] == "openai"


def test_research_session_from_streamlit_preserves_raw_image_outputs_for_bundle():
    st.session_state.clear()
    image_payload = "data:image/png;base64,iVBORw0KGgo="
    st.session_state["session_id"] = "figure-test-session"
    st.session_state["researcher_notes"] = ""
    st.session_state["messages"] = [
        {
            "type": "function_call_output",
            "output": [
                {
                    "type": "input_image",
                    "image_url": image_payload,
                }
            ],
        }
    ]
    st.session_state["vetted_files"] = {}

    trace = build_analysis_trace()
    session = build_research_session_from_streamlit(trace)

    assert trace["outputs"][0]["output"][0]["image_url"]["type"] == "image_base64"
    assert session.raw_outputs[0]["output"][0]["image_url"] == image_payload


def test_goto_data_analysis_preserves_uploaded_file_names_before_deleting_files():
    st.session_state.clear()
    st.session_state["session_id"] = "uploaded-names-test-session"
    st.session_state["uploaded_files"] = [
        type("Upload", (), {"name": "sales.csv"})(),
        type("Upload", (), {"name": "inventory.csv"})(),
    ]

    goto_data_analysis_widget()

    assert "uploaded_files" not in st.session_state
    assert st.session_state["uploaded_file_names"] == ["sales.csv", "inventory.csv"]


def test_research_session_uses_vetted_source_filenames_when_upload_objects_are_gone():
    st.session_state.clear()
    st.session_state["session_id"] = "vetted-source-filenames-test-session"
    st.session_state["source"] = "uploader"
    st.session_state["researcher_notes"] = ""
    st.session_state["messages"] = []
    st.session_state["vetted_files"] = {
        "sales_2026": {"source_filename": "Sales 2026.csv"},
        "inventory": {},
    }

    session = build_research_session_from_streamlit()

    assert session.context_bundle.data["uploaded_context"]["uploaded_files"] == ["Sales 2026.csv", "inventory"]
    assert session.source_files["uploaded_files"] == ["Sales 2026.csv", "inventory"]


def test_research_bundle_fingerprint_ignores_trace_timestamp():
    st.session_state.clear()
    st.session_state["session_id"] = "fingerprint-test-session"
    st.session_state["researcher_notes"] = "Reviewed."
    st.session_state["messages"] = []
    st.session_state["vetted_files"] = {}

    trace = build_analysis_trace()
    same_trace_new_timestamp = dict(trace)
    same_trace_new_timestamp["timestamp"] = "2099-01-01T00:00:00+00:00"

    assert _research_bundle_fingerprint(trace) == _research_bundle_fingerprint(same_trace_new_timestamp)


def test_research_bundle_cache_invalidates_when_inputs_change():
    st.session_state.clear()
    st.session_state["session_id"] = "bundle-cache-test-session"
    st.session_state["researcher_notes"] = "Initial notes."
    st.session_state["messages"] = []
    st.session_state["vetted_files"] = {}
    st.session_state["research_bundle_zip"] = b"zip"
    st.session_state["research_bundle_session_id"] = "bundle-cache-test-session"
    st.session_state["research_bundle_fingerprint"] = _research_bundle_fingerprint()

    assert _research_bundle_cache_is_current() is True

    st.session_state["researcher_notes"] = "Edited notes."

    assert _research_bundle_cache_is_current() is False

    _clear_research_bundle_cache()

    assert "research_bundle_zip" not in st.session_state
    assert "research_bundle_session_id" not in st.session_state
    assert "research_bundle_fingerprint" not in st.session_state


def test_research_bundle_cache_invalidates_when_messages_change():
    st.session_state.clear()
    st.session_state["session_id"] = "bundle-message-cache-test-session"
    st.session_state["researcher_notes"] = ""
    st.session_state["messages"] = []
    st.session_state["vetted_files"] = {}
    st.session_state["research_bundle_fingerprint"] = _research_bundle_fingerprint()

    st.session_state["messages"] = [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "New analysis request."}],
        }
    ]

    assert _research_bundle_cache_is_current() is False


def test_research_bundle_cache_invalidates_when_model_changes():
    st.session_state.clear()
    st.session_state.update({
        "session_id": "bundle-model-cache-test-session",
        "model": "gpt-5.6-luna",
        "researcher_notes": "",
        "messages": [],
        "vetted_files": {},
    })
    st.session_state["research_bundle_fingerprint"] = _research_bundle_fingerprint()

    st.session_state["model"] = "gpt-5.6-terra"

    assert _research_bundle_cache_is_current() is False


def test_redact_sensitive_session_state_hides_credentials_without_mutating_original():
    session_state = {
        "OPENAI_API_KEY": "sk-test",
        "session_id": "safe-session-id",
        "nested": {
            "access_token": "token-value",
            "visible": "not-sensitive",
        },
        "items": [
            {"password": "password-value"},
            {"label": "safe-label"},
        ],
    }

    redacted = redact_sensitive_session_state(session_state)

    assert redacted["OPENAI_API_KEY"] == "[redacted]"
    assert redacted["session_id"] == "safe-session-id"
    assert redacted["nested"]["access_token"] == "[redacted]"
    assert redacted["nested"]["visible"] == "not-sensitive"
    assert redacted["items"][0]["password"] == "[redacted]"
    assert redacted["items"][1]["label"] == "safe-label"
    assert session_state["OPENAI_API_KEY"] == "sk-test"


def test_restore_trace_session_preserves_api_key_but_not_imported_session_state():
    st.session_state.clear()
    st.session_state["OPENAI_API_KEY"] = "local-key"
    st.session_state["unrelated_state"] = "discard-me"
    trace = {
        "session_id": "old-session",
        "messages": [],
        "cost": 1.5,
        "context_window_usage": 0.1,
        "researcher_notes": "Review the July outliers before publishing.",
        "OPENAI_API_KEY": "untrusted-trace-key",
    }
    preparation = ResumePreparation(vetted_files={"sales": {"source_filename": "sales.csv"}})

    restore_trace_session(trace, preparation)

    assert st.session_state["OPENAI_API_KEY"] == "local-key"
    assert "unrelated_state" not in st.session_state
    assert st.session_state["resumed_from_session_id"] == "old-session"
    assert st.session_state["session_id"] != "old-session"
    assert "model" not in st.session_state
    assert st.session_state["context_window_usage"] == 0.1
    assert st.session_state["context_window_tokens"] == round(0.1 * MAX_MODEL_CONTEXT_TOKENS)
    assert st.session_state["researcher_notes"] == "Review the July outliers before publishing."
    assert st.session_state["researcher_notes_widget"] == "Review the July outliers before publishing."
    assert "Historical outputs and charts" in st.session_state["resume_warning"]


def test_restore_trace_session_rejects_boolean_cost():
    st.session_state.clear()

    restore_trace_session({"messages": [], "cost": True}, ResumePreparation(vetted_files={}))

    assert st.session_state["cost"] == 0


@pytest.mark.parametrize("cost", [-0.01, float("nan"), float("inf")])
def test_restore_trace_session_rejects_negative_or_nonfinite_cost(cost):
    st.session_state.clear()

    restore_trace_session({"messages": [], "cost": cost}, ResumePreparation(vetted_files={}))

    assert st.session_state["cost"] == 0


def test_restore_trace_session_rejects_context_tokens_above_application_cap():
    st.session_state.clear()
    trace = {
        "messages": [],
        "context_window_usage": 0.1,
        "resume": {"context_window_tokens": MAX_MODEL_CONTEXT_TOKENS + 1},
    }

    restore_trace_session(trace, ResumePreparation(vetted_files={}))

    assert st.session_state["context_window_tokens"] == round(0.1 * MAX_MODEL_CONTEXT_TOKENS)


def test_researcher_notes_textarea_displays_restored_value_and_saves_edits():
    def script():
        import streamlit as st

        from arctic_analytics.streamlit.helpers import render_researcher_notes

        st.session_state.setdefault("researcher_notes", "Restored research context.")
        render_researcher_notes()

    app = AppTest.from_function(script).run()

    assert not app.exception
    assert app.text_area(key="researcher_notes_widget").value == "Restored research context."

    app.text_area(key="researcher_notes_widget").set_value("Edited research context.").run()

    assert not app.exception
    assert app.session_state["researcher_notes"] == "Edited research context."


def test_researcher_notes_textarea_is_disabled_during_an_agent_turn():
    def script():
        import streamlit as st

        from arctic_analytics.streamlit.helpers import render_researcher_notes

        st.session_state.setdefault("researcher_notes", "Keep this context.")
        st.session_state.setdefault("agent_turn_state", "idle")
        render_researcher_notes(
            disabled=st.session_state.get("agent_turn_state") != "idle"
        )

    app = AppTest.from_function(script).run()
    assert not app.exception
    assert not app.text_area(key="researcher_notes_widget").disabled

    app.session_state["agent_turn_state"] = "running"
    app.run()

    assert not app.exception
    assert app.text_area(key="researcher_notes_widget").disabled


def test_restore_trace_session_ignores_model_from_older_traces():
    st.session_state.clear()
    trace = {"messages": [], "model": "gpt-5.4-mini-2026-03-17"}
    preparation = ResumePreparation(vetted_files={})

    restore_trace_session(trace, preparation)

    assert "model" not in st.session_state
    assert "resume_warning" not in st.session_state


def test_restore_trace_session_counts_the_resumed_message_history():
    st.session_state.clear()
    system_message = {
        "type": "message",
        "role": "system",
        "content": [{"type": "input_text", "text": "System prompt"}],
    }
    top_level_user_message = {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": "Top-level question"}],
    }
    resumed_user_messages = [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "First resumed question"}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Second resumed question"}],
        },
    ]
    trace = {
        "messages": [system_message, top_level_user_message],
        "resume": {"messages": [system_message, *resumed_user_messages]},
    }

    restore_trace_session(trace, ResumePreparation(vetted_files={}))

    assert st.session_state["messages"] == [system_message, *resumed_user_messages]
    assert st.session_state["count"] == 2
