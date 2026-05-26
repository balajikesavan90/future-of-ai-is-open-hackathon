# Citing Arctic Analytics

Arctic Analytics is research software. If it supports an analysis, dataset, appendix, methods section, or publication, cite the software release used for the work.

## Software Citation

Use the repository `CITATION.cff` file as the source of citation metadata. The current DOI is:

```text
10.5281/zenodo.18514535
```

Suggested methods wording:

```text
Analyses were performed using Arctic Analytics v0.1.0 (DOI: 10.5281/zenodo.18514535), experimental open-source research software for metadata-aware, inspectable, constrained AI-assisted analysis over structured data.
```

Short citation wording:

```text
Arctic Analytics v0.1.0, DOI: 10.5281/zenodo.18514535.
```

## DOI Workflow

Before citing a release:

1. Confirm the package version in `src/arctic_analytics/__init__.py`.
2. Confirm `CITATION.cff` uses the same version.
3. Confirm the Zenodo record points to the same repository release or archive.
4. Archive research bundles, traces, source data, and publication appendices separately when needed.

## Zenodo Recommendations

Use Zenodo for release-level software citation. For a specific paper, archive the exact research bundle and source data used by that paper as supplementary material or a separate dataset record when data-sharing rules allow it.

Do not rely on the software DOI alone to reproduce a specific analysis. A paper should also preserve the relevant dataset, metadata, prompts, generated code, trace, environment information, and limitations.

## Paper Methods Example

```text
Structured-data analyses were supported by Arctic Analytics v0.1.0. Dataset metadata and column descriptions were reviewed before agent inference. The exported artifact bundle contains the analysis trace, prompts, generated code, tool outputs, environment snapshot, and software citation metadata. Agent-generated code and outputs were manually reviewed before inclusion in the manuscript.
```
