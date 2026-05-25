import pytest

from arctic_analytics.llm.openai_responses import OpenAIResponsesUtility


def test_calculate_cost_returns_numeric_cost_for_known_model():
    client = OpenAIResponsesUtility()

    assert client._calculate_cost(1_000_000, 1_000_000, "gpt-5-nano-2025-08-07") == pytest.approx(0.45)


def test_calculate_cost_rejects_unknown_model():
    client = OpenAIResponsesUtility()

    with pytest.raises(ValueError, match="not recognized for cost calculation"):
        client._calculate_cost(100, 100, "unknown-model")
