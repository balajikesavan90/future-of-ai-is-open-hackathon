# Architecture

Python Data Analysis Agent centers on one workflow: Tool-Calling Analysis over loaded structured data.

```text
User
  |
  v
Context ingestion
  |
  v
Metadata editing
  |
  v
Context construction
  |
  v
LLM reasoning
  |
  v
Tool calls
  |
  v
Constrained execution
  |
  v
Trace generation
  |
  v
Artifact bundle generation
  |
  v
Output
```

## Module Map

| Stage | Modules | Notes |
| --- | --- | --- |
| User | `src/python_data_analysis_agent/streamlit_app.py`, `src/python_data_analysis_agent/streamlit/widgets/home.py` | Streamlit entrypoint and workflow routing. |
| Context ingestion | `src/python_data_analysis_agent/streamlit/widgets/uploader.py`, `src/python_data_analysis_agent/streamlit/widgets/sample_datasets.py`, `src/python_data_analysis_agent/core/data_import.py` | Loads CSV uploads or bundled sample datasets. |
| Metadata editing | `src/python_data_analysis_agent/streamlit/widgets/data_dictionary.py`, `src/python_data_analysis_agent/streamlit/widgets/uploaded_data.py` | Lets users edit dataset descriptions, column descriptions, data types, and primary-key flags. |
| Context construction | `src/python_data_analysis_agent/core/system_messages.py` | Builds the system prompt from metadata, summary statistics, missing values, and row samples. |
| LLM reasoning | `src/python_data_analysis_agent/llm/ai.py`, `src/python_data_analysis_agent/llm/openai_responses.py` | Dispatches to the supported tool-calling analysis implementation. |
| Tool calls | `src/python_data_analysis_agent/llm/openai_responses.py` | Defines tool specs and processes model-requested Python expression, function, and plot calls. |
| Constrained execution | `src/python_data_analysis_agent/core/security.py`, `src/python_data_analysis_agent/llm/openai_responses.py` | Validates generated code, restricts imports/globals, executes with timeout, and checks outputs. |
| Trace generation | `src/python_data_analysis_agent/streamlit/helpers.py` | Builds JSON-safe session traces with prompts, messages, tool calls, outputs, metadata, and known limitations. |
| Artifact bundle generation | `src/python_data_analysis_agent/artifacts/` | Packages Streamlit session traces, context, prompts, generated code, outputs, environment metadata, methods drafts, limitations, and citation files. |
| Output | `src/python_data_analysis_agent/streamlit/widgets/analytics_agent.py` | Displays messages, reasoning summaries, tool calls, tool responses, tables, plots, and trace export controls. |

## Local-First Artifact Boundary

The artifact bundle layer is intentionally pure Python. Streamlit adapts session state into a `ResearchSession`, then uses the artifact layer to create a downloadable bundle. Bundle creation is exposed through the local Streamlit UI after an analysis session.

## Deprecated Areas

The previous code-generation-only Data Analyst flow, document/debug tools, Snowflake connector UI, Replicate/Llama path, and top-level `utils`/`widgets` compatibility wrappers are removed from active use. See [legacy archive notes](archive/legacy_deprecated.md).

For current Streamlit/framework coupling points, see [Architecture Debt](ARCHITECTURE_DEBT.md).
