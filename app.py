import streamlit as st

from widgets.sidebar import render_sidebar
from widgets.home import render_home

# App title
st.set_page_config(page_title="Data Analyst")

render_home()
render_sidebar()
