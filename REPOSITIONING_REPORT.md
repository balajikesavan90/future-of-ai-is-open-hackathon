# Repositioning Report

## Summary

Arctic Analytics has been narrowed to an experimental open-source framework for metadata-aware, transparent, and constrained AI-assisted analysis over structured data.

The supported workflow is now Tool-Calling Analysis only.

## Files Changed

- `README.md`: updated positioning, setup, documentation links, and removed Replicate setup.
- `CONTRIBUTING.md`: narrowed contribution scope and updated repository references.
- `CITATION.cff`, `.zenodo.json`: replaced generic charting/document-debug claims with metadata-aware, transparent, constrained structured-analysis framing.
- `pyproject.toml`, `poetry.lock`: removed obsolete Snowflake and Replicate dependencies and updated repository metadata.
- `src/arctic_analytics/streamlit/widgets/home.py`: removed mode toggle and always routes to Tool-Calling Analysis.
- `src/arctic_analytics/streamlit/widgets/analytics_agent.py`: updated user-facing terminology and calls the supported analysis dispatch.
- `src/arctic_analytics/streamlit/widgets/prompt_guide.py`: collapsed prompt guidance to Tool-Calling Analysis.
- `src/arctic_analytics/streamlit/widgets/about.py`: removed hackathon/personal/dual-mode framing.
- `src/arctic_analytics/streamlit/widgets/data_dictionary.py`: removed active Snowflake source handling.
- `src/arctic_analytics/streamlit/helpers.py`: renamed reset and trace metadata from agent-specific state to analysis state.
- `src/arctic_analytics/streamlit_app.py`: simplified reset routing for the single analysis mode.
- `src/arctic_analytics/core/system_messages.py`: removed document/debug prompts and non-agent prompt branch.
- `src/arctic_analytics/core/data_import.py`: removed active Snowflake import and ingestion path.
- `src/arctic_analytics/llm/ai.py`: reduced dispatch to the OpenAI Responses tool-calling path.
- `docs/research_questions.md`: removed debugging-oriented export language.
- `tests/*`: removed compatibility-shim and non-agent dispatch expectations.

## Files Added

- `CLEANUP_PLAN.md`: repository inventory and cleanup plan.
- `SECURITY.md`: explicit execution restrictions, blocked imports, timeout behavior, missing isolation boundaries, and residual risks.
- `docs/architecture.md`: workflow diagram and module map.
- `.github/workflows/tests.yml`: CI workflow running `poetry install` and `poetry run pytest`.
- `examples/README.md`: inspectability walkthrough.
- `examples/sample_dataset.csv`: sample structured dataset.
- `examples/sample_metadata.json`: sample editable metadata.
- `examples/sample_trace_export.json`: representative trace export.
- `src/arctic_analytics/legacy/DEPRECATED.md`: legacy removal rationale and replacement path.

## Files Removed

- Active non-agent workflow:
  - `src/arctic_analytics/streamlit/widgets/data_analyst.py`
  - `src/arctic_analytics/core/data_analyst.py`
- Removed LLM/provider paths outside the single supported workflow:
  - `src/arctic_analytics/llm/meta_llama.py`
  - `src/arctic_analytics/llm/openai_chat_completions.py`
- Removed document/debug and Snowflake legacy modules:
  - `src/arctic_analytics/legacy/document_and_debug.py`
  - `src/arctic_analytics/legacy/mistral_helpers.py`
  - `src/arctic_analytics/legacy/snowflake_arctic_helpers.py`
  - `src/arctic_analytics/legacy/snowflake_connection.py`
- Removed top-level compatibility wrappers:
  - `utils/`
  - `widgets/`
- Removed obsolete media and personal artifact:
  - `media/`
  - `balaji.jpg`
- Removed generated artifacts:
  - `dist/`
  - `__pycache__/`
  - `.pytest_cache/`

## Files Deprecated

- `src/arctic_analytics/legacy/DEPRECATED.md` documents the retired legacy surface. The implementation files were deleted rather than retained because compatibility was not required for the new scope.

## Breaking Changes

- `utils.*` and top-level `widgets.*` imports no longer exist.
- Data Analyst/code-generation-only analysis is removed.
- Meta/Llama via Replicate is removed.
- OpenAI Chat Completions analysis dispatch is removed.
- Snowflake ingestion is removed from active code.
- Document/debug assistant functionality is removed.
- `construct_system_message` no longer accepts `agent_model`.
- `generate_ai_response` no longer accepts `agent_model` and always uses Tool-Calling Analysis.
- Trace exports no longer include mode metadata because Tool-Calling Analysis is the only supported path.

## Migration Notes

- Import from `arctic_analytics.*` package modules only.
- Use `arctic_analytics.llm.ai.generate_ai_response(vetted_files, model)` for supported analysis dispatch.
- Use `arctic_analytics.core.system_messages.construct_system_message(vetted_files)` for context construction.
- Replace any old Data Analyst workflow usage with Tool-Calling Analysis in `src/arctic_analytics/streamlit/widgets/analytics_agent.py`.
- Replace any Snowflake ingestion with CSV upload or sample datasets unless a future focused connector is designed.

## Remaining Technical Debt

- `app.py` remains as a compatibility entrypoint for `streamlit run app.py`.
- The supported OpenAI Responses implementation still mixes provider calls, tool specifications, execution glue, and UI-adjacent assumptions.
- Trace export is still a Streamlit session snapshot, not a replayable run record.
- Execution restrictions remain Python-level controls, not OS/container isolation.
- Dataset provenance and prompt/code/output hashes are not implemented.

## Validation

- `poetry lock` completed after dependency cleanup.
- `poetry run pytest` passed: 10 tests.

## Suggested Next Steps

- Split tool specifications and execution adapters out of `openai_responses.py`.
- Add context bundle export with stable hashes.
- Add dataset and metadata provenance fields to trace export.
- Add subprocess or container execution isolation before handling untrusted users or sensitive data.
