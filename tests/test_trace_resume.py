import json

import pandas as pd
import pytest

from arctic_analytics.core.trace_resume import TraceResumeError, load_analysis_trace, messages_for_resume, prepare_resume


def uploaded_file(name, columns):
    return {
        "source_filename": name,
        "columns_names": pd.Index(columns),
        "data_types": pd.Series({column: "Int64" for column in columns}),
        "dataset_description": "",
        "primary_key": [],
        "dataframe": pd.DataFrame({column: [1] for column in columns}),
    }


def resumable_trace():
    return {
        "trace_schema_version": "0.3.0",
        "package_version": "0.1.0",
        "timestamp": "2026-09-05T00:00:00+00:00",
        "session_id": "original-session",
        "cost": 0,
        "context_window_usage": 0,
        "system_message": "System prompt",
        "prompt_str": "Question",
        "messages": [],
        "events": [],
        "tool_calls": [],
        "outputs": [],
        "dataset_metadata": {
            "sales": {
                "dataset_description": "Monthly sales.",
                "primary_key": ["id"],
                "data_types": {"id": "Int64", "amount": "Float64"},
                "data_dictionary": {"id": {"Column Name": "id", "Data Type": "Int64"}},
                "column_names": ["id", "amount"],
            }
        },
        "errors": [],
        "limitations": ["Not a deterministic replay."],
        "resume": {
            "resume_schema_version": "1.0",
            "source": "uploader",
            "datasets": [{
                "dataset_key": "sales",
                "source_filename": "Sales 2026.csv",
                "column_names": ["id", "amount"],
            }],
        },
    }


def test_load_analysis_trace_rejects_invalid_json_and_unknown_versions():
    with pytest.raises(TraceResumeError):
        load_analysis_trace(b"not json")

    with pytest.raises(TraceResumeError):
        load_analysis_trace(json.dumps({"trace_schema_version": "9.0.0"}).encode())

    assert load_analysis_trace(json.dumps(resumable_trace()).encode())["session_id"] == "original-session"


def test_prepare_resume_requires_original_filename_and_columns():
    trace = resumable_trace()
    uploaded = {"other": uploaded_file("Sales 2026.csv", ["id", "amount"])}

    preparation = prepare_resume(trace, uploaded)

    assert list(preparation.vetted_files) == ["sales"]
    assert preparation.vetted_files["sales"]["dataset_description"] == "Monthly sales."
    assert preparation.vetted_files["sales"]["primary_key"] == ["id"]

    with pytest.raises(TraceResumeError, match="original file"):
        prepare_resume(trace, {"other": uploaded_file("renamed.csv", ["id", "amount"])})
    with pytest.raises(TraceResumeError, match="original file"):
        prepare_resume(trace, {"other": uploaded_file("Sales 2026.csv", ["amount", "id"])})


@pytest.mark.parametrize(
    ("dataset_description", "primary_key"),
    [
        (None, ["id"]),
        ({"unexpected": "metadata"}, ["id"]),
        ("Monthly sales.", "id"),
        ("Monthly sales.", ["id", 1]),
    ],
)
def test_prepare_resume_sanitizes_untrusted_widget_metadata(dataset_description, primary_key):
    trace = resumable_trace()
    trace["dataset_metadata"]["sales"]["dataset_description"] = dataset_description
    trace["dataset_metadata"]["sales"]["primary_key"] = primary_key

    preparation = prepare_resume(trace, {"other": uploaded_file("Sales 2026.csv", ["id", "amount"])})

    restored = preparation.vetted_files["sales"]
    assert restored["dataset_description"] == (dataset_description if isinstance(dataset_description, str) else "")
    assert restored["primary_key"] == (primary_key if isinstance(primary_key, list) and all(isinstance(key, str) for key in primary_key) else [])


@pytest.mark.parametrize("source", [None, "sample"])
def test_prepare_resume_rejects_manifest_without_uploader_source(source):
    trace = resumable_trace()
    if source is None:
        del trace["resume"]["source"]
    else:
        trace["resume"]["source"] = source

    with pytest.raises(TraceResumeError, match="must declare uploader"):
        prepare_resume(trace, {"other": uploaded_file("Sales 2026.csv", ["id", "amount"])})


@pytest.mark.parametrize("manifest", [None, {}, {"resume_schema_version": "0.9"}])
def test_prepare_resume_rejects_missing_or_malformed_manifest(manifest):
    trace = resumable_trace()
    if manifest is None:
        del trace["resume"]
    else:
        trace["resume"] = manifest

    with pytest.raises(TraceResumeError, match="resume manifest"):
        prepare_resume(trace, {"fresh_name": uploaded_file("renamed.csv", ["id", "amount"])})


def test_messages_for_resume_uses_full_fidelity_messages_and_sanitizes_old_chart_descriptors():
    trace = resumable_trace()
    system_message = {
        "type": "message",
        "role": "system",
        "content": [{"type": "input_text", "text": "System prompt"}],
    }
    trace["messages"] = [system_message, {
        "type": "function_call_output",
        "output": [{"type": "input_image", "image_url": {"type": "image_base64"}}],
    }]

    assert messages_for_resume(trace)[1]["output"] == "Historical chart output is unavailable in this exported trace."

    trace["resume"]["messages"] = [system_message, {
        "type": "function_call_output",
        "output": [{"type": "input_image", "image_url": "data:image/png;base64,abc"}],
    }]
    assert messages_for_resume(trace)[1]["output"][0]["image_url"] == "data:image/png;base64,abc"


@pytest.mark.parametrize(
    "messages",
    [
        ["not a message"],
        [{"type": "message", "role": "user", "content": [{"text": "Question"}]}],
        [{"type": "message", "role": "system", "content": []}],
        [{"type": "message", "role": "system", "content": [{"text": None}]}],
    ],
)
def test_messages_for_resume_discards_histories_without_a_valid_system_message(messages):
    trace = resumable_trace()
    trace["resume"]["messages"] = messages

    assert messages_for_resume(trace) == []


@pytest.mark.parametrize("image_url", ["https://example.com/chart.png", "data:text/plain;base64,abc"])
def test_messages_for_resume_rejects_non_data_image_urls(image_url):
    trace = resumable_trace()
    trace["resume"]["messages"] = [{
        "type": "message",
        "role": "system",
        "content": [{"type": "input_text", "text": "System prompt"}],
    }, {
        "type": "function_call_output",
        "output": [{"type": "input_image", "image_url": image_url}],
    }]

    messages = messages_for_resume(trace)

    assert messages[1]["output"] == "Historical chart output is unavailable in this exported trace."


def test_load_analysis_trace_rejects_legacy_traces_without_resume_manifest():
    trace = resumable_trace()
    del trace["resume"]
    trace["trace_schema_version"] = "0.2.0"

    with pytest.raises(TraceResumeError, match="supported import format"):
        load_analysis_trace(json.dumps(trace).encode())
