import pytest

from arctic_analytics.llm.openai_responses import OpenAIResponsesUtility


def test_calculate_cost_returns_numeric_cost_for_known_model():
    client = OpenAIResponsesUtility()

    assert client._calculate_cost(1_000_000, 1_000_000, "gpt-5.4-nano-2026-03-17") == pytest.approx(1.45)


def test_calculate_cost_rejects_unknown_model():
    client = OpenAIResponsesUtility()

    with pytest.raises(ValueError, match="not recognized for cost calculation"):
        client._calculate_cost(100, 100, "unknown-model")


@pytest.mark.parametrize(
    ("model", "context_window_tokens"),
    [
        ("gpt-5.4-mini-2026-03-17", 400_000),
        ("gpt-5.4-nano-2026-03-17", 400_000),
        ("gpt-5.4-2026-03-05", 1_050_000),
        ("gpt-5.5-2026-04-23", 1_050_000),
    ],
)
def test_calculate_context_window_usage_for_supported_models(model, context_window_tokens):
    client = OpenAIResponsesUtility()

    assert client._calculate_context_window_usage(context_window_tokens, model) == pytest.approx(1.0)


def test_calculate_context_window_usage_rejects_unknown_model():
    client = OpenAIResponsesUtility()

    with pytest.raises(ValueError, match="not recognized for context window usage calculation"):
        client._calculate_context_window_usage(100, "unknown-model")
