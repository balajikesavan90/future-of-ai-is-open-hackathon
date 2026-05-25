# Release Checklist

Use this checklist before creating a public release, package publication, or Zenodo archive.

## Version And Citation

- Update `src/arctic_analytics/__init__.py`.
- Update `pyproject.toml`.
- Update `CITATION.cff`.
- Update `.zenodo.json`.
- Verify the README citation section points to the current DOI or release DOI.
- Verify the Zenodo record and repository release/tag refer to the same version.

## Documentation

- Verify `README.md` still describes implemented behavior conservatively.
- Verify `docs/SECURITY.md`, `docs/threat_model.md`, and `docs/security_assumptions.md` still match the execution layer.
- Verify `docs/reproducibility.md` matches trace and example behavior.
- Verify archive notes in `docs/archive/` do not describe active features.
- Verify architecture/debt docs still match package structure.

## Examples

- Verify `examples/sample_dataset.csv` and `examples/sample_metadata.json` still load.
- Verify `examples/sample_trace_export.json` validates against `schemas/analysis_trace.schema.json`.
- If the sample trace is regenerated, record the model and note that it remains illustrative and external API dependent.

## Tests

- Run `poetry run pytest`.
- Confirm security tests still describe application-level restrictions, not sandbox guarantees.
- Confirm trace schema validation passes.

## Publication Hygiene

- Check `git status --short` for accidental cache, secret, trace export, or virtualenv files.
- Confirm `.streamlit/secrets.toml` is not tracked.
- Confirm release notes mention current limitations: no deterministic replay, no security isolation, no durable audit log, and no governance guarantees.
