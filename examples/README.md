# Examples

This directory contains small illustrative examples of the inspectable Arctic Analytics workflow and research artifact bundle format. The examples are useful for review and documentation, but they are not deterministic replay artifacts.

## Labels

| File | Labels | Notes |
| --- | --- | --- |
| `sample_dataset.csv` | Replayable input | Static CSV copy of the bundled `tips` dataset. It can be loaded without an external model call. |
| `sample_metadata.json` | Replayable input | Static dataset description and data dictionary used for context construction. |
| `sample_trace_export.json` | Illustrative, external dependency, experimental | Generated through the application path with an external OpenAI API call. It is schema-validated in tests, but it is not deterministically replayable. |
| `sample_research_bundle/` | Illustrative artifact bundle | Checked-in bundle format example generated from the sample dataset, metadata, prompt, and trace. |

## Walkthrough

1. Load `sample_dataset.csv`, which contains the `tips` dataset.
2. Review and edit the metadata in `sample_metadata.json`.
3. Ask the focused analysis question used in the trace: `Which day has the highest average tip percentage? Calculate tip percentage as tip divided by total_bill.`
4. Review the visible tool call, generated code, tool response, and final answer before relying on the result.
5. Export the trace and compare its structure with `sample_trace_export.json`.
6. Inspect `sample_research_bundle/` to see the publication-support artifact format.

## Research Bundle Example

The checked-in `sample_research_bundle/` directory lets reviewers inspect the artifact format without using an API key. In normal use, research bundles are created from the local Streamlit sidebar after an analysis session.

## Trace Provenance

`sample_trace_export.json` and `sample_research_bundle/` were generated with Arctic Analytics' application path using a real external OpenAI API call. The checked-in trace records the current supported example model, `gpt-5.4-mini-2026-03-17`.

To regenerate both the trace and the checked-in research bundle:

```bash
poetry run python scripts/regenerate_example_trace.py
```

To regenerate only the trace:

```bash
poetry run python scripts/regenerate_example_trace.py --trace-only
```

To test regeneration without overwriting the checked-in bundle:

```bash
poetry run python scripts/regenerate_example_trace.py \
  --output /tmp/sample_trace_export.json \
  --bundle-output /tmp/sample_research_bundle
```

The script reads `OPENAI_API_KEY` from the environment first, then falls back to Streamlit secrets, such as `.streamlit/secrets.toml`.

The example session state uses the bundled `tips` dataset and its data dictionary, constructs the system prompt with `arctic_analytics.core.system_messages.construct_system_message()`, calls `arctic_analytics.llm.ai.generate_ai_response()`, executes the model-produced tool call through the constrained execution path, exports the same JSON structure used by the Streamlit "Export Analysis Trace" control, and then writes `sample_research_bundle/` through the standard artifact bundle writer.

## Limitations

- The trace is a snapshot, not a replayable run record.
- The sample trace depends on external model/API behavior.
- Model outputs may vary across time, model versions, and configuration.
- The schema validates structure only; it does not prove correctness of the model answer or generated code.
- Execution restrictions are application-level constraints, not security isolation.
- Research bundles package review artifacts; they are not deterministic replay records.
