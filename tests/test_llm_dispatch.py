from arctic_analytics.llm import ai
import streamlit as st


class StubLlamaClient:
    def generate_llama_response(self, vetted_files, model, agent_model):
        return ("llama", vetted_files, model, agent_model)


class StubResponsesClient:
    def generate_openai_response(self, vetted_files, model):
        return ("responses", vetted_files, model)


class StubChatClient:
    def generate_openai_chat_completions_response(self, vetted_files, model):
        return ("chat", vetted_files, model)


def test_generate_ai_response_dispatches_to_llama(monkeypatch):
    st.session_state["session_id"] = "test-session"
    monkeypatch.setattr(ai, "llama_client", StubLlamaClient())

    assert ai.generate_ai_response({}, "meta/llama-4-scout-instruct") == (
        "llama",
        {},
        "meta/llama-4-scout-instruct",
        False,
    )


def test_generate_ai_response_dispatches_to_openai_responses(monkeypatch):
    st.session_state["session_id"] = "test-session"
    monkeypatch.setattr(ai, "openai_responses_client", StubResponsesClient())

    assert ai.generate_ai_response({}, "gpt-5-mini-2025-08-07", agent_model=True) == (
        "responses",
        {},
        "gpt-5-mini-2025-08-07",
    )


def test_generate_ai_response_dispatches_to_openai_chat(monkeypatch):
    st.session_state["session_id"] = "test-session"
    monkeypatch.setattr(ai, "openai_chat_completions_client", StubChatClient())

    assert ai.generate_ai_response({}, "gpt-5-nano-2025-08-07", agent_model=False) == (
        "chat",
        {},
        "gpt-5-nano-2025-08-07",
    )
