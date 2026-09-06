import os
from types import SimpleNamespace

import pytest

import arctic_analytics.llm.openai_responses as openai_responses
from arctic_analytics.llm.openai_responses import OpenAIResponsesUtility


def test_calculate_cost_returns_numeric_cost_for_known_model():
    client = OpenAIResponsesUtility()

    assert client._calculate_cost(1_000_000, 1_000_000, "gpt-5.6-luna") == pytest.approx(1.4)


def test_prepare_api_args_uses_reasoning_configuration_for_gpt_6_astra():
    client = OpenAIResponsesUtility()

    args = client._prepare_api_args(
        messages=[{"content": [{"text": "Follow these instructions."}]}],
        model="gpt-6-astra",
        temperature=0.1,
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
    ("model", "context_window_tokens"),
    [
        ("gpt-5.6-luna", 1_050_000),
        ("gpt-5.6-terra", 1_050_000),
        ("gpt-5.6-sol", 1_050_000),
        ("gpt-6-astra", 1_050_000),
    ],
)
def test_calculate_context_window_usage_for_supported_models(model, context_window_tokens):
    client = OpenAIResponsesUtility()

    assert client._calculate_context_window_usage(context_window_tokens, model) == pytest.approx(1.0)


def test_calculate_context_window_usage_rejects_unknown_model():
    client = OpenAIResponsesUtility()

    with pytest.raises(ValueError, match="Context window has not been configured"):
        client._calculate_context_window_usage(100, "unknown-model")
