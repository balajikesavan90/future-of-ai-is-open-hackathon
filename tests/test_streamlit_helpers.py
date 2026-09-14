import pytest
import pandas as pd
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

pytest.importorskip("streamlit")

from arctic_analytics.streamlit import helpers


@pytest.mark.parametrize("mime_type", ["png", "jpeg", "gif", "webp"])
def test_render_tool_response_renders_supported_base64_images(monkeypatch, mime_type):
    rendered = []
    monkeypatch.setattr(helpers.st, "image", rendered.append)

    image_url = f"data:image/{mime_type};base64,AAAA"
    helpers.render_tool_response(image_url)

    assert rendered == [image_url]


def test_render_tool_response_previews_and_offers_download_for_large_text(monkeypatch):
    rendered = {"warning": [], "code": [], "download": []}
    tool_response = "{" + ("x" * helpers.MAX_RENDERED_TOOL_RESPONSE_CHARS) + "}"

    monkeypatch.setattr(helpers.st, "warning", rendered["warning"].append)
    monkeypatch.setattr(
        helpers.st,
        "code",
        lambda value, **kwargs: rendered["code"].append((value, kwargs)),
    )
    monkeypatch.setattr(
        helpers.st,
        "download_button",
        lambda *args, **kwargs: rendered["download"].append((args, kwargs)),
    )
    monkeypatch.setattr(helpers.json, "loads", lambda _value: pytest.fail("large output must not be parsed"))

    helpers.render_tool_response(tool_response)

    assert rendered["warning"]
    assert rendered["code"] == [(tool_response[:helpers.MAX_RENDERED_TOOL_RESPONSE_CHARS], {"language": "json"})]
    assert rendered["download"][0][0] == ("Download full tool output",)
    assert rendered["download"][0][1]["data"] == tool_response


def test_render_tool_response_uses_output_id_for_large_download_key(monkeypatch):
    keys = []
    tool_response = "x" * (helpers.MAX_RENDERED_TOOL_RESPONSE_CHARS + 1)

    monkeypatch.setattr(helpers.st, "warning", lambda _message: None)
    monkeypatch.setattr(helpers.st, "code", lambda _value, **_kwargs: None)
    monkeypatch.setattr(
        helpers.st,
        "download_button",
        lambda *_args, **kwargs: keys.append(kwargs["key"]),
    )

    helpers.render_tool_response(tool_response, output_id="call_1")
    helpers.render_tool_response(tool_response, output_id="call_2")

    assert keys == ["tool-output-call_1", "tool-output-call_2"]


def test_render_tool_response_renders_large_dataframe_json_as_a_table(monkeypatch):
    rendered_dataframes = []
    tool_response = pd.DataFrame({"text": ["x" * 1_000] * 100}).to_json(orient="index")
    assert len(tool_response) > helpers.MAX_RENDERED_TOOL_RESPONSE_CHARS

    monkeypatch.setattr(helpers.st, "dataframe", lambda dataframe, **_kwargs: rendered_dataframes.append(dataframe))
    monkeypatch.setattr(helpers.st, "code", lambda *_args, **_kwargs: pytest.fail("table JSON must not use text preview"))

    assert helpers.render_tool_response(tool_response) is True

    assert rendered_dataframes[0].shape == (100, 1)


def test_render_tool_response_offers_retained_raw_download_for_dataframe(monkeypatch, tmp_path):
    rendered = []
    full_response = pd.DataFrame({"value": [1, 2]}).to_json(orient="index")
    retained_path = tmp_path / "retained-output.json"
    retained_path.write_text(full_response, encoding="utf-8")

    monkeypatch.setattr(helpers.st, "dataframe", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        helpers.st,
        "download_button",
        lambda *args, **kwargs: rendered.append((args, kwargs)),
    )

    assert helpers.render_tool_response("preview", full_output_path=str(retained_path)) is True
    assert rendered[0][0] == ("Download full tool output",)
    assert rendered[0][1]["data"] == full_response.encode("utf-8")


def test_render_tool_response_renders_complete_rows_from_truncated_dataframe_json(monkeypatch):
    rendered_dataframes = []
    full_response = pd.DataFrame({"text": ["x" * 1_000] * 100}).to_json(orient="index")
    preview = full_response[:helpers.MAX_RENDERED_TOOL_RESPONSE_CHARS]

    monkeypatch.setattr(helpers.st, "dataframe", lambda dataframe, **_kwargs: rendered_dataframes.append(dataframe))
    monkeypatch.setattr(helpers.st, "code", lambda *_args, **_kwargs: pytest.fail("table preview must not use text rendering"))

    assert helpers.render_tool_response(preview) is True

    assert 0 < rendered_dataframes[0].shape[0] < 100
    assert rendered_dataframes[0].iloc[0, 0] == "x" * 1_000


