# Arctic Analytics

Arctic Analytics is an open-source framework exploring metadata-aware, transparent, and constrained AI-assisted analysis over structured data.

The project investigates a narrow question: how should structured-data analysis change when context is explicit, execution is visible, and generated code runs under practical constraints? Arctic Analytics lets users upload or select tabular data, review and edit data dictionaries, inject metadata before inference, inspect generated code or tool calls, execute Python with application-level restrictions, and review outputs before relying on them.

This is not an enterprise governance platform, a general AI copilot, or a novel agent architecture. It is an experimental precursor for studying metadata-aware and inspectable analysis workflows.

> Packaging note: the app is available as the `arctic-analytics` distribution with the `arctic_analytics` import package.

## What It Does Today

- Loads CSV files or bundled sample datasets.
- Builds dataset metadata, including columns, data types, summary statistics, missing values, and small row samples.
- Lets users edit dataset descriptions, column descriptions, data types, and primary key flags before analysis.
- Injects that metadata into model context before inference.
- Uses Tool-Calling Analysis as the only supported analysis workflow.
- Executes generated Python with AST validation, restricted globals, output constraints, and a timeout.
- Shows prompts, reasoning summaries, generated code, tool calls, tool responses, outputs, and a lightweight JSON trace export in the Streamlit UI.

## Design Principles

### Context Before Inference

The model should receive explicit context before attempting analysis. Arctic Analytics prioritizes editable metadata, dataset descriptions, data dictionaries, dataframe shape, summary statistics, missing values, and sample rows as first-class context inputs.

### Transparency Over Magic

Generated analysis should be inspectable. The UI exposes the system prompt, message context, generated Python, tool calls, tool-call reasons, and tool responses so users can see how an answer was produced.

### Constraints Over Unrestricted Execution

Generated code should not run with unrestricted access by default. Arctic Analytics applies Python-level validation, import/function restrictions, output-type checks, and runtime limits before returning results.

Important limitation: these are Python-level restrictions and runtime constraints. They are not isolated container or OS-level sandboxing.

### Human Accountability

Arctic Analytics is designed for human review. Outputs should be checked against the data, generated code, and visible intermediate steps before they are trusted.

## Research Questions

- Does explicit metadata improve structured-data analysis quality?
- Which metadata matters most: dataset descriptions, data dictionaries, data types, summary statistics, missing values, row samples, or user-written business context?
- Does visible generated code or visible tool calling improve user trust?
- Which execution constraints meaningfully reduce risk without blocking useful analysis?
- What should be included in an AI analysis context bundle?
- How should intermediate analysis steps be represented for review?
- What minimum trace is useful before investing in durable audit infrastructure?

## Current Limitations

- Python-level restrictions are not OS-level or container sandboxing.
- There are no durable audit logs.
- Trace export is a Streamlit session snapshot, not a replayable execution record.
- There are no replayable runs.
- There is no role-based governance.
- There is no dataset provenance model.
- There is no policy engine.
- There is no claim of novel agent architecture.

## Roadmap

Near-term:

- Improve trace export coverage.
- Add clearer context bundle exports.
- Add hashes for prompts, generated code, dataset metadata, and execution results.
- Strengthen tests around execution constraints and trace generation.

Medium-term:

- Separate reusable analysis/context logic from Streamlit state.
- Add structured context bundles.
- Add replay-oriented run manifests.
- Track dataset and data-dictionary provenance.

Long-term:

- Move execution into isolated subprocesses or containers.
- Add replayable runs.
- Add durable trace storage.
- Add stronger provenance and versioning for datasets, prompts, generated code, and outputs.

## Getting Started

### Prerequisites

- Python 3.12
- pip
- Poetry

### Installation

```bash
git clone https://github.com/balajikesavan90/arctic-analytics.git
cd arctic-analytics
poetry install
```

### Installing As A Package

```bash
pip install arctic-analytics

# Or, during local development
poetry install
```

### Setting Up Secrets

Create `.streamlit/secrets.toml` with:

```toml
ENV = "dev"
OPENAI_API_KEY = "<Create an OpenAI account and add your API key here.>"
```

### Running The App

```bash
# Compatibility entrypoint
streamlit run app.py

# Package-native Streamlit entrypoint
streamlit run src/arctic_analytics/streamlit_app.py

# Installed console script
arctic-analytics-app
```

## Documentation

- [Design principles](docs/design_principles.md)
- [Research questions](docs/research_questions.md)
- [Architecture](docs/architecture.md)
- [Security](SECURITY.md)
- [Examples](examples/README.md)

## Contributing

Contributions are welcome, especially around trace visibility, context modeling, execution constraints, and documentation of limitations. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
