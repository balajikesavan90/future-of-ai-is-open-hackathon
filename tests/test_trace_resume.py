import json
import warnings

import pandas as pd
import pytest
from PIL import Image

from arctic_analytics.core import trace_resume
from arctic_analytics.core.trace_resume import (
    TraceResumeError,
    load_analysis_trace,
    messages_for_resume,
    prepare_resume,
    replace_resumed_system_message,
)

VALID_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"
)


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


def test_load_analysis_trace_converts_excessive_nesting_to_trace_resume_error():
    with pytest.raises(TraceResumeError, match="valid UTF-8"):
        load_analysis_trace(b'{"nested":' * 2_000 + b"0" + b"}" * 2_000)


@pytest.mark.parametrize("nonfinite", ["NaN", "Infinity", "-Infinity", "1e400"])
def test_load_analysis_trace_rejects_nonfinite_numbers(nonfinite):
    payload = json.dumps(resumable_trace()).replace('"cost": 0', f'"cost": {nonfinite}').encode()

    with pytest.raises(TraceResumeError, match="non-finite|valid UTF-8"):
        load_analysis_trace(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("system_message", None),
        ("prompt_str", {"type": "text", "preview": "Question", "truncated": True}),
        ("system_message", ["unexpected"]),
        ("prompt_str", 42),
        ("system_message", False),
    ],
)
def test_load_analysis_trace_validates_system_message_and_prompt_types(field, value):
    trace = resumable_trace()
    trace[field] = value

    if isinstance(value, (list, int, bool)) and value is not None:
        with pytest.raises(TraceResumeError, match="supported import format"):
            load_analysis_trace(json.dumps(trace).encode())
    else:
        assert load_analysis_trace(json.dumps(trace).encode())[field] == value


def test_prepare_resume_requires_original_filename_and_columns():
    trace = resumable_trace()
    uploaded = {"other": uploaded_file("Sales 2026.csv", ["id", "amount"])}

    preparation = prepare_resume(trace, uploaded)

    assert list(preparation.vetted_files) == ["sales"]
    assert preparation.vetted_files["sales"]["dataset_description"] == "Monthly sales."
    assert preparation.vetted_files["sales"]["primary_key"] == ["id"]

    with pytest.raises(TraceResumeError, match="file named"):
        prepare_resume(trace, {"other": uploaded_file("renamed.csv", ["id", "amount"])})
    with pytest.raises(TraceResumeError, match="file named"):
        prepare_resume(trace, {"other": uploaded_file("Sales 2026.csv", ["amount", "id"])})


@pytest.mark.parametrize(
    "dataset_key", ["pd", "st", "get_dataframe_names", "__builtins__", "invalid-key", "class"],
)
def test_prepare_resume_rejects_unsafe_dataset_keys(dataset_key):
    trace = resumable_trace()
    trace["resume"]["datasets"][0]["dataset_key"] = dataset_key

    with pytest.raises(TraceResumeError, match="incomplete"):
        prepare_resume(trace, {"other": uploaded_file("Sales 2026.csv", ["id", "amount"])})


def test_prepare_resume_accepts_refreshed_content_with_matching_structure():
    trace = resumable_trace()
    uploaded = uploaded_file("Sales 2026.csv", ["id", "amount"])
    uploaded["dataframe"] = pd.DataFrame({"id": [999], "amount": [0]})

    resumed = prepare_resume(trace, {"sales": uploaded})

    assert resumed.vetted_files["sales"]["dataframe"].iloc[0].to_dict() == {"id": 999, "amount": 0}


def test_prepare_resume_matches_duplicate_identical_filenames_in_order():
    trace = resumable_trace()
    duplicate = dict(trace["resume"]["datasets"][0])
    duplicate["dataset_key"] = "sales_copy"
    trace["resume"]["datasets"].append(duplicate)
    trace["dataset_metadata"]["sales_copy"] = {}
    first = uploaded_file("Sales 2026.csv", ["id", "amount"])
    second = uploaded_file("Sales 2026.csv", ["id", "amount"])

    restored = prepare_resume(trace, {"first": first, "second": second}).vetted_files

    assert list(restored) == ["sales", "sales_copy"]
    assert restored["sales"] is not restored["sales_copy"]


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


