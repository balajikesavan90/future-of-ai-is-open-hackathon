"""Build local-first Arctic Analytics research artifact bundles."""

from __future__ import annotations

import json
import platform
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

from arctic_analytics import __version__
from arctic_analytics.artifacts.extractors import (
    extract_generated_code,
    extract_prompts,
    final_answer_markdown,
    json_safe,
    write_outputs_and_figures,
)
from arctic_analytics.artifacts.models import ResearchArtifactBundle, ResearchSession
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
    written.extend(write_outputs_and_figures(session.analysis_trace.data, outputs_dir, figures_dir))
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


def _analysis_trace_payload(session: ResearchSession) -> dict[str, Any]:
    if session.analysis_trace.data is not None:
        return session.analysis_trace.data
    return {
        "available": False,
        "reason": "No analysis trace was provided. This bundle packages available context and citation artifacts only.",
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


def _copy_citation(destination: Path) -> Path:
    root = Path(__file__).resolve().parents[3]
    source = root / "CITATION.cff"
    if source.exists():
        shutil.copyfile(source, destination)
    else:
        destination.write_text("message: Cite Arctic Analytics using the repository CITATION.cff metadata.\n")
    return destination


def _write_json(path: Path, data: Any) -> Path:
    path.write_text(json.dumps(json_safe(data), indent=2, default=str) + "\n")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.write_text(text)
    return path
