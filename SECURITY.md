# Security

Arctic Analytics runs model-generated Python through application-level checks before execution. These controls reduce accidental misuse, but they are not a complete sandbox.

## Execution Restrictions

- Code is parsed with Python `ast` before execution.
- Imports are limited to an allowlist in `src/arctic_analytics/core/security.py`.
- Known dangerous calls and modules, including OS/process/file/network-oriented APIs, are blocked during validation.
- Execution receives restricted globals and the loaded dataframes, not a normal unrestricted Python environment.
- Tool outputs are constrained to supported table, series, scalar, text, and plot result types.
- Long-running execution is interrupted by a timeout.

## Blocked Imports And Calls

The validator blocks imports and calls associated with filesystem access, process execution, dynamic code execution, networking, package installation, environment inspection, and interpreter escape hatches. Examples include `os`, `subprocess`, `socket`, `requests`, `open`, `eval`, `exec`, `compile`, `__import__`, and similar APIs.

The allowlist is intentionally narrow and centered on structured-data analysis libraries such as pandas, numpy, seaborn, matplotlib, datetime, math, and statsmodels.

## Timeout Behavior

Generated code is executed with a runtime timeout. If the timeout is reached, execution returns an error instead of an analysis result.

The timeout is a responsiveness control. It is not a CPU, memory, or process isolation boundary.

## What Is Not Provided

- No OS sandbox.
- No container sandbox.
- No memory isolation.
- No network isolation.
- No filesystem isolation beyond blocked Python APIs.
- No protection against vulnerabilities in allowed libraries.
- No durable audit log.
- No replayable run record.

## Residual Risks

Allowed libraries may expose unexpected behavior or resource-heavy operations. Python-level validation can miss edge cases. Large dataframes or expensive generated code can still consume memory or CPU before timeout handling completes. Users should treat outputs as reviewable analysis artifacts, not trusted autonomous decisions.

For untrusted users, sensitive datasets, or production workloads, run Arctic Analytics inside an external sandbox such as a locked-down container, VM, or managed execution service with explicit CPU, memory, filesystem, and network controls.
