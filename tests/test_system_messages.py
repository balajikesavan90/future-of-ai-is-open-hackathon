import pandas as pd
import streamlit as st

from arctic_analytics.core.system_messages import construct_system_message


def test_construct_system_message_includes_dataframe_metadata():
    st.session_state["session_id"] = "test-session"
    vetted_files = {
        "sales": {
            "dataframe": pd.DataFrame({"region": ["east"], "revenue": [10]}),
            "dataset_description": "Sales by region.",
            "data_dictionary_json": '{"0":{"Column Name":"region","Data Type":"string"}}',
        }
    }

    message = construct_system_message(vetted_files)

    assert "Sales by region." in message
    assert "The dataset has already been loaded as a pandas DataFrame named sales" in message