def test_prepare_resume_restores_data_dictionary_only_when_columns_match():
    trace = resumable_trace()
    uploaded = {"other": uploaded_file("Sales 2026.csv", ["id", "amount"])}
    trace["dataset_metadata"]["sales"]["data_dictionary"] = {
        "id": {"Column Name": "id", "Data Type": "Int64"},
        "amount": {"Column Name": "amount", "Data Type": "Float64"},
    }

    restored = prepare_resume(trace, uploaded).vetted_files["sales"]
    assert json.loads(restored["data_dictionary_json"]) == trace["dataset_metadata"]["sales"]["data_dictionary"]

    trace["dataset_metadata"]["sales"]["data_dictionary"] = {
        "id": {"Column Name": "id", "Data Type": "Int64"},
        "stale": {"Column Name": "removed", "Data Type": "Int64"},
    }
    restored = prepare_resume(trace, uploaded).vetted_files["sales"]
    assert "data_dictionary_json" not in restored


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
        "type": "function_call",
        "call_id": "call_1",
        "name": "render_chart",
        "arguments": "{}",
    }, {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": [{"type": "input_image", "image_url": {"type": "image_base64"}}],
    }]

    assert messages_for_resume(trace)[2]["output"] == "Historical chart output is unavailable in this exported trace."

    trace["resume"]["messages"] = [system_message, {
        "type": "function_call",
        "call_id": "call_1",
        "name": "render_chart",
        "arguments": "{}",
    }, {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": [{"type": "input_image", "image_url": VALID_PNG_DATA_URL}],
    }]
    assert messages_for_resume(trace)[2]["output"][0]["image_url"] == VALID_PNG_DATA_URL


def test_messages_for_resume_preserves_user_visible_display_output():
    trace = resumable_trace()
    system_message = {
        "type": "message",
        "role": "system",
        "content": [{"type": "input_text", "text": "System prompt"}],
    }
    trace["resume"]["messages"] = [system_message, {
        "type": "function_call",
        "call_id": "call_1",
        "name": "run_python_expression",
        "arguments": "{}",
    }, {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": "Compact model-facing notice.",
        "display_output": "Full user-visible result.",
    }]

    restored = messages_for_resume(trace)

    assert restored[-1]["output"] == "Compact model-facing notice."
    assert restored[-1]["display_output"] == "Full user-visible result."


def test_messages_for_resume_discards_non_dict_history_items():
    trace = resumable_trace()
    system_message = {
        "type": "message",
        "role": "system",
        "content": [{"type": "input_text", "text": "System prompt"}],
    }
    tool_call = {"type": "function_call", "name": "run_python_expression"}
    trace["resume"]["messages"] = [system_message, "unexpected", 42, tool_call]

    assert messages_for_resume(trace) == []


def test_messages_for_resume_discards_history_with_invalid_later_content_item():
    trace = resumable_trace()
    trace["resume"]["messages"] = [{
        "type": "message",
        "role": "system",
        "content": [{"type": "input_text", "text": "System prompt"}],
    }, {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": "Continue"}, "invalid"],
    }]

    assert messages_for_resume(trace) == []


def test_messages_for_resume_discards_history_with_multiple_text_items():
    trace = resumable_trace()
    trace["resume"]["messages"] = [{
        "type": "message",
        "role": "system",
        "content": [{"type": "input_text", "text": "System prompt"}],
    }, {
        "type": "message",
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Visible question"},
            {"type": "input_text", "text": "Hidden question"},
        ],
    }]

    assert messages_for_resume(trace) == []


@pytest.mark.parametrize(
    ("role", "content_type"),
    [("system", "output_text"), ("user", "output_text"), ("assistant", "input_text")],
)
def test_messages_for_resume_discards_role_incompatible_content(role, content_type):
    trace = resumable_trace()
    trace["resume"]["messages"] = [{
        "type": "message",
        "role": "system",
        "content": [{"type": "input_text", "text": "System prompt"}],
    }, {
        "type": "message",
        "role": role,
        "content": [{"type": content_type, "text": "Wrong role"}],
    }]

    assert messages_for_resume(trace) == []


@pytest.mark.parametrize(
    "message",
    [
        {"type": "function_call", "call_id": "", "name": "run_python_expression", "arguments": "{}"},
        {"type": "function_call", "call_id": "  ", "name": "run_python_expression", "arguments": "{}"},
        {"type": "function_call_output", "call_id": None, "output": "result"},
        {"type": "function_call_output", "output": "result"},
    ],
)
def test_messages_for_resume_discards_history_with_invalid_tool_call_id(message):
    trace = resumable_trace()
    trace["resume"]["messages"] = [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "System prompt"}],
        },
        message,
    ]

    assert messages_for_resume(trace) == []


def test_messages_for_resume_keeps_history_with_tool_call_ids():
    trace = resumable_trace()
    trace["resume"]["messages"] = [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "System prompt"}],
        },
        {"type": "function_call", "call_id": "call_1", "name": "run_python_expression", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_1", "output": "result"},
    ]

    assert messages_for_resume(trace) == trace["resume"]["messages"]


