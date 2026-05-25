import streamlit as st

from arctic_analytics.llm import ai


class StubResponsesClient:
    def generate_openai_response(self, vetted_files, model):
        return ("responses", vetted_files, model)


def test_generate_ai_response_dispatches_to_tool_calling_analysis(monkeypatch):
    st.session_state["session_id"] = "test-session"
    monkeypatch.setattr(ai, "openai_responses_client", StubResponsesClient())

    assert ai.generate_ai_response({}, "gpt-5.4-mini-2026-03-17") == (
        "responses",
        {},
        "gpt-5.4-mini-2026-03-17",
    )
