# Deprecated Legacy Code

This directory contains archived code that is not part of the supported Arctic Analytics workflow.

## Reason

Arctic Analytics now focuses on Tool-Calling Analysis for metadata-aware, transparent, and constrained AI-assisted analysis over structured data. The legacy code supports older identities that are out of scope:

- code-generation-only Data Analyst workflow
- document/debug assistant workflow
- Snowflake-specific ingestion and model experiments
- Replicate-hosted Llama/Mistral experiments
- broad chat-with-data framing

## Replacement

Use the active Tool-Calling Analysis path:

- UI: `src/arctic_analytics/streamlit/widgets/analytics_agent.py`
- prompt construction: `src/arctic_analytics/core/system_messages.py`
- tool-calling LLM integration: `src/arctic_analytics/llm/openai_responses.py`
- constrained execution: `src/arctic_analytics/core/security.py`
- trace export: `src/arctic_analytics/streamlit/helpers.py`

## Removal Timeline

These files are retained only as temporary migration context for the 0.1.x line. They should be deleted before a 0.2.0 release unless a specific archived reference is still needed for a migration note.
