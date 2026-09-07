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
