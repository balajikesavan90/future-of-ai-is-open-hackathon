import json
import zipfile
from io import BytesIO
import re
from pathlib import Path

from arctic_analytics.artifacts import (
    AnalysisTrace,
    ContextBundle,
    ResearchSession,
    build_research_bundle_zip,
    validate_research_bundle,
    write_research_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def test_write_research_bundle_from_minimal_session(tmp_path):
    trace = {
        "model": "gpt-test",
        "prompt_str": "Summarize the data.",
        "messages": [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Summarize the data."}],
            },
            {
                "type": "function_call",
                "name": "run_python_expression",
                "arguments": json.dumps(
                    {
                        "python_expression": "sales['amount'].sum()",
                        "reason": "Compute total sales.",
                    }
                ),
            },
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Total sales were 3."}],
            },
        ],
        "tool_calls": [
            {
                "type": "function_call",
                "name": "run_python_expression",
                "arguments": json.dumps(
                    {
                        "python_expression": "sales['amount'].sum()",
                        "reason": "Compute total sales.",
                    }
                ),
            }
        ],
        "outputs": [{"output": {"result": 3}}],
        "dataset_metadata": {"sales": {"column_names": ["amount"]}},
        "limitations": ["Example limitation."],
    }
    session = ResearchSession(
        prompt="Summarize the data.",
        analysis_trace=AnalysisTrace(trace),
        context_bundle=ContextBundle({"dataset_metadata": trace["dataset_metadata"], "researcher_notes": "Reviewed by analyst."}),
        researcher_notes="Reviewed by analyst.",
    )

    bundle = write_research_bundle(session, tmp_path / "bundle")

    assert (bundle.output_dir / "analysis_trace.json").exists()
    validation = validate_research_bundle(bundle.output_dir)
    assert validation.valid is True
    assert validation.missing == []
    manifest = json.loads((bundle.output_dir / "run_manifest.json").read_text())
    assert manifest["model"] == "gpt-test"
    assert manifest["provider"] == "openai"
    assert manifest["trace_present"] is True
    assert manifest["generated_by"] == "arctic analytics research bundle export"
    assert manifest["hash_algorithm"] == "sha256"
    assert manifest["dataset_content_sha256"] is None
    assert SHA256_PATTERN.match(manifest["metadata_or_context_sha256"])
    assert SHA256_PATTERN.match(manifest["analysis_trace_sha256"])
    assert (bundle.output_dir / "context_bundle.json").exists()
    assert (bundle.output_dir / "methods.md").read_text().startswith("# Draft Methods")
    citation = (bundle.output_dir / "citation.cff").read_text()
    assert "doi: 10.5281/zenodo.18514535" in citation
    assert "family-names: Kesavan" in citation
    context = json.loads((bundle.output_dir / "context_bundle.json").read_text())
    assert context["researcher_notes"] == "Reviewed by analyst."
    assert "sales['amount'].sum()" in (bundle.output_dir / "generated_code" / "001_run_python_expression.py").read_text()
    assert "Total sales were 3." in (bundle.output_dir / "outputs" / "final_answer.md").read_text()
    assert build_research_bundle_zip(session).startswith(b"PK")


def test_research_bundle_writes_raw_image_outputs_from_sanitized_trace(tmp_path):
    image_payload = "data:image/png;base64,iVBORw0KGgo="
    session = ResearchSession(
        analysis_trace=AnalysisTrace(
            {
                "outputs": [
                    {
                        "type": "function_call_output",
                        "output": {
                            "type": "image_base64",
                            "media_type": "image/png",
                            "truncated": True,
                        },
                    }
                ],
            }
        ),
        context_bundle=ContextBundle({}),
        raw_outputs=[{"type": "function_call_output", "output": image_payload}],
    )

    bundle = write_research_bundle(session, tmp_path / "bundle")

    figure_path = bundle.output_dir / "figures" / "001_figure.png"
    assert figure_path.exists()
    assert figure_path.read_bytes() == b"\x89PNG\r\n\x1a\n"
    assert not (bundle.output_dir / "outputs" / "001_output.json").exists()

    zip_bytes = build_research_bundle_zip(session)
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        assert "research_bundle/figures/001_figure.png" in archive.namelist()


def test_checked_in_sample_research_bundle_has_core_files():
    sample_bundle = ROOT / "examples" / "sample_research_bundle"
    expected = [
        "README.md",
        "run_manifest.json",
        "analysis_trace.json",
        "context_bundle.json",
        "prompts.json",
        "methods.md",
        "generated_code/001_run_python_expression.py",
        "outputs/final_answer.md",
        "environment.json",
        "citation.cff",
        "software_citation.md",
        "limitations.md",
    ]

    for relative_path in expected:
        assert (sample_bundle / relative_path).exists(), relative_path

    manifest = json.loads((sample_bundle / "run_manifest.json").read_text())
    assert manifest["run_id"] == "tips-example-openai-api-session"
    assert manifest["source_data_filename"] == "examples/sample_dataset.csv"
    assert manifest["metadata_filename"] == "examples/sample_metadata.json"
    assert manifest["trace_present"] is True
    assert manifest["hash_algorithm"] == "sha256"
    assert SHA256_PATTERN.match(manifest["dataset_content_sha256"])
    assert SHA256_PATTERN.match(manifest["metadata_or_context_sha256"])
    assert SHA256_PATTERN.match(manifest["analysis_trace_sha256"])


def test_bundle_validation_reports_missing_files(tmp_path):
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "README.md").write_text("example\n")

    validation = validate_research_bundle(bundle_dir)

    assert validation.valid is False
    assert "run_manifest.json" in validation.missing
    assert "generated_code/" in validation.missing
