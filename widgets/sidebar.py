import streamlit as st

from utils.streamlit_helpers import reset


def render_reset():
    st.sidebar.button(':red[Reset]', on_click=reset)

def render_session_state():
    st.sidebar.write(st.session_state)
