# Quickstart: Local Streamlit Workflow

This quickstart is for researchers who want to run Arctic Analytics locally and export research artifacts from the UI.

## Install

```bash
git clone https://github.com/balajikesavan90/arctic-analytics.git
cd arctic-analytics
poetry install
```

## Configure API Access

Create `.streamlit/secrets.toml`:

```toml
ENV = "dev"
OPENAI_API_KEY = "<your OpenAI API key>"
```

## Start The Local App

```bash
poetry run arctic-analytics-app
```

You can also run:

```bash
poetry run arctic-analytics app
```

## Run An Analysis

1. Upload dataset(s), or start with a bundled sample dataset.
2. Review and edit the dataset description, data dictionary, data types, and primary key flags.
3. Ask an analysis question.
4. Inspect the agent's visible tool calls, generated code, outputs, and response.
5. Ask follow-up questions as needed.
6. Use the sidebar to export the analysis trace or research artifact bundle.

## Inspect The Checked-In Bundle Example

Open:

```text
examples/sample_research_bundle/
```

This small bundle shows the artifact format without requiring an API key.
