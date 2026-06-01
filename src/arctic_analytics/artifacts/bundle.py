"""Build local-first Arctic Analytics research artifact bundles."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from importlib import metadata
from importlib import resources
from pathlib import Path
from typing import Any
from uuid import uuid4

from arctic_analytics import __version__
from arctic_analytics.artifacts.extractors import (
    extract_generated_code,
    extract_prompts,
    final_answer_markdown,
    json_safe,
    write_outputs_and_figures,
)
from arctic_analytics.artifacts.models import BundleValidationResult, ResearchArtifactBundle, ResearchSession
from arctic_analytics.artifacts.text import (
    render_bundle_readme,
    render_limitations,
    render_methods,
    render_software_citation,
)


def write_research_bundle(session: ResearchSession, output_dir: Path | str) -> ResearchArtifactBundle:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    written.append(_write_json(output_path / "run_manifest.json", _run_manifest_payload(session)))
    written.append(_write_json(output_path / "analysis_trace.json", _analysis_trace_payload(session)))
    written.append(_write_json(output_path / "context_bundle.json", session.context_bundle.data))
    written.append(_write_json(output_path / "prompts.json", extract_prompts(session)))
    written.append(_write_json(output_path / "environment.json", _environment_payload(session)))
    written.append(_write_text(output_path / "methods.md", render_methods(session)))
    written.append(_write_text(output_path / "software_citation.md", render_software_citation()))
    written.append(_write_text(output_path / "limitations.md", render_limitations(session)))
    written.append(_write_text(output_path / "README.md", render_bundle_readme(session)))
    written.append(_copy_citation(output_path / "citation.cff"))

    generated_code_dir = output_path / "generated_code"
    generated_code_dir.mkdir(exist_ok=True)
    code_snippets = extract_generated_code(session.analysis_trace.data)
    if code_snippets:
        for snippet in code_snippets:
            path = generated_code_dir / snippet["filename"]
            header = f"# Tool: {snippet['tool_name']}\n# Reason: {snippet['reason']}\n\n"
            written.append(_write_text(path, header + snippet["code"].rstrip() + "\n"))
    else:
        written.append(_write_text(generated_code_dir / "generated_code_unavailable.md", "No generated code snippets were available.\n"))

    outputs_dir = output_path / "outputs"
    figures_dir = output_path / "figures"
    written.extend(write_outputs_and_figures(session.analysis_trace.data, outputs_dir, figures_dir, session.raw_outputs))
    written.append(_write_text(outputs_dir / "final_answer.md", final_answer_markdown(session.analysis_trace.data)))

    return ResearchArtifactBundle(output_dir=output_path, files=written)


def build_research_bundle_zip(session: ResearchSession) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_dir = Path(tmpdir) / "research_bundle"
        write_research_bundle(session, bundle_dir)
        zip_path = Path(tmpdir) / "research_bundle.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(bundle_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(bundle_dir.parent))
        return zip_path.read_bytes()


EXPECTED_BUNDLE_PATHS = [
    "README.md",
    "run_manifest.json",
    "context_bundle.json",
    "analysis_trace.json",
    "prompts.json",
    "generated_code/",
    "outputs/",
    "figures/",
    "environment.json",
    "methods.md",
    "limitations.md",
    "software_citation.md",
    "citation.cff",
]


def validate_research_bundle(output_dir: Path | str) -> BundleValidationResult:
    """Check that a bundle has the expected MVP files and directories."""
    root = Path(output_dir)
    missing = []
    warnings = []

    for relative_path in EXPECTED_BUNDLE_PATHS:
        path = root / relative_path.rstrip("/")
        if relative_path.endswith("/"):
            if not path.is_dir():
                missing.append(relative_path)
        elif not path.is_file():
            missing.append(relative_path)

    if (root / "figures").is_dir() and not any((root / "figures").iterdir()):
        warnings.append("figures/ exists but does not contain exported image artifacts.")
    if (root / "generated_code").is_dir() and not any((root / "generated_code").iterdir()):
        warnings.append("generated_code/ exists but does not contain generated code artifacts.")

    return BundleValidationResult(valid=not missing, missing=missing, warnings=warnings)


def _analysis_trace_payload(session: ResearchSession) -> dict[str, Any]:
    if session.analysis_trace.data is not None:
        return session.analysis_trace.data
    return {
        "available": False,
        "reason": "No analysis trace was provided. This bundle packages available context and citation artifacts only.",
    }


def _run_manifest_payload(session: ResearchSession) -> dict[str, Any]:
    trace = session.analysis_trace.data or {}
    source_data_filename = _source_data_filename(session.source_files)
    metadata_filename = _metadata_filename(session.source_files)
    model = trace.get("model")
    return {
        "run_id": trace.get("session_id") or str(uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "arctic_analytics_version": __version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "model": model,
        "provider": _provider_for_model(model),
        "source_data_filename": source_data_filename,
        "metadata_filename": metadata_filename,
        "hash_algorithm": "sha256",
        "dataset_content_sha256": _file_sha256(source_data_filename),
        "metadata_or_context_sha256": _metadata_or_context_sha256(session, metadata_filename),
        "analysis_trace_sha256": _trace_sha256(session),
        "trace_present": session.analysis_trace.available,
        "generated_by": session.command or "arctic analytics research bundle export",
        "limitations": [
            "This manifest is a lightweight review aid, not a deterministic replay record.",
            "Source data and metadata filenames and hashes are recorded only when available from the active session.",
            "Model outputs may vary across model versions, providers, and time.",
        ],
    }


def _environment_payload(session: ResearchSession) -> dict[str, Any]:
    return {
        "arctic_analytics_version": __version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": session.command,
        "source_files": session.source_files,
        "dependencies": _selected_dependency_versions(),
    }


def _selected_dependency_versions() -> dict[str, str | None]:
    packages = ["streamlit", "pandas", "numpy", "openai", "matplotlib", "seaborn", "plotly", "statsmodels"]
    versions: dict[str, str | None] = {}
    for package in packages:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def _provider_for_model(model: Any) -> str | None:
    if not isinstance(model, str) or not model:
        return None
    if model.startswith(("gpt-", "o3", "o4")):
        return "openai"
    return None


def _source_data_filename(source_files: dict[str, Any]) -> str | None:
    data = source_files.get("data")
    if data:
        return str(data)

    uploaded_files = source_files.get("uploaded_files")
    if isinstance(uploaded_files, list) and uploaded_files:
        return ", ".join(str(item) for item in uploaded_files)

    source = source_files.get("source")
    if source:
        return str(source)

    return None


def _metadata_filename(source_files: dict[str, Any]) -> str | None:
    metadata_file = source_files.get("metadata")
    if metadata_file:
        return str(metadata_file)
    return None


def _file_sha256(filename: str | None) -> str | None:
    if not filename:
        return None

    path = Path(filename)
    if path.is_file():
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    return None


def _json_sha256(data: Any) -> str | None:
    if data is None:
        return None
    payload = json.dumps(json_safe(data), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _metadata_or_context_sha256(session: ResearchSession, metadata_filename: str | None) -> str | None:
    return _file_sha256(metadata_filename) or _json_sha256(session.context_bundle.data)


def _trace_sha256(session: ResearchSession) -> str | None:
    return _json_sha256(session.analysis_trace.data)


def _copy_citation(destination: Path) -> Path:
    try:
        citation_text = resources.files("arctic_analytics").joinpath("CITATION.cff").read_text()
    except (FileNotFoundError, ModuleNotFoundError):
        citation_text = "message: Cite Arctic Analytics using the repository CITATION.cff metadata.\n"
    destination.write_text(citation_text)
    return destination


def _write_json(path: Path, data: Any) -> Path:
    path.write_text(json.dumps(json_safe(data), indent=2, default=str) + "\n")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.write_text(text)
    return path
