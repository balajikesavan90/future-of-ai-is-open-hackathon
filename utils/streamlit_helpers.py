import streamlit as st

def reset_app():
    st.session_state = {}
    print('###############################')
    print('reset_app')
    print('###############################')

def goto_data_dictionary_widget():
    st.session_state['data_dictionaries_loaded'] = False

def goto_data_analysis_widget():
    st.session_state['datasets_vetted'] = True
    del st.session_state['uploaded_files']

def reset_data_analyst():
    st.session_state['messages'] = []
    st.session_state['count'] = 0
    print('###############################')
    print('reset_data_analyst')
    print('###############################')

def reset_chart_builder():
    st.session_state['messages'] = []
    st.session_state['count'] = 0
    print('###############################')
    print('reset_chart_builder')
    print('###############################')

def render_reset():
    st.sidebar.button(':red[Reset App]', on_click=reset_app)

def render_reset_data_analyst():
    st.sidebar.button(':red[Reset Data Analyst]', on_click=reset_data_analyst, key='reset_chat_sidebar')

def render_reset_chart_builder():
    st.sidebar.button(':red[Reset Chart Builder]', on_click=reset_chart_builder, key='reset_chart_builder_sidebar')

def render_session_state():
    st.sidebar.write(st.session_state)
