# Examples

This directory contains a small illustrative example of the inspectable Arctic Analytics workflow.

## Files

- `sample_dataset.csv`: the bundled `tips` dataset exported as CSV.
- `sample_metadata.json`: the `tips` dataset description and data dictionary used for context construction.
- `sample_trace_export.json`: trace JSON generated through the application's OpenAI Responses path and trace export builder, showing the real `construct_system_message()` output, model-produced tool call, constrained execution output, and limitations.

## Evidence Labels

| File | Label | Notes |
| --- | --- | --- |
| `sample_dataset.csv` | Reproducible | Static bundled CSV input. |
| `sample_metadata.json` | Reproducible | Static metadata input for the sample dataset. |
| `sample_trace_export.json` | Illustrative, external API dependent | Generated through a real OpenAI API call and useful for inspection, but not deterministically replayable. |

## Walkthrough

1. Load `sample_dataset.csv`, which contains the `tips` dataset.
2. Review and edit the metadata in `sample_metadata.json`.
3. Ask the focused analysis question used in the trace: `Which day has the highest average tip percentage? Calculate tip percentage as tip divided by total_bill.`
4. Review the tool call and generated code before relying on the result.
5. Export the trace and compare it with `sample_trace_export.json`.

## Trace Provenance

`sample_trace_export.json` was generated with Arctic Analytics' application path using a real external OpenAI API call to `gpt-5-nano-2025-08-07`. The example session state uses the bundled `tips` dataset and its data dictionary, constructs the system prompt with `arctic_analytics.core.system_messages.construct_system_message()`, calls `arctic_analytics.llm.ai.generate_ai_response()`, executes the model-produced tool call through the constrained execution path, then exports the same JSON structure used by the Streamlit "Export Analysis Trace" control.

The goal is inspectability: the dataset, metadata, tool call, generated code, result, and limitations should all be reviewable.

## Limitations

- The trace is a snapshot, not a replayable record.
- The example depends on external model/API behavior.
- Model outputs may vary across time, model versions, and configuration.
- Execution restrictions are application-level constraints, not security isolation.
