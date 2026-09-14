"""Lightweight models for local-first research artifact exports."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


@dataclass
class AnalysisTrace:
    """A captured Python Data Analysis Agent analysis trace."""

    data: JsonDict | None = None

    @property
    def available(self) -> bool:
        return self.data is not None


@dataclass
class ContextBundle:
    """Context and metadata supplied to a Python Data Analysis Agent workflow."""

    data: JsonDict


@dataclass
class ResearchSession:
    """Provider-independent inputs needed to generate a research artifact bundle."""

    prompt: str | None = None
    analysis_trace: AnalysisTrace = field(default_factory=AnalysisTrace)
    context_bundle: ContextBundle = field(default_factory=lambda: ContextBundle({}))
    source_files: JsonDict = field(default_factory=dict)
    researcher_notes: str | None = None
    assumptions: list[str] = field(default_factory=list)
    command: str | None = None
    raw_outputs: list[Any] = field(default_factory=list)
    model: str | None = None
    retained_output_bytes: dict[str, bytes] = field(default_factory=dict)


@dataclass
class ResearchArtifactBundle:
    """Description of a written research artifact bundle."""

    output_dir: Path
    files: list[Path]


@dataclass
class BundleValidationResult:
    """Lightweight completeness check result for a research artifact bundle."""

    valid: bool
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
