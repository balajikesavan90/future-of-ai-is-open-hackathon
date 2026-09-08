import streamlit as st

from arctic_analytics.llm import ai
from arctic_analytics.streamlit.helpers import select_sample_prompt


class StubResponsesClient:
    def generate_openai_response(self, vetted_files, model):
        return ("responses", vetted_files, model)


def test_generate_ai_response_dispatches_to_tool_calling_analysis(monkeypatch):
    st.session_state["session_id"] = "test-session"
    monkeypatch.setattr(ai, "openai_responses_client", StubResponsesClient())

    assert ai.generate_ai_response({}, "gpt-5.6-luna") == (
        "responses",
        {},
        "gpt-5.6-luna",
    )


def test_select_sample_prompt_queues_prompt_for_rerun():
    st.session_state.clear()

    select_sample_prompt("Analyze the sample data")

    assert st.session_state["pending_sample_prompt"] == "Analyze the sample data"
    assert st.session_state["agent_turn_state"] == "queued"
    assert st.session_state["show_sample"] is False
    assert st.session_state["disable_sample_button"] is True
