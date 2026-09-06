# Walkthrough: From Structured Dataset To Inspectable Research Bundle

This walkthrough uses the built-in `penguins` sample dataset to show a research-flavored local workflow without adding a large dataset.

## Research-Style Question

How do penguin body mass, flipper length, bill dimensions, species, and island relate to each other, and which relationships are strong enough to justify follow-up analysis?

## Local Workflow

1. Start the local Streamlit app.
2. Open **Analyze Data**.
3. Select **Penguins Dataset**.
4. Review the generated data dictionary before analysis.
5. Edit the dataset description and column descriptions if they are incomplete.
6. Select **Save Data Dictionary and Proceed**.

## Example Prompt

```text
Analyze relationships between penguin body mass, flipper length, bill dimensions, species, and island. Identify one pattern that looks scientifically interesting, create a plot, and explain what should be checked before treating it as evidence.
```

## Review Before Export

Inspect the generated Python, tool-call reason, tool response, plotted output, and final answer. Treat the response as an exploratory result until the code and outputs match the source data and metadata.

## Export Evidence

Use the sidebar **Analysis Trace** section:

1. Select **Prepare Trace Export**.
2. Select **Export Analysis Trace**.
3. Select **Prepare Research Bundle**.
4. Select **Export Research Bundle**.

The bundle should contain context, trace, prompts, generated code, outputs, methods wording, limitations, environment metadata, and citation guidance.

## Limitations

This is an exploratory agent-assisted workflow. The exported bundle supports human review and downstream methods or appendix work, but it is not a deterministic replay record and does not prove the scientific claim.
