import streamlit as st

from utils.data_analysis_helpers import gather_metadata

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