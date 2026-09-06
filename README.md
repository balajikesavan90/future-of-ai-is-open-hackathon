# Arctic Analytics

Arctic Analytics is experimental open-source research software for AI-assisted structured-data research workflows. It is intended to help researchers inspect agent-generated analyses, preserve research artifacts, and support downstream publications, datasets, and methods rather than function as a standalone analytics product.

Arctic Analytics currently supports metadata-aware agent analysis over tabular data. Researchers can upload or select CSV data, review and edit data dictionaries, inject metadata before inference, inspect generated code and tool calls, execute Python with application-level restrictions, export traces, and package research bundles for review.

> Packaging note: the app is available as the `arctic-analytics` distribution with the `arctic_analytics` import package.

## Start Here: Local Research Run

Fastest local path for researchers who want to run the Streamlit workbench:

```bash
git clone https://github.com/balajikesavan90/arctic-analytics.git
cd arctic-analytics
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
cp .env.example .env
# edit .env and set OPENAI_API_KEY
streamlit run app.py
```

Live AI-assisted analysis requires an OpenAI API key. If no key is configured, the app asks for one on first launch and can save it to local `.env`.

Poetry remains the developer/contributor path. `uv`/pip is the recommended fastest path for researchers who just want to run locally.

> No API key needed: inspect the checked-in completed artifact at [examples/sample_research_bundle](examples/sample_research_bundle). The sample bundle does not run a new analysis. It lets you inspect a completed analysis artifact.

## Known Good Local Environment

- Python 3.12
- `uv`
- Streamlit
- OpenAI API key for live model calls
- Linux/macOS shell commands are expected in the docs
- Windows users may need PowerShell-equivalent activation commands

## Developer Install

Use Poetry when contributing, running tests, or working on package internals:

```bash
poetry install
poetry run streamlit run app.py
poetry run pytest
```

## First Path Through The Project

Use the path that matches what you need:

| Path | Use it for | Start here |
| --- | --- | --- |
| Try demo | Quick onboarding with Streamlit Community Cloud, sample data, and broad exploratory prompts such as "find something interesting." This shows what the tool can do; it is not the primary research workflow. | Streamlit Cloud deployment, when available |
| Run locally | Real research workflow with local Streamlit, your own data or sample data, editable metadata, visible generated code/tool calls, trace export, and research bundle export. | [Quickstart: local evidence bundle](quickstart_local.md) |
| Inspect sample bundle | No-API review of the checked-in evidence format before installing anything or configuring OpenAI. | [examples/sample_research_bundle](examples/sample_research_bundle) |
| Export evidence | Package the trace, context, prompts, generated code, outputs, environment metadata, methods draft, limitations, and citation files after a local analysis session. | Streamlit sidebar, **Analysis Trace** |

Streamlit Community Cloud is for demo and onboarding. Local Streamlit execution is the intended path for research work that may support downstream papers, datasets, appendices, or methods.

## No API Key? Inspect A Completed Sample Bundle

Open [examples/sample_research_bundle](examples/sample_research_bundle) to inspect the evidence format before configuring credentials. Useful files include:

- `context_bundle.json`
- `analysis_trace.json`
- `generated_code/`
- `outputs/`
- `methods.md`
- `limitations.md`
- `run_manifest.json`

The sample bundle does not run a new analysis. It lets you inspect a completed analysis artifact.

## What It Does Today

- Supports metadata-aware structured-data analysis.
- Supports exploratory agent workflows with visible evidence, code, and outputs.
- Exposes generated code, tool calls, tool responses, prompts, outputs, and trace snapshots.
- Uses constrained execution with application-level Python restrictions.
- Builds dataset metadata, including columns, data types, summary statistics, missing values, and row samples.
- Lets researchers edit dataset descriptions, column descriptions, data types, and primary key flags before analysis.
- Injects metadata into model context before agent inference.
- Exports lightweight JSON analysis traces and can resume an analysis when CSVs with the original filenames and ordered columns are uploaded again. Matching intentionally does not use a content hash, so refreshed rows are supported; a visible stale-results warning prompts researchers to re-run important findings.
- Exports local research artifact bundles containing traces, context, prompts, generated code, outputs, environment metadata, methods drafts, limitations, and citation files.

## Intended Usage Model

Arctic Analytics supports two paths:

Demo path:

- Streamlit Community Cloud
- sample data
- broad exploratory prompts such as "find something interesting"
- quick onboarding and demonstration

Research path:

- local Streamlit execution
- researcher-owned data
- editable metadata and data dictionaries
- visible generated code, tool calls, and outputs
- trace and research bundle export
- publication support

The Streamlit app remains useful for demonstrations and interactive exploration. Local Streamlit execution is the intended path for research work that may support publications, supplementary material, datasets, or methods sections.

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

- Traces are snapshots of Streamlit session state. They can restore conversation and metadata for continuation with re-uploaded CSVs, but are not deterministic execution replays. Only trace-schema version 0.3.0 exports with a resume manifest are resumable; those traces retain chart payloads. Trace exports larger than 10 MiB are not prepared because they cannot be imported for resume.
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
- `uv` for the fastest local research install, or Poetry for contributor workflows

### Installation

```bash
git clone https://github.com/balajikesavan90/arctic-analytics.git
cd arctic-analytics
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
```

### Installing As A Package

```bash
pip install arctic-analytics

# Or, during local development
poetry install
```

### Running Locally

For local terminal runs, `.env` is preferred:

```bash
cp .env.example .env
```

Then edit `.env`:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
```

Environment variables are also supported:

```bash
export OPENAI_API_KEY="<your OpenAI API key>"
```

Streamlit secrets are also supported:

```bash
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml` with:

```toml
OPENAI_API_KEY = "<Create an OpenAI account and add your API key here.>"
```

Do not commit real credentials.

Then run:

```bash
# Fast local path
streamlit run app.py

# Installed console script
poetry run arctic-analytics-app

# Console entrypoint
poetry run arctic-analytics app

# Compatibility entrypoint
poetry run streamlit run app.py

# Package-native Streamlit entrypoint
poetry run streamlit run src/arctic_analytics/streamlit_app.py
```

For the full 15-minute local walkthrough, including sample data, generated code inspection, trace export, and research bundle export, use [quickstart_local.md](quickstart_local.md).

To inspect the evidence format without an API key, open [examples/sample_research_bundle](examples/sample_research_bundle).

## Citing Arctic Analytics

If Arctic Analytics supports work that appears in a paper, dataset, appendix, or methods section, cite the software using [CITATION.cff](CITATION.cff).

DOI: `10.5281/zenodo.18514535`

Suggested wording:

```text
Analyses were performed using Arctic Analytics v0.1.0 (DOI: 10.5281/zenodo.18514535).
```

Before citing a newer release, verify that the README, `CITATION.cff`, package version, and Zenodo record refer to the same version. See [docs/citing.md](docs/citing.md).

## Documentation

- [Quickstart: local artifact bundles](quickstart_local.md)
- [Structured dataset to research bundle walkthrough](docs/walkthrough_structured_bundle.md)
- [Local flow image capture instructions](docs/assets/README.md)
- [Sample bundle figure gap note](docs/sample_bundle_figure_gap.md)
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