def test_render_tool_response_replays_retained_dataframe_instead_of_partial_json(monkeypatch, tmp_path):
    rendered_dataframes = []
    full_response = pd.DataFrame({"text": ["x" * 1_000] * 100}).to_json(orient="index")
    retained_path = tmp_path / "retained-output.json"
    retained_path.write_text(full_response, encoding="utf-8")

    monkeypatch.setattr(helpers.st, "dataframe", lambda dataframe, **_kwargs: rendered_dataframes.append(dataframe))
    monkeypatch.setattr(helpers.st, "code", lambda *_args, **_kwargs: pytest.fail("retained table JSON must not use text preview"))

    assert helpers.render_tool_response(
        full_response[:helpers.MAX_RENDERED_TOOL_RESPONSE_CHARS],
        full_output_path=str(retained_path),
    ) is True

    assert rendered_dataframes[0].shape == (100, 1)


def test_render_tool_response_reads_retained_file_for_download(monkeypatch, tmp_path):
    rendered = []
    retained_path = tmp_path / "retained-output.txt"
    retained_path.write_text("complete output", encoding="utf-8")

    monkeypatch.setattr(helpers.st, "code", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(helpers.st, "download_button", lambda *args, **kwargs: rendered.append((args, kwargs)))

    helpers.render_tool_response("preview", full_output_path=str(retained_path))

    assert rendered[0][1]["data"] == b"complete output"


def test_render_tool_response_handles_unreadable_retained_file(monkeypatch, tmp_path):
    retained_path = tmp_path / "retained-output.txt"
    retained_path.write_text("complete output", encoding="utf-8")
    warnings = []

    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unreadable")),
    )
    monkeypatch.setattr(helpers.st, "code", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(helpers.st, "warning", warnings.append)
    monkeypatch.setattr(
        helpers.st,
        "download_button",
        lambda *_args, **_kwargs: pytest.fail("unreadable output must not offer a download"),
    )

    helpers.render_tool_response("preview", full_output_path=str(retained_path))

    assert "cannot be downloaded" in warnings[-1]


def test_retained_tool_output_path_ignores_non_string_id():
    assert helpers.retained_tool_output_path(["malformed"]) is None


def test_extract_raw_outputs_discards_imported_retained_file_path(monkeypatch):
    monkeypatch.setattr(helpers, "retained_tool_output_path", lambda _output_id: None)

    outputs = helpers._extract_raw_outputs([{
        "type": "function_call_output",
        "call_id": "call_1",
        "output": "Model-facing output.",
        "_retained_output_path": "/etc/passwd",
    }])

    assert "_retained_output_path" not in outputs[0]


def test_retain_tool_output_uses_generated_filename_and_enforces_limit(monkeypatch):
    session_state = {}
    monkeypatch.setattr(helpers, "st", SimpleNamespace(session_state=session_state))
    monkeypatch.setattr(helpers, "MAX_RETAINED_TOOL_OUTPUT_BYTES", 3)

    retained_path = helpers.retain_tool_output("../../outside", "abc")

    assert retained_path is not None
    assert Path(retained_path).parent == Path(
        session_state[helpers.RETAINED_TOOL_OUTPUT_DIRECTORY_KEY].name
    )
    assert Path(retained_path).name != "../../outside.txt"
    assert helpers.retain_tool_output("second", "abcd") is None

    helpers.clear_retained_tool_outputs()


def test_retain_tool_output_falls_back_when_temp_storage_write_fails(monkeypatch):
    session_state = {}
    monkeypatch.setattr(helpers, "st", SimpleNamespace(session_state=session_state))
    monkeypatch.setattr(Path, "write_bytes", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("full")))

    assert helpers.retain_tool_output("call_1", "output") is None
    assert session_state[helpers.RETAINED_TOOL_OUTPUTS_KEY] == {}

    helpers.clear_retained_tool_outputs()


def test_retain_tool_output_falls_back_when_temp_storage_creation_fails(monkeypatch):
    session_state = {}
    monkeypatch.setattr(helpers, "st", SimpleNamespace(session_state=session_state))
    monkeypatch.setattr(
        helpers.tempfile,
        "TemporaryDirectory",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
    )

    assert helpers.retain_tool_output("call_1", "output") is None
    assert helpers.RETAINED_TOOL_OUTPUT_DIRECTORY_KEY not in session_state


def test_render_ai_prompt_hides_user_visible_tool_output(monkeypatch):
    rendered = []
    fake_streamlit = SimpleNamespace(
        session_state={
            "session_id": "test-session",
            "messages": [
                {"role": "system", "content": [{"text": "System instructions."}]},
                {
                    "type": "function_call_output",
                    "output": "Model-facing output.",
                    "display_output": "User-visible output.",
                },
            ],
        },
        sidebar=SimpleNamespace(expander=lambda *_args, **_kwargs: nullcontext()),
        subheader=lambda *_args, **_kwargs: None,
        write=rendered.append,
    )
    monkeypatch.setattr(helpers, "st", fake_streamlit)
    monkeypatch.setattr(helpers, "render_trace_export", lambda: None)

    helpers.render_ai_prompt()

    assert rendered == [[{"type": "function_call_output", "output": "Model-facing output."}]]
