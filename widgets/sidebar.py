import streamlit as st

from utils.streamlit_helpers import reset


def render_sidebar():
    st.sidebar.write(st.session_state)
    st.sidebar.button('Reset', on_click=reset)
