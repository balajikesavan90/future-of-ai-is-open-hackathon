import base64
import io
import os
from types import SimpleNamespace

import pytest
from PIL import Image

import arctic_analytics.llm.openai_responses as openai_responses
from arctic_analytics.config import MAX_MODEL_CONTEXT_TOKENS
from arctic_analytics.llm.openai_responses import OpenAIResponsesUtility


def test_calculate_cost_returns_numeric_cost_for_known_model():
    client = OpenAIResponsesUtility()

    assert client._calculate_cost(1_000_000, 1_000_000, "gpt-5.6-luna") == pytest.approx(1.4)


def test_prepare_api_args_uses_reasoning_configuration_for_gpt_6_astra():
    client = OpenAIResponsesUtility()

    args = client._prepare_api_args(
        messages=[{"content": [{"text": "Follow these instructions."}]}],
        model="gpt-6-astra",
        response_format=None,
        reasoning_effort="low",
        tools=[],
        tool_choice="auto",
        include=[],
    )

    assert "temperature" not in args
    assert args["reasoning"] == {"effort": "low", "summary": "auto"}


def test_client_uses_session_api_key_without_mutating_environment(monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, api_key):
            captured["api_key"] = api_key

    monkeypatch.setattr(
        openai_responses,
        "st",
        SimpleNamespace(secrets={}, session_state={"OPENAI_API_KEY": "from-session"}),
    )
    monkeypatch.setattr(openai_responses, "OpenAI", FakeOpenAI)
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")

    client = OpenAIResponsesUtility()._client()

    assert isinstance(client, FakeOpenAI)
    assert captured["api_key"] == "from-session"
    assert os.environ["OPENAI_API_KEY"] == "from-env"


def test_client_is_reused_until_api_key_changes(monkeypatch):
    created_clients = []
    session_state = {"OPENAI_API_KEY": "first-key"}

    class FakeOpenAI:
        def __init__(self, api_key):
            self.api_key = api_key
            created_clients.append(self)

    monkeypatch.setattr(
        openai_responses,
        "st",
        SimpleNamespace(secrets={}, session_state=session_state),
    )
    monkeypatch.setattr(openai_responses, "OpenAI", FakeOpenAI)

    utility = OpenAIResponsesUtility()
    first_client = utility._client()
    second_client = utility._client()
    session_state["OPENAI_API_KEY"] = "second-key"
    third_client = utility._client()

    assert second_client is first_client
    assert third_client is not first_client
    assert [client.api_key for client in created_clients] == ["first-key", "second-key"]


def test_calculate_cost_rejects_unknown_model():
    client = OpenAIResponsesUtility()

    with pytest.raises(ValueError, match="Pricing has not been configured"):
        client._calculate_cost(100, 100, "unknown-model")


@pytest.mark.parametrize(
    "model",
    [
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
        "gpt-6-astra",
    ],
)
def test_calculate_context_window_usage_uses_application_limit(model):
    client = OpenAIResponsesUtility()

    assert client._calculate_context_window_usage(MAX_MODEL_CONTEXT_TOKENS, model) == pytest.approx(1.0)
    assert client._calculate_context_window_usage(MAX_MODEL_CONTEXT_TOKENS // 2, model) == pytest.approx(0.5)


def test_calculate_context_window_usage_rejects_unknown_model():
    client = OpenAIResponsesUtility()

    with pytest.raises(ValueError, match="is not supported"):
        client._calculate_context_window_usage(100, "unknown-model")


def test_request_context_limit_rejects_oversized_requests():
    class FixedTokenEncoding:
        def encode(self, _value):
            return [0] * (MAX_MODEL_CONTEXT_TOKENS + 1)

    client = OpenAIResponsesUtility()
    client.enc_gpt4 = FixedTokenEncoding()

    with pytest.raises(ValueError, match="128,000-token limit"):
        client._enforce_request_context_limit({"input": []})


def test_request_context_estimates_image_tokens_without_counting_base64_as_text():
    image_buffer = io.BytesIO()
    Image.new("RGB", (1_000, 800)).save(image_buffer, format="PNG")
    image_url = "data:image/png;base64," + base64.b64encode(image_buffer.getvalue()).decode()

    class TextOnlyEncoding:
        def encode(self, value):
            assert image_url not in value
            return []

    client = OpenAIResponsesUtility()
    client.enc_gpt4 = TextOnlyEncoding()

    token_count = client._request_context_token_count(
        {
            "model": "gpt-5.6-luna",
            "input": [{"type": "function_call_output", "output": [{"type": "input_image", "image_url": image_url}]}],
        }
    )

    assert token_count == 960


def test_response_context_usage_excludes_generated_tokens():
    response = SimpleNamespace(
        output=[],
        usage=SimpleNamespace(
            input_tokens=MAX_MODEL_CONTEXT_TOKENS // 2,
            output_tokens=MAX_MODEL_CONTEXT_TOKENS // 2,
        ),
    )

    _tool_calls, _cost, _messages, context_usage, context_tokens = OpenAIResponsesUtility()._process_api_response(
        response, [], "gpt-5.6-luna"
    )

    assert context_usage == pytest.approx(0.5)
    assert context_tokens == MAX_MODEL_CONTEXT_TOKENS // 2
