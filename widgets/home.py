import streamlit as st

from widgets.snowflake_connection import render_snowflake_connection
from widgets.uploader import render_uploader
from widgets.sample_datasets import render_sample_datasets
from widgets.data_dictionary import render_data_dictionary_widget
from widgets.uploaded_data import render_uploaded_data
from widgets.data_analyst import render_data_analyst
from widgets.document_and_debug import render_document_and_debug_code_widget
from widgets.chart_builder import render_chart_builder



def setup_home():
    if 'vetted_files' not in st.session_state.keys():
        st.session_state['vetted_files'] = {}
    
    if 'data_dictionaries_loaded' not in st.session_state.keys():
        st.session_state['data_dictionaries_loaded'] = False    
    
    if 'datasets_vetted' not in st.session_state.keys():
        st.session_state['datasets_vetted'] = False

def render_home():
    if st.session_state['vetted_files'] == {}:

        analyze_data, build_charts, document_debug_code, about = st.tabs(['🔍 Analyze Data', '📊 Build Charts', '🐞 Document & Debug Code', '🤖 About'])
        with analyze_data:
            st.subheader('🔍 :blue[Data Analyst]')
            st.write(':blue[Answer questions about your data using Actic Analytics.]')
            render_sample_datasets(page = 'data_analyst')
            render_uploader(page = 'data_analyst')
            render_snowflake_connection(page = 'data_analyst')
        with build_charts:
            st.subheader('📊 :blue[Chart Builder]')
            st.write(':blue[Create charts from your data using Actic Analytics.]')
            render_sample_datasets(page = 'chart_builder')
            render_uploader(page = 'chart_builder')
            render_snowflake_connection(page = 'chart_builder')
        with document_debug_code:
            st.subheader('🐞 :blue[Document & Debug Code]')
            st.write(':blue[Document and debug your code using Actic Analytics.]')
            render_document_and_debug_code_widget()
        with about:
            st.write('About')

    else:
        if not st.session_state['data_dictionaries_loaded']:
            render_data_dictionary_widget()

        else:
            if not st.session_state['datasets_vetted']:
                render_uploaded_data(st.session_state['active_page'])
            else:
                if st.session_state['active_page'] == 'data_analyst':
                    render_data_analyst()
                elif st.session_state['active_page'] == 'chart_builder':
                    render_chart_builder()