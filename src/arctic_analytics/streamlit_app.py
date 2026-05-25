"""Package-native Streamlit app entrypoint."""

import logging

import streamlit as st

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

    setup_home()
    if st.session_state["datasets_vetted"]:
        render_reset_analysis()
    render_home()

    if st.secrets["ENV"] == "dev":
        render_session_state()

    logging.info(f'############################### - {st.session_state["session_id"]}')


if __name__ == "__main__":
    main()
