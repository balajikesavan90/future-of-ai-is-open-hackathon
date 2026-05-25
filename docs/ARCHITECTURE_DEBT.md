# Architecture Debt

Arctic Analytics is positioned as an experimental framework, but the current implementation is still primarily a Streamlit application with reusable pieces inside it. This document maps the coupling points that prevent the project from being a clean reusable framework today.

## Current Boundaries

| Area | Current modules | Coupling |
| --- | --- | --- |
| Context ingestion | `src/arctic_analytics/core/data_import.py`, `src/arctic_analytics/streamlit/widgets/uploader.py`, `src/arctic_analytics/streamlit/widgets/sample_datasets.py` | Ingestion writes directly to `st.session_state` and expects Streamlit-selected sources. |
| Metadata editing | `src/arctic_analytics/streamlit/widgets/data_dictionary.py` | Metadata editing is UI-native and stores edited data dictionaries in Streamlit state. |
| Context construction | `src/arctic_analytics/core/system_messages.py` | Prompt construction accepts `vetted_files`, but logs through `st.session_state["session_id"]` and returns a prompt string rather than a structured context bundle. |
| LLM dispatch | `src/arctic_analytics/llm/ai.py`, `src/arctic_analytics/llm/openai_responses.py` | Dispatch reads and mutates `st.session_state["messages"]`, `cost`, and `context_window_usage`. |
| Tool rendering | `src/arctic_analytics/llm/openai_responses.py`, `src/arctic_analytics/streamlit/helpers.py` | LLM response processing directly renders Streamlit expanders while processing tool calls. |
| Execution | `src/arctic_analytics/core/security.py`, `src/arctic_analytics/llm/openai_responses.py` | Low-level execution is mostly separable, but output normalization and token-size checks live in the OpenAI/Streamlit-adjacent class. |
| Trace generation | `src/arctic_analytics/streamlit/helpers.py` | Trace builder reads directly from Streamlit session state instead of accepting a run object. |

## What Prevents Reuse

- There is no framework-level run object representing dataset metadata, prompt, messages, tool calls, outputs, errors, and limitations.
- There is no schema-backed context bundle separate from the final system prompt.
- Tool-call execution and Streamlit rendering happen in the same loop.
- OpenAI response handling mutates the same message list that the UI renders.
- Trace generation is tied to `st.session_state`, which makes non-Streamlit usage awkward.
- Execution result normalization lives in `OpenAIResponsesUtility` rather than a provider-independent execution module.
- Model configuration, pricing, and context-window assumptions are hard-coded in the OpenAI utility.
- There is no stable public Python API for loading data, building context, running one analysis step, or exporting a trace.

## Refactor Direction

Do not refactor all of this at once. The lowest-risk path is:

1. Introduce a small provider-independent run/state dataclass or Pydantic model.
2. Move context bundle creation into `core/` without Streamlit logging dependencies.
3. Move execution result normalization out of `llm/openai_responses.py`.
4. Make trace building accept an explicit run/state object while keeping the Streamlit wrapper.
5. Separate tool-call processing from Streamlit rendering.
6. Add replay fixtures only after the run/state object is stable.

## What Not To Improve Yet

- Do not add a database or durable audit log before the trace schema and run object settle.
- Do not add role-based governance before human-review semantics are implemented.
- Do not add multiple LLM providers before the OpenAI path is less coupled to Streamlit.
- Do not add container execution before application-level execution behavior is better tested and documented.
- Do not overfit abstractions around examples; keep the first extraction small and testable.
