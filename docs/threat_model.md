# Threat Model

Arctic Analytics is an experimental framework. Its execution controls are application-level restrictions for generated Python, not a security boundary.

## In Scope

- Unsafe imports requested by model-generated code.
- Prompt-generated code that attempts file, process, network, environment, or dynamic execution access.
- Filesystem access through blocked Python APIs such as `open`.
- Timeout failures and long-running generated code.
- Output-shape constraints for tables, scalars, text, and plots.

## Out Of Scope

- Adversarial model compromise.
- Container escapes.
- OS isolation.
- Malicious dependency chains.
- Vulnerabilities in allowed third-party libraries.
- Multi-user access control.
- Governance guarantees or audit-grade provenance.

## Current Boundary

The current boundary is Python AST validation, import and function restrictions, restricted globals, result-type checks, and a timeout. This can reduce accidental misuse and some unsafe generated code paths, but it is not sufficient for untrusted execution.
