# Reproducibility

Arctic Analytics currently supports partial reproducibility through inspectable artifacts. It does not provide deterministic replay.

## Current State

- Trace exports capture a snapshot of Streamlit session state, messages, tool calls, outputs, metadata, errors, model name, cost, timestamp, trace schema version, and package version when available.
- A JSON Schema for the lightweight trace shape is available at `schemas/analysis_trace.schema.json` and is validated in tests.
- Examples provide a small dataset, metadata, and one trace generated through the application path.
- Tests cover selected data import, prompt construction, execution restriction, dispatch, and trace export behavior.

## Missing

- Replayability.
- Dataset hashes.
- Prompt hashes.
- Output hashes.
- Stable run manifests.
- Stable dataset, prompt, tool-call, and output IDs.
- Full semantic trace validation beyond the current structural schema.

## Roadmap

Future optional additions:

- Dataset hashes.
- Prompt hashes.
- Output hashes.
- Broader trace schema coverage.
- Run manifests.

These additions are not implemented today.
