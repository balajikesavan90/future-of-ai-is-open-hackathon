import pytest

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
