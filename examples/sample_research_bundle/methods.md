# Draft Methods

Analyses were supported by Arctic Analytics v0.1.0, experimental open-source research software for metadata-aware, inspectable, constrained AI-assisted analysis over structured data.

The analysis workflow used an agent to review structured-data context before producing inspectable Python tool calls. The context supplied to the agent included dataset metadata, data dictionary information, summary statistics when available, and a researcher-provided prompt.

## Analysis Question

Which day has the highest average tip percentage? Calculate tip percentage as tip divided by total_bill.

## Data And Context

Datasets represented in the exported context bundle: tips.

## Agent And Model

Model recorded in the trace: gpt-5.4-mini-2026-03-17.

## Execution Summary

The artifact bundle includes the exported analysis trace, prompts, generated code snippets, tool outputs, and limitations. Generated Python was intended for application-level constrained execution and human review. The bundle contains 1 generated code snippet(s).

## Human Review

This methods draft is generated for review and publication support. Researchers should verify that the metadata, generated code, outputs, and final claims match the source data and intended analysis before citing or publishing results.
