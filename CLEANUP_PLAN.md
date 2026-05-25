# Cleanup Plan

Arctic Analytics is being repositioned as an experimental open-source framework for metadata-aware, transparent, and constrained AI-assisted analysis over structured data.

The target shape is intentionally narrow:

- Tool-calling analysis is the only supported analysis path.
- Editable metadata and data dictionaries remain first-class.
- Reasoning, tool calls, generated code, constrained execution, trace export, and human review remain visible.
- Document/debug, hackathon, generic chat-with-data, Snowflake, code-generation-only, and broad assistant framing are removed or deprecated.
- Backward compatibility is preserved only where it does not keep obsolete concepts alive.

## Repository Inventory

| Component | Purpose | Keep | Deprecate | Remove | Reason |
| --- | --- | --- | --- | --- | --- |
| `README.md` | Primary project positioning and setup | Yes | No | No | Needs wording updates to emphasize tool-calling analysis only and remove legacy repository identity. |
| `docs/design_principles.md` | Research framing | Yes | No | No | Aligned with metadata-aware and transparent analysis; needs agent-only terminology. |
| `docs/research_questions.md` | Research questions | Yes | No | No | Mostly aligned; remove generic debugging wording. |
| `docs/architecture.md` | Architecture map | Yes | No | No | Missing; create to map actual modules to the analysis flow. |
| `media/` | Old UI screenshots | No | No | Yes | Screenshots reference obsolete Data Analyst, chart builder, and document/debug flows. |
| `legacy/` package | Archived Snowflake, Mistral, document/debug code | No | Yes | No | Keep only as explicitly deprecated archive because it is already isolated and may aid migration. |
| `widgets/` top-level | Compatibility wrappers | No | No | Yes | Duplicate package widgets and preserve obsolete import paths. |
| `utils/` top-level | Compatibility wrappers | No | No | Yes | Duplicate package modules and preserve obsolete helper names. |
| `src/arctic_analytics/streamlit/widgets/home.py` | Main Streamlit workflow routing | Yes | No | No | Must remove mode toggle and always route to tool-calling analysis. |
| `src/arctic_analytics/streamlit/widgets/analytics_agent.py` | Tool-calling analysis UI | Yes | No | No | Core analysis surface; rename user-facing terminology to "Tool-Calling Analysis". |
| `src/arctic_analytics/streamlit/widgets/data_analyst.py` | Non-agent code-generation-only UI | No | Yes | Yes from active package | Conflicts with agent-only scope; archive/deprecate rather than keep active. |
| `src/arctic_analytics/core/data_analyst.py` | Parser and repair helpers for non-agent generated code | No | Yes | Yes from active package | Supports removed code-generation-only path. |
| `src/arctic_analytics/core/system_messages.py` | Context and analysis system prompts | Yes | No | No | Remove document/debug prompts and non-agent prompt branch. |
| `src/arctic_analytics/llm/openai_responses.py` | Tool-calling OpenAI Responses implementation | Yes | No | No | Core supported analysis engine. |
| `src/arctic_analytics/llm/openai_chat_completions.py` | Chat completions tool/code path | No | Yes | Yes from dispatch | Duplicates tool execution and supports non-agent path. Archive only if needed later. |
| `src/arctic_analytics/llm/meta_llama.py` | Replicate/Llama path | No | Yes | Yes from dispatch | Not tool-calling analysis; adds inactive dependency surface. |
| `src/arctic_analytics/core/security.py` | AST validation and constrained Python execution | Yes | No | No | Core constrained execution; document limits clearly. |
| Trace export in `streamlit/helpers.py` | JSON session snapshot | Yes | No | No | Core inspectability feature; update labels and remove mode flags where possible. |
| Citation metadata | Citation and archive metadata | Yes | No | No | Needs new abstract/keywords and non-hackathon repository language. |
| CI | Automated validation | Yes | No | No | Missing GitHub Actions workflow; add `poetry install` and `pytest`. |
| Dependencies | Runtime and dev requirements | Yes | No | Partially | Remove Snowflake and Replicate dependencies; keep analysis, plotting, Streamlit, OpenAI dependencies. |
| Packaging | Poetry package config and script | Yes | No | No | Keep package-native entrypoint; update repository metadata if needed. |
| Tests | Regression coverage | Yes | No | Partially | Remove tests for compatibility shims, non-agent dispatch, and deprecated paths; keep aligned tests. |
| Examples | Inspectability demonstration | Yes | No | No | Missing; create sample dataset, metadata, trace export, and walkthrough. |
| Snowflake code | Direct Snowflake ingestion | No | Yes | Yes from active import path | Outside reduced scope and currently inactive/commented in UI. |
| Deprecated wrappers | Old `utils.*` and `widgets.*` imports | No | No | Yes | Backward compatibility is not worth preserving for duplicate wrappers. |
| Generated artifacts | Build/cache output | No | No | Yes | `dist/`, `__pycache__/`, `.pytest_cache/` should not live in the repo. |

