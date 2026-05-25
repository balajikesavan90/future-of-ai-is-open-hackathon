#!/usr/bin/env python3
"""Regenerate examples/sample_trace_export.json with a real OpenAI API call."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


DEFAULT_PROMPT = "Which day has the highest average tip percentage? Calculate tip percentage as tip divided by total_bill."
DEFAULT_MODEL = "gpt-5.4-mini-2026-03-17"


class NullContainer:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def data_dictionary_json(metadata):
    rows = []
    for column in metadata["columns"]:
        rows.append(
            {
                "Primary Key": column.get("primary_key", False),
                "Column Name": column["name"],
                "Data Type": column["data_type"],
                "Description": column["description"],
            }
        )
    return pd.DataFrame(rows).to_json(orient="index")


def load_vetted_files(dataset_path, metadata_path):
    metadata = json.loads(metadata_path.read_text())
    dataset_name = metadata["dataset_name"]
    dataframe = pd.read_csv(dataset_path)

    for column in metadata["columns"]:
        column_name = column["name"]
        data_type = column["data_type"]
        if data_type == "category":
            dataframe[column_name] = dataframe[column_name].astype("category")
        elif data_type in {"Float64", "Int64"}:
            dataframe[column_name] = dataframe[column_name].astype(data_type)

    return {
        dataset_name: {
            "dataset_description": metadata["dataset_description"],
            "columns_names": dataframe.columns,
            "data_types": dataframe.dtypes,
            "pandas_describe": dataframe.describe(include="all"),
            "primary_key": [
                column["name"]
                for column in metadata["columns"]
                if column.get("primary_key", False)
            ],
            "dataframe": dataframe,
            "data_dictionary_json": data_dictionary_json(metadata),
        }
    }


def seed_session_state(session_id, model, prompt, vetted_files):
    from arctic_analytics.core.system_messages import construct_system_message
    from arctic_analytics.llm.ai import construct_welcome_message

    st.session_state.clear()
    st.session_state["session_id"] = session_id
    st.session_state["model"] = model
    st.session_state["cost"] = 0
    st.session_state["context_window_usage"] = 0
    st.session_state["vetted_files"] = vetted_files
    st.session_state["messages_container"] = NullContainer()

    system_message = construct_system_message(vetted_files)
    st.session_state["messages"] = [
        {
            "role": "system",
            "content": [{"text": system_message, "type": "input_text"}],
            "type": "message",
        },
        {
            "role": "assistant",
            "content": [{"text": construct_welcome_message(), "type": "output_text"}],
            "type": "message",
        },
        {
            "role": "user",
            "content": [{"text": prompt, "type": "input_text"}],
            "type": "message",
        },
    ]
    st.session_state["system_message"] = system_message
    st.session_state["prompt_str"] = prompt


def suppress_streamlit_rendering():
    import arctic_analytics.llm.openai_responses as openai_responses

    openai_responses.render_tool_call = lambda *args, **kwargs: None
    openai_responses.render_tool_response = lambda *args, **kwargs: None


def validate_trace(trace):
    from jsonschema import Draft202012Validator, FormatChecker

    schema_path = ROOT / "schemas" / "analysis_trace.schema.json"
    schema = json.loads(schema_path.read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(trace)


def load_openai_api_key():
    if os.environ.get("OPENAI_API_KEY"):
        return

    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception as exc:
        raise SystemExit(
            "OPENAI_API_KEY must be set in the environment or in Streamlit secrets.toml."
        ) from exc

    os.environ["OPENAI_API_KEY"] = api_key


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the example analysis through the OpenAI Responses API and regenerate examples/sample_trace_export.json."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--session-id", default="tips-example-openai-api-session")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "examples" / "sample_dataset.csv",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=ROOT / "examples" / "sample_metadata.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "examples" / "sample_trace_export.json",
    )
    parser.add_argument("--skip-schema-validation", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    load_openai_api_key()

    from arctic_analytics.llm.openai_responses import OpenAIResponsesUtility
    from arctic_analytics.streamlit.helpers import build_analysis_trace

    suppress_streamlit_rendering()
    vetted_files = load_vetted_files(args.dataset, args.metadata)
    seed_session_state(args.session_id, args.model, args.prompt, vetted_files)

    client = OpenAIResponsesUtility()
    st.session_state["messages"] = client.generate_openai_response(vetted_files, args.model)
    st.session_state["prompt_str"] = args.prompt

    trace = build_analysis_trace()
    if not args.skip_schema_validation:
        validate_trace(trace)

    args.output.write_text(json.dumps(trace, indent=2, default=str) + "\n")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
