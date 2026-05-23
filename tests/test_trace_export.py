import json

import pandas as pd
import streamlit as st

from arctic_analytics.streamlit.helpers import build_analysis_trace


def test_build_analysis_trace_is_json_safe_and_truncates_large_payloads():
    st.session_state.clear()
    long_text = "x" * 12000
    image_payload = "data:image/png;base64," + ("a" * 12000)

    st.session_state["session_id"] = "trace-test-session"
    st.session_state["model"] = "gpt-test"
    st.session_state["agent_model"] = True
    st.session_state["cost"] = 0.123
    st.session_state["system_message"] = long_text
    st.session_state["prompt_str"] = long_text
    st.session_state["messages"] = [
        {
            "type": "function_call",
            "name": "generate_plot",
            "arguments": json.dumps({"function_definition": "def generate_plot(): pass"}),
        },
        {
            "type": "function_call_output",
            "output": image_payload,
        },
        {
            "role": "assistant",
            "output": pd.DataFrame(
                {
                    "count": [1, 2],
                    "created_at": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                }
            ),
        },
        {
            "role": "assistant",
            "error": True,
            "content": "example error",
        },
    ]
    st.session_state["vetted_files"] = {
        "sales": {
            "dataset_description": "Sales data.",
            "columns_names": pd.Index(["count", "created_at"]),
            "data_types": pd.Series({"count": "Int64", "created_at": "datetime64[ns]"}),
            "primary_key": [],
            "data_dictionary_json": '{"0":{"Column Name":"count","Data Type":"Int64"}}',
            "dataframe": pd.DataFrame({"count": [1, 2]}),
        }
    }

    trace = build_analysis_trace()
    dumped = json.dumps(trace)

    assert dumped
    assert trace["system_message"]["truncated"] is True
    assert trace["system_message"]["length_chars"] == 12000
    assert trace["prompt_str"]["truncated"] is True
    assert trace["outputs"][0]["output"]["type"] == "image_base64"
    assert trace["outputs"][0]["output"]["payload_length_chars"] == 12000
    assert trace["outputs"][1]["output"]["data"][0]["count"] == 1
    assert isinstance(trace["outputs"][1]["output"]["data"][0]["count"], int)
    assert trace["outputs"][1]["output"]["data"][0]["created_at"].startswith("2026-01-01")
    assert trace["dataset_metadata"]["sales"]["column_names"] == ["count", "created_at"]
    assert trace["dataset_metadata"]["sales"]["columns_names"] == ["count", "created_at"]
    assert trace["errors"][0]["content"] == "example error"
