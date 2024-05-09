import streamlit as st

from widgets.snowflake_connection import render_snowflake_connection
from widgets.uploader import render_uploader
from widgets.data_dictionary import render_data_dictionary_widget
from widgets.uploaded_data import render_uploaded_data
from widgets.chat import render_chat
from widgets.create_documentation import render_create_documentation


def setup_home():
    if 'vetted_files' not in st.session_state.keys():
        st.session_state['vetted_files'] = {}
    
    if 'data_dictionaries_loaded' not in st.session_state.keys():
        st.session_state['data_dictionaries_loaded'] = False    
    
    if 'datasets_vetted' not in st.session_state.keys():
        st.session_state['datasets_vetted'] = False

def render_home():
    if st.session_state['vetted_files'] == {}:

        analyze_data, create_documentation, about = st.tabs(['Analyze Data', 'Create Documentation', 'About'])
        with analyze_data:
            render_snowflake_connection()
            render_uploader()
        with create_documentation:
            render_create_documentation()
        with about:
            st.write('About')

    else:
        if not st.session_state['data_dictionaries_loaded']:
            render_data_dictionary_widget()

        else:
            if not st.session_state['datasets_vetted']:
                render_uploaded_data()
            else:
                render_chat()