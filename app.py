import streamlit as st

from widgets.sidebar import render_reset, render_session_state
from widgets.home import setup_home, render_home

# App title
st.set_page_config(page_title="Data Analyst")

render_reset()
setup_home()
render_home()
render_session_state()
