"""Package-native Streamlit app entrypoint."""

import logging
import os

import streamlit as st

from arctic_analytics.config import get_config_value, has_openai_api_key
from arctic_analytics.streamlit.helpers import (
    render_reset,
    render_reset_analysis,
    render_session_state,
    setup_session_state,
)
from arctic_analytics.streamlit.widgets.home import render_home, setup_home


def main():
    st.set_page_config(
        page_title="Arctic Analytics",
        layout="wide",
        page_icon="❄️",
        initial_sidebar_state="auto",
    )

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    if "session_id" not in st.session_state.keys():
        st.session_state.update(setup_session_state())

    render_reset()

    st.header(":blue[Arctic Analytics]")
    render_api_key_setup_notice()

    setup_home()
    if st.session_state["datasets_vetted"]:
        render_reset_analysis()
    render_home()

    if get_config_value("ENV", secrets=st.secrets, environ=os.environ, default="") == "dev":
        render_session_state()

    logging.info(f'############################### - {st.session_state["session_id"]}')


def render_api_key_setup_notice():
    if has_openai_api_key(secrets=st.secrets, environ=os.environ):
        return

    st.sidebar.warning("OpenAI API key not configured.")
    st.sidebar.caption(
        "Set OPENAI_API_KEY in your shell or copy `.streamlit/secrets.example.toml` "
        "to `.streamlit/secrets.toml` before running agent analysis."
    )
    with st.expander("Set up local API access", expanded=False):
        st.write(
            "You can still load sample data and review metadata, but agent analysis "
            "requires an OpenAI API key."
        )
        st.code("export OPENAI_API_KEY='your-key-here'\npoetry run arctic-analytics-app", language="bash")
        st.code(
            "cp .streamlit/secrets.example.toml .streamlit/secrets.toml\n"
            "# then edit .streamlit/secrets.toml",
            language="bash",
        )


if __name__ == "__main__":
    main()
