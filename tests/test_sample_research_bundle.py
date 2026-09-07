import hashlib
import json
from pathlib import Path


def test_sample_research_bundle_trace_digest_matches_trace():
    bundle_dir = Path("examples/sample_research_bundle")
    manifest = json.loads((bundle_dir / "run_manifest.json").read_text())
    trace = json.loads((bundle_dir / "analysis_trace.json").read_text())
    canonical_trace = json.dumps(trace, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")

    assert manifest["analysis_trace_sha256"] == hashlib.sha256(canonical_trace).hexdigest()
