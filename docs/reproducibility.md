# Reproducibility

Arctic Analytics currently supports partial reproducibility through inspectable artifacts. It does not provide deterministic replay.

## Current State

- Trace exports capture a snapshot of Streamlit session state, messages, tool calls, outputs, metadata, errors, cost, timestamp, trace schema version, and package version when available. Upload traces can resume an analysis only after the original CSV files are uploaded again, content-verified with SHA-256 fingerprints, and reviewed. Only trace-schema version 0.3.0 exports with a resume manifest are resumable; those traces retain chart payloads. The app does not prepare trace exports larger than 10 MiB, matching the resume import limit.
- Research bundle exports package run manifests, traces, context bundles, prompts, generated code snippets, tool outputs, environment metadata, methods drafts, limitations, and citation files for review.
- Run manifests include selected SHA-256 hashes for source dataset content, context metadata, and the analysis trace when that content is available.
- A JSON Schema for the lightweight trace shape is available at `schemas/analysis_trace.schema.json` and is validated in tests.
- Examples provide a small dataset, metadata, and one trace generated through the application path.
- Tests cover selected data import, prompt construction, execution restriction, dispatch, and trace export behavior.

## Missing

- Replayability.
- Prompt hashes.
- Output hashes.
- Stable dataset, prompt, tool-call, and output IDs.
- Full semantic trace validation beyond the current structural schema.

## Artifact Bundles

Artifact bundles are publication-support packages, not replayable runs. They help researchers preserve the evidence needed for review: metadata, prompts, generated code, tool outputs, environment metadata, limitations, and citation guidance.

Artifact bundles are created from the local Streamlit app after an analysis session. Use the sidebar export controls to prepare and download the bundle.

## Roadmap

Future optional additions:

- Prompt hashes.
- Output hashes.
- Broader trace schema coverage.
- More detailed run manifests.

These additions are not implemented today.