@pytest.mark.parametrize(
    "output",
    [{}, [42], [], [{"type": "input_image", "image_url": VALID_PNG_DATA_URL, "extra": True}]],
)
def test_messages_for_resume_discards_unsupported_tool_output_shapes(output):
    trace = resumable_trace()
    trace["resume"]["messages"] = [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "System prompt"}],
        },
        {"type": "function_call", "call_id": "call_1", "name": "render_chart", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_1", "output": output},
    ]

    assert messages_for_resume(trace) == []


@pytest.mark.parametrize(
    "history",
    [
        [
            {"type": "function_call_output", "call_id": "call_1", "output": "result"},
        ],
        [
            {"type": "function_call", "call_id": "call_1", "name": "tool", "arguments": "{}"},
        ],
        [
            {"type": "function_call", "call_id": "call_1", "name": "tool", "arguments": "{}"},
            {"type": "function_call", "call_id": "call_1", "name": "tool", "arguments": "{}"},
        ],
        [
            {"type": "function_call", "call_id": "call_1", "name": "tool", "arguments": "{}"},
            {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Oops"}]},
            {"type": "function_call_output", "call_id": "call_1", "output": "result"},
        ],
    ],
)
def test_messages_for_resume_discards_invalid_tool_call_sequences(history):
    trace = resumable_trace()
    trace["resume"]["messages"] = [{
        "type": "message",
        "role": "system",
        "content": [{"type": "input_text", "text": "System prompt"}],
    }, *history]

    assert messages_for_resume(trace) == []


def test_replace_resumed_system_message_preserves_following_history():
    history = [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "Old system prompt"}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Continue the analysis."}],
        },
    ]

    rebuilt = replace_resumed_system_message(history, "Reviewed system prompt")

    assert rebuilt[0]["content"][0]["text"] == "Reviewed system prompt"
    assert rebuilt[1:] == history[1:]


@pytest.mark.parametrize(
    "invalid_message",
    [
        {},
        {"type": "message", "role": "assistant", "content": []},
        {"type": "function_call", "name": "run_python_expression"},
    ],
)
def test_messages_for_resume_discards_entire_history_when_any_message_is_invalid(invalid_message):
    trace = resumable_trace()
    trace["resume"]["messages"] = [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "System prompt"}],
        },
        invalid_message,
    ]

    assert messages_for_resume(trace) == []


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


def test_messages_for_resume_discards_history_with_later_system_message():
    trace = resumable_trace()
    trace["resume"]["messages"] = [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "System prompt"}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Continue"}],
        },
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "Hidden instruction"}],
        },
    ]

    assert messages_for_resume(trace) == []


def test_resumed_image_validation_discards_decompression_bombs(monkeypatch):
    def raise_decompression_bomb(*args, **kwargs):
        raise Image.DecompressionBombError("too many pixels")

    monkeypatch.setattr(trace_resume.Image, "open", raise_decompression_bomb)

    assert not trace_resume._is_valid_base64_image_data_url(VALID_PNG_DATA_URL)


def test_resumed_image_validation_discards_decompression_bomb_warnings(monkeypatch):
    def warn_decompression_bomb(*args, **kwargs):
        warnings.warn("too many pixels", Image.DecompressionBombWarning)

    monkeypatch.setattr(trace_resume.Image, "open", warn_decompression_bomb)

    assert not trace_resume._is_valid_base64_image_data_url(VALID_PNG_DATA_URL)


@pytest.mark.parametrize(
    "image_url", ["https://example.com/chart.png", "data:text/plain;base64,abc", "data:image/png;base64,abc"],
)
def test_messages_for_resume_rejects_non_data_image_urls(image_url):
    trace = resumable_trace()
    trace["resume"]["messages"] = [{
        "type": "message",
        "role": "system",
        "content": [{"type": "input_text", "text": "System prompt"}],
    }, {
        "type": "function_call",
        "call_id": "call_1",
        "name": "render_chart",
        "arguments": "{}",
    }, {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": [{"type": "input_image", "image_url": image_url}],
    }]

    messages = messages_for_resume(trace)

    assert messages[2]["output"] == "Historical chart output is unavailable in this exported trace."


def test_load_analysis_trace_rejects_legacy_traces_without_resume_manifest():
    trace = resumable_trace()
    del trace["resume"]
    trace["trace_schema_version"] = "0.2.0"

    with pytest.raises(TraceResumeError, match="supported import format"):
        load_analysis_trace(json.dumps(trace).encode())
