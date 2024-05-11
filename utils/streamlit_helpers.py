import streamlit as st

def reset_app():
    st.session_state = {}

def goto_data_dictionary_widget():
    st.session_state['data_dictionaries_loaded'] = False

def goto_data_analysis_widget():
    st.session_state['datasets_vetted'] = True
    del st.session_state['uploaded_files']

def reset_chat():
    st.session_state['messages'] = []
    st.session_state['count'] = 0

def render_reset():
    st.sidebar.button(':red[Reset]', on_click=reset_app)

def render_reset_chat():
    st.sidebar.button(':red[Reset Chat]', on_click=reset_chat, key='reset_chat_sidebar')

def render_session_state():
    st.sidebar.write(st.session_state)
