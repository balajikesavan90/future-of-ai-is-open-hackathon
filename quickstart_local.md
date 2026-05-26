# Quickstart: Local Streamlit Workflow

This walkthrough is for researchers who want to run Arctic Analytics locally, use the Streamlit UI, inspect agent-generated analysis, and export evidence artifacts.

## 1. Clone The Repository

```bash
git clone https://github.com/balajikesavan90/arctic-analytics.git
cd arctic-analytics
```

## 2. Install Dependencies

Arctic Analytics currently targets Python 3.12.

```bash
poetry install
```

If Poetry is not installed:

```bash
python -m pip install poetry
poetry install
```

## 3. Configure API Access

The local app supports `OPENAI_API_KEY` from your shell environment:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export ENV="dev"
```

You can also use Streamlit secrets:

```bash
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml` and replace the placeholder key:

```toml
ENV = "dev"
OPENAI_API_KEY = "your-openai-api-key"
```

Do not commit `.streamlit/secrets.toml`.

## 4. Launch The Local App

```bash
poetry run arctic-analytics-app
```

Equivalent command:

```bash
poetry run arctic-analytics app
```

Open the Streamlit URL printed in your terminal, usually `http://localhost:8501`.

## 5. Load A Sample Dataset

In the **Analyze Data** tab, select a bundled sample dataset such as **Tips Dataset**.

The sample path is useful for a first run because it avoids file-format friction while still exercising the same metadata, agent analysis, code inspection, trace export, and bundle export flow.

## 6. Review And Edit Metadata

Review the generated data dictionary before analysis:

- dataset description
- column names
- data types
- primary-key flags
- column descriptions

Edit any metadata that looks incomplete or wrong, then choose **Save Data Dictionary and Proceed**.

## 7. Run An Exploratory Analysis

Use an exploratory prompt to start:

```text
Find me something interesting in this data and plot it.
```

Focused prompts are also useful:

```text
Which day has the highest average tip percentage? Calculate tip percentage as tip divided by total_bill.
```

The broad prompt is intentionally supported. Treat it as exploration, then review the generated code and outputs before relying on the result.

## 8. Inspect Generated Code And Tool Calls

After the agent responds, inspect:

- visible tool calls
- tool-call reasons
- generated Python code
- tool responses
- plots or tables
- final answer text
- the sidebar section **What does the AI see?**

The generated analysis is meant to be reviewed by a human researcher, not trusted as an opaque final result.

## 9. Export An Analysis Trace

In the sidebar, open **Analysis Trace**:

1. Select **Prepare Trace Export**.
2. Select **Export Analysis Trace**.

The trace is a JSON snapshot of the current Streamlit session. It is useful for inspection, but it is not a deterministic replay record.

## 10. Export A Research Bundle

In the same **Analysis Trace** sidebar section:

1. Select **Prepare Research Bundle**.
2. Select **Export Research Bundle**.

The downloaded zip contains review artifacts such as:

- `run_manifest.json`
- `analysis_trace.json`
- `context_bundle.json`
- `prompts.json`
- `generated_code/`
- `outputs/`
- `figures/`
- `environment.json`
- `methods.md`
- `limitations.md`
- `software_citation.md`
- `citation.cff`

Use this bundle as evidence for downstream papers, datasets, appendices, or methods work after reviewing the code, outputs, and limitations.

## No-API Walkthrough

You can inspect the evidence format without configuring OpenAI or running the app.

Open:

```text
examples/sample_research_bundle/
```

Key files:

- `README.md`: explains the bundle contents.
- `run_manifest.json`: lightweight run metadata, including run id, timestamp, software version, Python/platform details, model/provider when known, source filenames when known, and limitations.
- `context_bundle.json`: dataset metadata and analysis context available to the workflow.
- `analysis_trace.json`: session trace with messages, tool calls, outputs, model, cost, and known limitations.
- `prompts.json`: system and user prompt material available for review.
- `generated_code/`: Python snippets generated for tool execution.
- `outputs/`: tool outputs and final answer material.
- `figures/`: decoded figures when exported image payloads are available.
- `environment.json`: local software/runtime metadata.
- `methods.md`: draft methods language for human editing.
- `limitations.md`: limitations to disclose when using the bundle.
- `software_citation.md` and `citation.cff`: citation metadata and suggested wording.

This checked-in bundle is illustrative. It helps reviewers understand what Arctic Analytics exports before they spend time on local setup.

Maintainers can regenerate the checked-in trace and sample bundle from the same live API run:

```bash
poetry run python scripts/regenerate_example_trace.py
```

## Docker

A Dockerfile is included for local experimentation, but Docker is not the primary documented research path and is not a substitute for reviewing exported artifacts.

Build:

```bash
docker build -t arctic-analytics .
```

Run with an environment API key:

```bash
docker run --rm -p 8501:8501 -e OPENAI_API_KEY="$OPENAI_API_KEY" -e ENV=dev arctic-analytics
```

Then open:

```text
http://localhost:8501
```

If Docker behavior differs from the Poetry workflow, treat Docker as experimental and use the Poetry-based local setup above.
