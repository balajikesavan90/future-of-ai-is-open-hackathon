# Quickstart: 15-Minute Local Evidence Bundle

This walkthrough is for researchers who want to run Arctic Analytics locally, use the Streamlit **Analyze Data** workflow, inspect agent-generated code and tool calls, and export an evidence bundle for downstream review.

Streamlit Community Cloud is useful for demo and onboarding. Local Streamlit execution is the intended research workflow.

## What You Will Produce

By the end of this walkthrough, you should have:

- a local Streamlit Arctic Analytics session
- a sample dataset loaded through **Analyze Data**
- reviewed or edited metadata before inference
- one agent-assisted analysis response
- inspected generated code, tool calls, and tool outputs
- exported an analysis trace JSON
- exported a research bundle zip

## 1. Clone The Repository

```bash
git clone https://github.com/balajikesavan90/arctic-analytics.git
cd arctic-analytics
```

## 2. Install Dependencies

Arctic Analytics currently targets Python 3.12. The fastest local research path uses `uv` and editable pip install.

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
```

Poetry remains the developer/contributor path:

```bash
poetry install
poetry run pytest
```

## 3. Configure OpenAI API Access

Agent analysis requires an OpenAI API key. Choose one of the setup paths below. You do not need more than one.

For local terminal runs, `.env` is preferred. The app checks the current Streamlit session, `.env`, environment variables, and Streamlit secrets.

Option A, local `.env` path:

```bash
cp .env.example .env
```

Then edit `.env`:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
```

Option B, environment variable path:

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

Option C, Streamlit secrets path:

```bash
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "your-openai-api-key"
```

Do not commit `.streamlit/secrets.toml`.

If no key is configured before launch, the Streamlit app asks for the key and can save it locally to `.env`.

## 4. Launch The Local Streamlit App

```bash
streamlit run app.py
```

Developer/contributor equivalent:

```bash
poetry run arctic-analytics-app
poetry run arctic-analytics app
```

Open the Streamlit URL printed in your terminal, usually:

```text
http://localhost:8501
```

## 5. Load A Sample Dataset

In the **Analyze Data** tab, select **Tips Dataset**.

The sample dataset avoids file-format friction while exercising the same local research workflow: metadata review, agent analysis, generated code inspection, trace export, and research bundle export.

## 6. Review And Edit The Data Dictionary

Before analysis, review the generated metadata:

- dataset description
- column names
- data types
- primary-key flags
- column descriptions

Edit anything that looks incomplete or wrong. Then select **Save Data Dictionary and Proceed**.

This metadata is part of what the agent sees before generating analysis code.

## 7. Run An Exploratory Prompt

Use the built-in broad exploratory prompt or type:

```text
Find me something interesting in this data and plot it.
```

This prompt is intentionally supported for exploration. Treat the response as a starting point, then inspect the generated code and outputs before relying on it.

A focused follow-up prompt can be useful after the exploratory pass:

```text
Which day has the highest average tip percentage? Calculate tip percentage as tip divided by total_bill.
```

## 8. Inspect Generated Code And Tool Calls

After the agent responds, inspect the visible evidence in the UI:

- tool calls
- tool-call reasons
- generated Python code
- tool responses
- plots or tables
- final answer text
- sidebar section **What does the AI see?**

The generated analysis is not meant to be trusted as an opaque final answer. Review the code, outputs, metadata, and limitations before using a result in downstream work.

## 9. Export An Analysis Trace

In the sidebar, open **Analysis Trace**:

1. Select **Prepare Trace Export**.
2. Select **Export Analysis Trace**.

The trace is a JSON snapshot of the current Streamlit session. It is useful for review, but it is not a deterministic replay record.

## 10. Export A Research Bundle

In the same **Analysis Trace** sidebar section:

1. Select **Prepare Research Bundle**.
2. Select **Export Research Bundle**.

The downloaded zip contains review artifacts such as:

- `README.md`
- `run_manifest.json`
- `context_bundle.json`
- `analysis_trace.json`
- `prompts.json`
- `generated_code/`
- `outputs/`
- `figures/`
- `environment.json`
- `methods.md`
- `limitations.md`
- `software_citation.md`
- `citation.cff`

