"""Package-native Streamlit app entrypoint."""

import logging
import os

import streamlit as st

from arctic_analytics.config import (
    get_config_value,
    get_openai_api_key,
    has_openai_api_key,
    save_openai_api_key_to_env,
)
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

    st.header(":blue[Arctic Analytics]")

    render_reset()
    render_api_key_setup_notice()

    if not has_openai_api_key(secrets=st.secrets, environ=os.environ, session_state=st.session_state):
        render_api_key_setup_screen()

    setup_home()
    if st.session_state["datasets_vetted"]:
        render_reset_analysis()
    render_home()

    if get_config_value("ENV", secrets=st.secrets, environ=os.environ, default="") == "dev":
        render_session_state()

    logging.info(f'############################### - {st.session_state["session_id"]}')


def render_api_key_setup_screen():
    st.subheader("Set up OpenAI API key")
    st.write("Live AI-assisted analysis requires an OpenAI API key.")
    st.caption(
        "Your API key is stored locally on this machine if you choose to save it. "
        "It is not committed to Git and is not included in exported research bundles."
    )

    with st.form("openai_api_key_setup"):
        api_key = st.text_input("OpenAI API key", type="password")
        save_key = st.checkbox("Save this key locally in .env", value=True)
        submitted = st.form_submit_button("Use OpenAI API key")

    if submitted:
        cleaned_key = api_key.strip()
        if not cleaned_key:
            st.error("Enter an OpenAI API key to continue.")
            return

        st.session_state["OPENAI_API_KEY"] = cleaned_key
        os.environ["OPENAI_API_KEY"] = cleaned_key
        if save_key:
            save_openai_api_key_to_env(cleaned_key)
            st.success("Saved OpenAI API key to local .env.")
        else:
            st.success("OpenAI API key will be used for this Streamlit session.")
        st.rerun()

    st.caption("No API key yet? You can still inspect the checked-in sample research bundle from the README.")


def render_api_key_setup_notice():
    api_key = get_openai_api_key(secrets=st.secrets, environ=os.environ, session_state=st.session_state)
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        return

    st.sidebar.warning("OpenAI API key not configured.")
    st.sidebar.caption(
        "Set OPENAI_API_KEY in your shell or copy `.streamlit/secrets.example.toml` "
        "to `.streamlit/secrets.toml` before running agent analysis."
    )
    with st.sidebar.expander("Set up local API access", expanded=False):
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
