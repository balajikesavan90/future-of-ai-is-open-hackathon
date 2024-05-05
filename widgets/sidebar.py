import streamlit as st

from utils.streamlit_helpers import reset_app, reset_chat


def render_reset():
    st.sidebar.button(':red[Reset]', on_click=reset_app)

def render_reset_chat():
    st.sidebar.button(':red[Reset Chat]', on_click=reset_chat, key='reset_chat_sidebar')

def render_session_state():
    st.sidebar.write(st.session_state)