Use this bundle as evidence for downstream papers, datasets, appendices, or methods work after reviewing the generated code, outputs, and limitations.

## 11. Inspect The Expected Bundle Files

After unzipping the exported bundle, check the core files:

- `README.md`: explains the bundle contents.
- `run_manifest.json`: lightweight run metadata, source filenames when available, selected SHA-256 hashes when source content is available, model/provider when known, and known limitations.
- `context_bundle.json`: dataset metadata, prompt context, researcher notes, assumptions, and source references available to the workflow.
- `analysis_trace.json`: session trace with messages, tool calls, outputs, model, cost, context usage, dataset metadata, errors, and limitations.
- `prompts.json`: system and user prompt material available for review.
- `generated_code/`: generated Python snippets extracted from tool calls.
- `outputs/`: tool outputs and final answer material.
- `figures/`: decoded figures when exported image payloads are available.
- `environment.json`: local software/runtime metadata and selected dependency versions.
- `methods.md`: draft methods language for human editing.
- `limitations.md`: limitations to disclose when using the bundle.
- `software_citation.md`: suggested software citation wording.
- `citation.cff`: citation metadata copied from the repository.

## No-API Walkthrough

You can inspect the evidence format without configuring OpenAI or running the app.

Open:

```text
examples/sample_research_bundle/
```

This checked-in bundle demonstrates the evidence format, not live agent execution. It was generated from a sample analysis and is useful for understanding what Arctic Analytics exports before you spend time on local setup.

The sample bundle does not run a new analysis. It lets you inspect a completed analysis artifact.

Key files:

- `README.md`: overview of the bundle contents.
- `run_manifest.json`: run id, timestamp, Arctic Analytics version, Python/platform details, model/provider, source filenames, selected SHA-256 hashes, trace presence, and limitations.
- `context_bundle.json`: dataset metadata and analysis context available to the workflow.
- `analysis_trace.json`: exported session trace, including messages, visible tool calls, outputs, model, cost, and known limitations.
- `prompts.json`: system prompt and user prompt material available for review.
- `generated_code/`: Python snippets generated for tool execution.
- `outputs/`: tool outputs and final answer material.
- `figures/`: decoded figures when exported image payloads are available.
- `environment.json`: local software/runtime metadata and selected dependency versions.
- `methods.md`: draft methods language for human editing.
- `limitations.md`: limitations to disclose when using the bundle.
- `software_citation.md`: suggested citation wording for Arctic Analytics.

For the corresponding input files, inspect:

```text
examples/sample_dataset.csv
examples/sample_metadata.json
examples/sample_trace_export.json
```

Maintainers can regenerate the checked-in trace and sample bundle from a live API run:

```bash
poetry run python scripts/regenerate_example_trace.py
```

## Troubleshooting

Python 3.12:

- Confirm `python --version` reports Python 3.12.
- If your default Python is different, create a Python 3.12 environment first, then run `poetry install`.

Poetry install:

- If `poetry` is missing, run `python -m pip install poetry`.
- If dependency resolution fails, confirm you are inside the repository root and using Python 3.12.

API key setup:

- Agent analysis requires `OPENAI_API_KEY`.
- The app checks the current Streamlit session, `.env`, environment variables, then Streamlit secrets.
- If chat input is disabled, confirm the key is set in the same shell used to launch Streamlit.
- If no key is found at launch, enter it in the setup screen and optionally save it to `.env`.

`.env` local credentials:

- Copy `.env.example` to `.env`.
- Replace the placeholder key.
- Do not commit `.env`.

Streamlit secrets:

- Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml`.
- Replace the placeholder key.
- Do not commit `.streamlit/secrets.toml`.

Environment variable fallback:

```bash
export OPENAI_API_KEY="your-openai-api-key"
poetry run arctic-analytics-app
```

Docker:

- A Dockerfile is included for local experimentation.
- Docker is not the primary documented research path.
- If Docker behavior differs from the Poetry workflow, use the Poetry-based local setup above.

Build:

```bash
docker build -t arctic-analytics .
```

Run:

```bash
docker run --rm -p 8501:8501 -e OPENAI_API_KEY="$OPENAI_API_KEY" -e ENV=dev arctic-analytics
```
