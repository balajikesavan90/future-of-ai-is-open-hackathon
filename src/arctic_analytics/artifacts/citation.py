"""Citation metadata helpers for research artifact bundles."""

from __future__ import annotations

from importlib import resources

FALLBACK_CITATION_CFF = """cff-version: 1.2.0
message: "If you use this software, please cite it as below."
authors:
  - family-names: Kesavan
    given-names: Balaji
title: "Arctic Analytics"
version: 0.1.0
date-released: 2026-02-06
url: "https://github.com/balajikesavan90/arctic-analytics"
repository-code: "https://github.com/balajikesavan90/arctic-analytics"
license: MIT
type: software
doi: 10.5281/zenodo.18514535
"""


def citation_cff_text() -> str:
    try:
        return resources.files("arctic_analytics").joinpath("CITATION.cff").read_text()
    except (FileNotFoundError, ModuleNotFoundError):
        return FALLBACK_CITATION_CFF


def citation_doi() -> str | None:
    for line in citation_cff_text().splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() == "doi":
            return value.strip().strip('"').strip("'") or None
    return None
