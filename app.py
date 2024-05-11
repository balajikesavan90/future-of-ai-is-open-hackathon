import streamlit as st

from utils.streamlit_helpers import render_reset, render_reset_chat, render_session_state
from widgets.home import setup_home, render_home

# App title
st.set_page_config(
    page_title='Arctic Analytics',
    layout='wide',
    page_icon='❄️',
    initial_sidebar_state='expanded'
)

# st.sidebar.write(st.session_state)

render_reset()

st.header(':blue[Arctic Analytics]')


setup_home()
if st.session_state['datasets_vetted']:
    render_reset_chat()
render_home()

if st.secrets['env'] == 'dev':
    render_session_state()