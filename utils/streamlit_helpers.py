import streamlit as st
import uuid
import logging
import json
import pandas as pd  # Add import for pandas
import matplotlib.figure as mfigure  # Add import for matplotlib.figure

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
    st.session_state['cost'] = 0
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
    st.session_state['cost'] = 0
    st.session_state['show_sample'] = True
    st.session_state['disable_sample_button'] = False
    st.session_state['context_window_usage'] = 0
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

def disable_sample_button():
    st.session_state['disable_sample_button'] = True

def render_ai_prompt():
    logging.info(f'render_ai_prompt - {st.session_state["session_id"]}')
    with st.sidebar.expander('What does the AI see?', expanded=True):
        if 'system_message' in st.session_state.keys():
            st.subheader(':blue[System Message]')
            st.write(st.session_state['system_message'])
        if 'messages' in st.session_state.keys():
            st.subheader(':blue[Messages]')
            messages_wo_system_message = st.session_state['messages'][1:]
            st.write(messages_wo_system_message)

def safely_escape_dollars(text):
    """
    Escapes dollar signs in text only if they don't appear to be already escaped.
    """
    if not text:
        return text
    if '\\$' in text:  # Check for already escaped dollars
        return text
    else:
        return text.replace('$', '\\$')

def try_convert_to_dataframe(data):
    """Helper function to attempt converting various data types to DataFrames"""
    try:
        if isinstance(data, dict):
            return pd.DataFrame.from_dict(data, orient='index')
        elif isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
            return pd.DataFrame(data)
        return None
    except Exception:
        return None

def render_tool_call(tool_call):
    """
    Renders a tool call in the Streamlit UI
    
    Args:
        tool_call: The tool call to render
    """
    if not isinstance(tool_call, dict):
        logging.warning(f'Unexpected tool call shape: {tool_call}')
        tool_call = {}

    function = tool_call.get('function', {})
    tool_name = tool_call.get('name') or function.get('name') or 'unknown'
    raw_arguments = tool_call.get('arguments') or function.get('arguments') or '{}'

    if isinstance(raw_arguments, dict):
        arguments = raw_arguments
    else:
        try:
            arguments = json.loads(raw_arguments)
        except (TypeError, json.JSONDecodeError):
            logging.warning(f'Unable to parse tool call arguments for {tool_name}: {raw_arguments}')
            arguments = {}

    if 'reason' in arguments:
        st.caption(f"Reason: {safely_escape_dollars(str(arguments['reason']))}")
    with st.expander(f"🛠️ See Tool Call - Tool Name: {tool_name}", expanded=False):
        if 'python_expression' in arguments:
            st.code(arguments['python_expression'], language='python')
        if 'function_definition' in arguments:
            st.code(arguments['function_definition'], language='python')
        if not arguments:
            st.code(str(raw_arguments), language='json')

def render_tool_response(tool_response):
    """
    Renders a tool response in the Streamlit UI
    
    Args:
        tool_response: The tool response to render
    """
    if tool_response.startswith('data:image/png;base64,'):
        with st.expander('🛠️ See Tool Response - Plot', expanded=True):
            st.image(tool_response)
    
    else:
        with st.expander('🛠️ See Tool Response', expanded=False):
            try:
                # Try parsing the response
                data = json.loads(tool_response)
                
                # Handle double-encoded JSON
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        pass
                
                # Try converting to DataFrame
                df = try_convert_to_dataframe(data)
                
                if df is not None:
                    st.dataframe(df, width='stretch')
                else:
                    st.write(data)
                    
            except json.JSONDecodeError:
                # Not JSON, display as plain text
                st.write(tool_response)
