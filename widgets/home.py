import streamlit as st
import logging

from widgets.sample_datasets import render_sample_datasets
from widgets.uploader import render_uploader
# from widgets.snowflake_connection import render_snowflake_connection
from widgets.about import render_about
from widgets.data_dictionary import render_data_dictionary_widget
from widgets.uploaded_data import render_uploaded_data
from widgets.data_analyst import render_data_analyst
from widgets.analytics_agent import render_analytics_agent

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
            st.session_state['agent_model'] = st.toggle(
                label=':blue[Use Agent Model]',
                value=True,
                help='Use the agent model to analyze your data. This will allow the AI to see your data.',
            )
            render_sample_datasets()
            render_uploader()
            # render_snowflake_connection()
        with about:
            render_about()

    else:
        if not st.session_state['data_dictionaries_loaded']:
            render_data_dictionary_widget()

        else:
            if not st.session_state['datasets_vetted']:
                render_uploaded_data()
            else:
                if st.session_state['agent_model']:
                    render_analytics_agent()
                else:
                    render_data_analyst()