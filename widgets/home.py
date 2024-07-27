import streamlit as st

from widgets.sample_datasets import render_sample_datasets
from widgets.uploader import render_uploader
from widgets.snowflake_connection import render_snowflake_connection
from widgets.document_and_debug import render_document_and_debug_code_widget
from widgets.about import render_about
from widgets.data_dictionary import render_data_dictionary_widget
from widgets.uploaded_data import render_uploaded_data
from widgets.data_analyst import render_data_analyst


def setup_home():
    if 'vetted_files' not in st.session_state.keys():
        st.session_state['vetted_files'] = {}
    
    if 'data_dictionaries_loaded' not in st.session_state.keys():
        st.session_state['data_dictionaries_loaded'] = False    
    
    if 'datasets_vetted' not in st.session_state.keys():
        st.session_state['datasets_vetted'] = False

def render_home():
    if st.session_state['vetted_files'] == {}:

        analyze_data, document_debug_code, about = st.tabs(['🔍 Analyze Data', '🗂️ Document and 🐞 Debug Code', '🤖 About'])
        with analyze_data:
            render_sample_datasets()
            render_uploader()
            render_snowflake_connection()
        with document_debug_code:
            st.subheader(':blue[🗂️ Document and 🐞 Debug Code]')
            st.write(':blue[Document and debug your code using Actic Analytics.]')
            render_document_and_debug_code_widget()
        with about:
            render_about()

    else:
        if not st.session_state['data_dictionaries_loaded']:
            render_data_dictionary_widget()

        else:
            if not st.session_state['datasets_vetted']:
                render_uploaded_data()
            else:
                render_data_analyst()