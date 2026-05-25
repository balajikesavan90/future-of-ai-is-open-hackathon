# Design Principles

Arctic Analytics is an experimental framework for metadata-aware, transparent, and constrained AI-assisted analysis over structured data. These principles describe what the project should emphasize as it evolves.

## Context Before Inference

Structured-data analysis depends on context. Column names and raw values are rarely enough. Arctic Analytics therefore collects and injects metadata before model inference, including:

- Dataset descriptions.
- Column descriptions.
- Data types.
- Primary key flags.
- Dataframe shape.
- Summary statistics.
- Missing-value counts.
- Small row samples.

The current implementation lets users edit data dictionaries before analysis. This makes context explicit and reviewable instead of leaving the model to infer meaning from column names alone.

Future work should make this context more structured. A context bundle should be exportable, hashable, and inspectable without requiring a Streamlit session.

## Transparency Over Magic

Arctic Analytics should not hide analysis behind opaque assistant behavior. The user should be able to inspect:

- The system prompt.
- User and assistant messages.
- Generated Python code.
- Tool calls.
- Tool-call reasons.
- Tool responses.
- Returned tables or plots.

The current Streamlit app exposes much of this information in expanders and in the sidebar. The lightweight trace export captures a JSON snapshot of the current session state. This is useful for inspection, but it is not a durable audit log or replayable run.

## Constraints Over Unrestricted Execution

Generated code should run under constraints. The current implementation uses AST validation, an import whitelist, a dangerous-function blacklist, restricted globals, output-type checks, and a runtime timeout.

These controls are useful, but they are application-level Python restrictions. They are not OS-level or container isolation. Public documentation and UI copy should be precise about that limitation.

Future execution work should move toward isolated processes or containers, resource limits, stronger filesystem/network controls, and clearer policy configuration.

## Human Accountability

Arctic Analytics should support human review rather than imply autonomous correctness. Users remain accountable for checking:

- Whether the injected metadata is correct.
- Whether the generated code matches the analytical intent.
- Whether intermediate tool results are reasonable.
- Whether final outputs are supported by the data.

The product language should avoid claims that the system is an autonomous analyst, a general AI copilot, or a replacement for domain expertise.

## Minimal Claims

Arctic Analytics can currently claim:

- Metadata-aware context construction.
- Editable data dictionaries.
- Visible generated code and tool calls.
- Python-level constrained execution.
- Inspectable Streamlit workflows.
- Lightweight trace export from current session state.

It should not currently claim:

- Enterprise governance.
- Secure sandboxing.
- Durable auditability.
- Replayable reproducibility.
- Role-based access control.
- Dataset provenance.
- Novel agent architecture.
