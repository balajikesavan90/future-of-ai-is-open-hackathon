"""Validate version fields that must agree for a release."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CFF_FILES = (ROOT / "CITATION.cff", ROOT / "src/python_data_analysis_agent/CITATION.cff")
FALLBACK_CITATION = ROOT / "src/python_data_analysis_agent/artifacts/citation.py"
ZENODO_METADATA = ROOT / ".zenodo.json"


def cff_version(path: Path) -> str | None:
    match = re.search(r'^version:\s*["\']?([^\s"\']+)', path.read_text(), flags=re.MULTILINE)
    return match.group(1) if match else None


def fallback_citation_version(path: Path) -> str | None:
    match = re.search(
        r'FALLBACK_CITATION_CFF\s*=\s*""".*?^version:\s*["\']?([^\s"\']+)',
        path.read_text(),
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="expected release version, without the leading 'v'")
    expected_version = parser.parse_args().version

    values = {
        str(CFF_FILES[0].relative_to(ROOT)): cff_version(CFF_FILES[0]),
        str(CFF_FILES[1].relative_to(ROOT)): cff_version(CFF_FILES[1]),
        str(FALLBACK_CITATION.relative_to(ROOT)): fallback_citation_version(FALLBACK_CITATION),
        str(ZENODO_METADATA.relative_to(ROOT)): json.loads(ZENODO_METADATA.read_text()).get("version"),
    }

    failures = [
        f"{path}: expected {expected_version!r}, found {version!r}"
        for path, version in values.items()
        if version != expected_version
    ]
    if CFF_FILES[0].read_bytes() != CFF_FILES[1].read_bytes():
        failures.append("CITATION.cff and src/python_data_analysis_agent/CITATION.cff differ")

    if failures:
        print("Release metadata validation failed:", *failures, sep="\n- ", file=sys.stderr)
        return 1

    print(f"Release metadata matches version {expected_version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
