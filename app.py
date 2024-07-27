import streamlit as st

from utils.streamlit_helpers import render_reset, render_reset_data_analyst, render_session_state, setup_session_state
from widgets.home import setup_home, render_home

# App title
st.set_page_config(
    page_title='Arctic Analytics',
    layout='wide',
    page_icon='❄️',
    initial_sidebar_state='auto'
)

if 'session_id' not in st.session_state.keys():
    st.session_state.update(setup_session_state())

render_reset()

st.header(':blue[Arctic Analytics]')
st.caption(':green[Answer questions about your data using Actic Analytics.]')

setup_home()
if st.session_state['datasets_vetted']:
    render_reset_data_analyst()
render_home()

if st.secrets['ENV'] == 'dev':
    render_session_state()