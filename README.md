# Arctic Analytics

Arctic Analytics is experimental open-source research software for AI-assisted structured-data research workflows. It is intended to help researchers inspect agent-generated analyses, preserve research artifacts, and support downstream publications, datasets, and methods rather than function as a standalone analytics product.

Arctic Analytics currently supports metadata-aware agent analysis over tabular data. Researchers can upload or select CSV data, review and edit data dictionaries, inject metadata before inference, inspect generated code and tool calls, execute Python with application-level restrictions, export traces, and package research bundles for review.

> Packaging note: the app is available as the `arctic-analytics` distribution with the `arctic_analytics` import package.

## What It Does Today

- Supports metadata-aware structured-data analysis.
- Supports exploratory agent workflows with visible evidence, code, and outputs.
- Exposes generated code, tool calls, tool responses, prompts, outputs, and trace snapshots.
- Uses constrained execution with application-level Python restrictions.
- Builds dataset metadata, including columns, data types, summary statistics, missing values, and row samples.
- Lets researchers edit dataset descriptions, column descriptions, data types, and primary key flags before analysis.
- Injects metadata into model context before agent inference.
- Exports lightweight JSON analysis traces.
- Exports local research artifact bundles containing traces, context, prompts, generated code, outputs, environment metadata, methods drafts, limitations, and citation files.

## Intended Usage Model

Streamlit Cloud:

- demos
- onboarding
- exploration

Local execution:

- primary workflow
- publication support
- reproducible artifacts
- researcher customization

The Streamlit app remains useful for demonstrations and interactive exploration. Local execution is the intended path for research work that may support publications, supplementary material, datasets, or methods sections.

## Example Research Workflow

```text
Upload dataset(s)
    |
    v
Set up metadata
    |
    v
Researcher asks a question
    |
    v
Agent performs visible analysis and generates a response
    |
    v
Researcher asks more questions
    |
    v
Agent performs more visible analysis and generates more responses
    |
    v
Repeat as needed
    |
    v
Trace
    |
    v
Artifacts
    |
    v
Publication
```

## Research Artifact Bundles

After an analysis session, researchers can export a research artifact bundle from the Streamlit sidebar. The bundle packages the dataset metadata, prompts, trace, generated code, outputs, environment details, limitations, and citation files so the evidence behind an analysis can be reviewed and used in papers, appendices, or supplementary material.

Review the checked-in example format at [examples/sample_research_bundle](examples/sample_research_bundle).

## Design Principles

### Context Before Inference

Structured-data research depends on context. Arctic Analytics prioritizes editable metadata, dataset descriptions, data dictionaries, dataframe shape, summary statistics, missing values, and row samples as first-class context inputs.

### Inspectability Over Magic

Generated analysis should be inspectable. The UI and exported artifacts expose the system prompt, message context, generated Python, tool calls, tool-call reasons, tool responses, outputs, and limitations so researchers can review how an answer was produced.

### Constraints Over Unrestricted Execution

Generated code should not run with unrestricted access by default. Arctic Analytics applies Python-level validation, import/function restrictions, output-type checks, and runtime limits before returning results.

Important limitation: these are Python-level restrictions and runtime constraints. They are not isolated container or OS-level sandboxing.

### Human Accountability

Arctic Analytics is designed for human review. Outputs should be checked against the source data, metadata, generated code, visible intermediate steps, and exported artifacts before they are trusted or cited.

## Current Limitations

This project does not provide:

- Deterministic reproducibility.
- Governance guarantees.
- Security isolation.
- Audit-grade provenance.
- Replacement for human review.

Current implementation limits:

- Traces are snapshots of Streamlit session state.
- Research bundles package artifacts for review; they are not replayable runs.
- Execution restrictions are not isolation.
- Examples may require external APIs when regenerating traces.
- Reproducibility is partial.
- Reusable framework boundaries are partial; the current implementation is still Streamlit-centered.
- There is no durable audit log, role-based governance, dataset provenance model, or policy engine.

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

### Running The Streamlit Demo

Create `.streamlit/secrets.toml` with:

```toml
ENV = "dev"
OPENAI_API_KEY = "<Create an OpenAI account and add your API key here.>"
```

Then run:

```bash
# Compatibility entrypoint
streamlit run app.py

# Package-native Streamlit entrypoint
streamlit run src/arctic_analytics/streamlit_app.py

# Installed console script
arctic-analytics-app

# Console entrypoint
arctic-analytics app
```

## Citing Arctic Analytics

If Arctic Analytics supports work that appears in a paper, dataset, appendix, or methods section, cite the software using [CITATION.cff](CITATION.cff).

DOI: `10.5281/zenodo.18514535`

Suggested wording:

```text
Analyses were performed using Arctic Analytics v0.1.0 (DOI: 10.5281/zenodo.18514535).
```

Before citing a newer release, verify that the README, `CITATION.cff`, `.zenodo.json`, package version, and Zenodo record refer to the same version. See [docs/citing.md](docs/citing.md).

## Documentation

- [Quickstart: local artifact bundles](quickstart_local.md)
- [Publication workflow](docs/publication_workflow.md)
- [Citation guidance](docs/citing.md)
- [Design principles](docs/design_principles.md)
- [Research questions](docs/research_questions.md)
- [Architecture](docs/architecture.md)
- [Security](SECURITY.md)
- [Threat model](docs/threat_model.md)
- [Reproducibility](docs/reproducibility.md)
- [Examples](examples/README.md)

## Contributing

Contributions are welcome, especially around trace visibility, context modeling, execution constraints, artifact bundles, reproducibility, and documentation of limitations. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
