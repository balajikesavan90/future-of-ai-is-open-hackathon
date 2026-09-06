# Publication Workflow

Arctic Analytics is intended to support AI-assisted structured-data research workflows that produce inspectable artifacts for papers, datasets, methods, and appendices.

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
Researcher asks follow-up questions
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
Artifact bundle
    |
    v
Paper appendix or supplement
    |
    v
Publication
```

## 1. Upload Dataset(s) And Set Up Metadata

Start with one or more CSV datasets in the local Streamlit app. Review and edit the dataset description, column descriptions, data types, and primary key flags before analysis. The metadata should capture domain context that column names alone do not provide.

## 2. Run Iterative Agent Analysis

Use the local Streamlit app for analysis work that may support publication. Ask an initial research question, inspect the agent-visible context, generated code, tool calls, tool responses, outputs, and limitations, then ask follow-up questions as needed. The workflow is exploratory and iterative; the exported trace and bundle should reflect the session you actually reviewed.

## 3. Export Artifacts

After the analysis session, prepare a research bundle from the local Streamlit sidebar. The bundle packages the current session's trace, context, prompts, generated code, outputs, environment metadata, limitations, and citation files.

## 4. Review Bundle Contents

Review the generated files before using them in a paper:

- `run_manifest.json`: lightweight run metadata for review.
- `analysis_trace.json`: exported session trace.
- `context_bundle.json`: metadata and context supplied to the workflow.
- `prompts.json`: prompt material available for review.
- `generated_code/`: generated Python snippets from tool calls.
- `outputs/`: tool outputs and final answer material.
- `methods.md`: draft methods text.
- `environment.json`: software/runtime metadata.
- `software_citation.md` and `citation.cff`: citation metadata.
- `limitations.md`: limitations to disclose.

## 5. Prepare Appendix Or Supplement

Use the bundle as supporting material for an appendix or reproducibility supplement. The bundle is not yet a deterministic replay record, so preserve source data, exported bundles, and any manual review notes needed to justify claims.