## Findings

### Dead Code

- `src/arctic_analytics/streamlit/widgets/data_analyst.py` and `src/arctic_analytics/core/data_analyst.py` only support the removed code-generation-only workflow.
- `src/arctic_analytics/legacy/document_and_debug.py`, `src/arctic_analytics/legacy/mistral_helpers.py`, and `src/arctic_analytics/legacy/snowflake_*` are archived/commented legacy code.
- Top-level `widgets/` and `utils/` are compatibility wrappers duplicating package modules.
- Snowflake UI import in `home.py` is commented out.

### Duplicate Code

- `widgets/*` duplicates `src/arctic_analytics/streamlit/widgets/*`.
- `utils/*` duplicates `src/arctic_analytics/core`, `src/arctic_analytics/llm`, and Streamlit helpers.
- `openai_chat_completions.py` duplicates tool execution concepts also present in `openai_responses.py`.

### Compatibility Shims

- Root `widgets/` and `utils/` wrappers preserve old import paths and should be removed.
- `app.py` is a trivial compatibility entrypoint. It can remain temporarily because it does not preserve an obsolete analysis mode.

### Obsolete Screenshots

- `media/4 data_analyst.PNG`, `media/5 chart_builder.PNG`, and `media/6 document_and_debug.PNG` are obsolete.
- The remaining media files are old UI screenshots and should be removed until refreshed screenshots exist.

### Stale Docs And Terminology

- `About` page still references the hackathon and dual Agent Mode behavior.
- Prompt guide uses "Analytics Agent" and "Data Analyst".
- Helper labels use "Analytics Agent" and "Data Analyst".
- README setup still references the old repository slug.

### Inactive Dependencies

- `snowflake-connector-python` is only used by removed Snowflake ingestion.
- `replicate` is only used by removed Meta/Llama path.
- `pyarrow`, `pillow`, and `statsmodels` should be rechecked after cleanup; some may be transitive or only used by constrained execution/plotting.

### Unsupported Claims

- Citation/Zenodo metadata claims general charting plus document/debug assistance.
- Some UI copy implies broad assistant capability. It should be narrowed to metadata-aware tool-calling analysis over loaded structured data.

## Implementation Plan

1. Remove the active non-agent workflow from UI routing, LLM dispatch, and system prompt construction.
2. Move or mark Data Analyst and document/debug lineage as deprecated under `legacy/`.
3. Standardize user-facing terminology on **Tool-Calling Analysis**.
4. Remove top-level compatibility wrappers and generated artifacts.
5. Update README, contribution/citation/archive metadata, security documentation, and architecture documentation.
6. Add examples demonstrating metadata, tool calls, constrained output, and trace export.
7. Add CI workflow for `poetry install` and `pytest`.
8. Run `pytest`, fix aligned failures, and write `REPOSITIONING_REPORT.md`.
