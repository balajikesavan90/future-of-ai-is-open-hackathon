import json
from pathlib import Path

from arctic_analytics.artifacts import (
    AnalysisTrace,
    ContextBundle,
    ResearchSession,
    build_research_bundle_zip,
    write_research_bundle,
)


ROOT = Path(__file__).resolve().parents[1]


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
        context_bundle=ContextBundle({"dataset_metadata": trace["dataset_metadata"]}),
    )

    bundle = write_research_bundle(session, tmp_path / "bundle")

    assert (bundle.output_dir / "analysis_trace.json").exists()
    assert (bundle.output_dir / "context_bundle.json").exists()
    assert (bundle.output_dir / "methods.md").read_text().startswith("# Draft Methods")
    assert "sales['amount'].sum()" in (bundle.output_dir / "generated_code" / "001_run_python_expression.py").read_text()
    assert "Total sales were 3." in (bundle.output_dir / "outputs" / "final_answer.md").read_text()
    assert build_research_bundle_zip(session).startswith(b"PK")


def test_checked_in_sample_research_bundle_has_core_files():
    sample_bundle = ROOT / "examples" / "sample_research_bundle"
    expected = [
        "README.md",
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
