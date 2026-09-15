import streamlit as st
import logging

from python_data_analysis_agent.streamlit.widgets.sample_datasets import render_sample_datasets
from python_data_analysis_agent.streamlit.widgets.uploader import render_uploader
from python_data_analysis_agent.streamlit.widgets.about import render_about
from python_data_analysis_agent.streamlit.widgets.data_dictionary import render_data_dictionary_widget
from python_data_analysis_agent.streamlit.widgets.uploaded_data import render_uploaded_data
from python_data_analysis_agent.streamlit.widgets.analytics_agent import render_analytics_agent

def setup_home():
    logging.info(f'setup_home - {st.session_state["session_id"]}')
    if 'vetted_files' not in st.session_state.keys():
        st.session_state['vetted_files'] = {}
    
    if 'data_dictionaries_loaded' not in st.session_state.keys():
        st.session_state['data_dictionaries_loaded'] = False    
    
    if 'datasets_vetted' not in st.session_state.keys():
        st.session_state['datasets_vetted'] = False

def render_home():
    logging.info(f'render_home - {st.session_state["session_id"]}')
    if st.session_state['vetted_files'] == {}:

        analyze_data, about = st.tabs(['🔍 Analyze Data', '🗒️ About'])
        with analyze_data:
            render_sample_datasets()
            render_uploader()
        with about:
            render_about()

    else:
        if not st.session_state['data_dictionaries_loaded']:
            render_data_dictionary_widget()

        else:
            if not st.session_state['datasets_vetted']:
                render_uploaded_data()
            else:
                render_analytics_agent()
