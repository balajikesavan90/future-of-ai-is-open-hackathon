import streamlit as st

def reset():
    st.session_state = {}

def goto_data_dictionary_widget():
    st.session_state['data_dictionaries_loaded'] = False

def goto_data_analysis_widget():
    st.session_state['datasets_vetted'] = True