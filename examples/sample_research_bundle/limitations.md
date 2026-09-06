# Limitations

- Execution uses Python-level validation and runtime constraints, not isolated container or OS-level sandboxing.
- Trace export is a snapshot of current Streamlit session state, not a durable audit log.
- The trace is not replayable and does not include full dataset provenance records.
