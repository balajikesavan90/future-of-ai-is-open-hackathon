import streamlit as st
import uuid
import logging

def setup_session_state():
    logging.info(f'###############################')
    logging.info(f'setup_session_state')
    logging.info(f'###############################')
    session_page = {}
    session_page['session_id'] = str(uuid.uuid4())
    return session_page

def reset_app():
    logging.info(f'reset_app - {st.session_state["session_id"]}')
    # Clear all keys in st.session_state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    # Re-initialize session_id
    st.session_state['session_id'] = str(uuid.uuid4())
    print('###############################')
    print('reset_app')
    print('###############################')

def goto_data_dictionary_widget():
    logging.info(f'goto_data_dictionary_widget - {st.session_state["session_id"]}')
    st.session_state['data_dictionaries_loaded'] = False

def goto_data_analysis_widget():
    logging.info(f'goto_data_analysis_widget - {st.session_state["session_id"]}')
    st.session_state['datasets_vetted'] = True
    if 'uploaded_files' in st.session_state.keys():
        del st.session_state['uploaded_files']

def reset_data_analyst():
    logging.info(f'reset_data_analyst - {st.session_state["session_id"]}')
    st.session_state['messages'] = []
    st.session_state['count'] = 0
    st.session_state['session_id'] = str(uuid.uuid4())
    print('###############################')
    print('reset_data_analyst')
    print('###############################')

def render_reset():
    logging.info(f'render_reset - {st.session_state["session_id"]}')
    st.sidebar.button(':red[Reset App]', on_click=reset_app)

def render_reset_data_analyst():
    logging.info(f'render_reset_data_analyst - {st.session_state["session_id"]}')
    st.sidebar.button(':red[Reset Data Analyst]', on_click=reset_data_analyst, key='reset_chat_sidebar')

def reset_analytics_agent():
    logging.info(f'reset_analytics_agent - {st.session_state["session_id"]}')
    st.session_state['messages'] = []
    st.session_state['count'] = 0
    st.session_state['session_id'] = str(uuid.uuid4())
    print('###############################')
    print('reset_analytics_agent')
    print('###############################')

def render_reset_analytics_agent():
    logging.info(f'render_reset_analytics_agent - {st.session_state["session_id"]}')
    st.sidebar.button(':red[Reset Analytics Agent]', on_click=reset_analytics_agent, key='reset_agent_sidebar')

def render_session_state():
    logging.info(f'render_session_state - {st.session_state["session_id"]}')
    st.sidebar.write(st.session_state)

def render_ai_prompt():
    logging.info(f'render_ai_prompt - {st.session_state["session_id"]}')
    with st.sidebar.expander('What does the AI see?', expanded=True):
        if 'system_message' in st.session_state.keys():
            st.subheader(':blue[System Message]')
            st.write(st.session_state['system_message'])
        if 'messages' in st.session_state.keys():
            st.subheader(':blue[Messages]')
            messages_wo_system_message = [msg for msg in st.session_state['messages'] if msg['role'] != 'system']
            st.write(messages_wo_system_message)