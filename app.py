import streamlit as st

from widgets.sidebar import render_reset, render_reset_chat, render_session_state
from widgets.home import setup_home, render_home

# App title
st.set_page_config(
    page_title="Data Analyst",
    layout="wide",
    initial_sidebar_state="expanded"
)

render_reset()
setup_home()
if st.session_state['datasets_vetted']:
    render_reset_chat()
render_home()
render_session_state()