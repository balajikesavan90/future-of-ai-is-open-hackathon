import json
import sys

import pytest

from scripts import validate_release_metadata as validator


@pytest.fixture
def release_metadata(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    package = root / "src" / "python_data_analysis_agent"
    artifacts = package / "artifacts"
    artifacts.mkdir(parents=True)

    root_cff = root / "CITATION.cff"
    packaged_cff = package / "CITATION.cff"
    cff_text = 'cff-version: 1.2.0\nversion: "2.0.0"\n'
    root_cff.write_text(cff_text)
    packaged_cff.write_text(cff_text)

    fallback = artifacts / "citation.py"
    fallback.write_text('FALLBACK_CITATION_CFF = """\nversion: 2.0.0\n"""\n')

    zenodo = root / ".zenodo.json"
    zenodo.write_text(json.dumps({"version": "2.0.0"}))

    monkeypatch.setattr(validator, "ROOT", root)
    monkeypatch.setattr(validator, "CFF_FILES", (root_cff, packaged_cff))
    monkeypatch.setattr(validator, "FALLBACK_CITATION", fallback)
    monkeypatch.setattr(validator, "ZENODO_METADATA", zenodo)
    return {
        "root_cff": root_cff,
        "packaged_cff": packaged_cff,
        "fallback": fallback,
        "zenodo": zenodo,
    }


def run_validation(monkeypatch, version="2.0.0"):
    monkeypatch.setattr(sys, "argv", ["validate_release_metadata.py", version])
    return validator.main()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("version: 2.0.0\n", "2.0.0"),
        ('version: "2.0.0"\n', "2.0.0"),
        ("title: Example\n", None),
    ],
)
def test_cff_version_parses_expected_field(tmp_path, text, expected):
    metadata = tmp_path / "citation.cff"
    metadata.write_text(text)

    assert validator.cff_version(metadata) == expected


def test_fallback_citation_version_requires_fallback_constant(tmp_path):
    citation = tmp_path / "citation.py"
    citation.write_text('FALLBACK_CITATION_CFF = """\nversion: 2.0.0\n"""\n')

    assert validator.fallback_citation_version(citation) == "2.0.0"
    citation.write_text('OTHER_CITATION_CFF = """\nversion: 2.0.0\n"""\n')
    assert validator.fallback_citation_version(citation) is None


def test_release_metadata_validation_succeeds_when_versions_match(release_metadata, monkeypatch, capsys):
    assert run_validation(monkeypatch) == 0
    assert "Release metadata matches version 2.0.0." in capsys.readouterr().out


@pytest.mark.parametrize(
    ("field", "expected_message"),
    [
        ("root_cff", "CITATION.cff: expected '2.0.0', found '9.9.9'"),
        ("packaged_cff", "src/python_data_analysis_agent/CITATION.cff: expected '2.0.0', found '9.9.9'"),
        ("fallback", "src/python_data_analysis_agent/artifacts/citation.py: expected '2.0.0', found '9.9.9'"),
        ("zenodo", ".zenodo.json: expected '2.0.0', found '9.9.9'"),
    ],
)
def test_release_metadata_validation_rejects_mismatched_versions(release_metadata, monkeypatch, capsys, field, expected_message):
    path = release_metadata[field]
    if field == "zenodo":
        path.write_text(json.dumps({"version": "9.9.9"}))
    else:
        path.write_text(path.read_text().replace("2.0.0", "9.9.9"))

    assert run_validation(monkeypatch) == 1
    assert expected_message in capsys.readouterr().err


def test_release_metadata_validation_rejects_divergent_cff_files(release_metadata, monkeypatch, capsys):
    release_metadata["packaged_cff"].write_text('cff-version: 1.2.0\nversion: "2.0.0"\nabstract: Different\n')

    assert run_validation(monkeypatch) == 1
    assert "CITATION.cff and src/python_data_analysis_agent/CITATION.cff differ" in capsys.readouterr().err
