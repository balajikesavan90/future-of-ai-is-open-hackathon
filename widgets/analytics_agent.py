import streamlit as st
import logging
import uuid
import time
import json
import pandas as pd

from utils.ai_helpers import construct_welcome_message, generate_ai_response

from widgets.prompt_guide import render_analytics_agent_prompt_guide
from utils.streamlit_helpers import render_ai_prompt


def stream_text(text):
    for paragraph in text.split('\n'):
        for word in paragraph.split():
            yield word + " "
            time.sleep(0.05)
        yield "\n"
        
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
            
def render_analytics_agent():
    logging.info(f'render_analytics_agent - {st.session_state["session_id"]}')
    st.divider()
    st.caption(':green[Arctic Analytics AI now has access to files you uploaded. Arctic Analytics will run code to analyze your data and generate insights.]')
    st.session_state['model'] = 'gpt-4.1-nano-2025-04-14'
    st.caption(f':blue[The analytics agent uses the {st.session_state["model"]} model.]')

    render_analytics_agent_prompt_guide()
    render_ai_prompt()

    if 'messages' not in st.session_state.keys() or not st.session_state['messages']:
        st.session_state['messages'] = [{'role': 'assistant', 'content': construct_welcome_message()}]

    if 'cost' not in st.session_state:
        st.session_state['cost'] = 0
    
    if 'count' not in st.session_state:
        st.session_state['count'] = 0

    with st.expander('See uploaded Datasets'):
        for filename in st.session_state['vetted_files']:
            st.subheader(f':blue[{filename}]')
            data_filter = st.selectbox(
                label='Select the number of rows to display',
                options=['First 5 rows', 'Last 5 rows', 'Random 5 rows'],
                key=f'{filename}_data_filter',
            )
            if data_filter == 'First 5 rows':
                st.dataframe(st.session_state['vetted_files'][filename]['dataframe'].head(), use_container_width=True)
            elif data_filter == 'Last 5 rows':
                st.dataframe(st.session_state['vetted_files'][filename]['dataframe'].tail(), use_container_width=True)
            elif data_filter == 'Random 5 rows':
                st.dataframe(st.session_state['vetted_files'][filename]['dataframe'].sample(5), use_container_width=True)

    for msg in st.session_state['messages']:
        if msg['role'] in ['user', 'assistant']:
            if 'content' in msg and msg['content'] != None:
                st.chat_message(msg['role']).write(msg['content'].replace('$', '\$'))
            if 'tool_calls' in msg:
                for tool_call in msg['tool_calls']:
                    with st.expander('🛠️ See Tool Call', expanded=False):
                        st.code(json.loads(tool_call['function']['arguments'])['code_snippet'])
        if msg['role'] == 'tool':
            with st.expander('🛠️ See Tool Response', expanded=False):
                tool_response = msg['content']

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
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.write(data)
                        
                except json.JSONDecodeError:
                    # Not JSON, display as plain text
                    st.write(tool_response)

    

    st.session_state['spinner_container'] = st.container()

    st.session_state['user_input'] = st.chat_input(
        max_chars = 1000, 
    )

    if st.session_state['user_input'] is not None and st.session_state['user_input'].strip():
        st.chat_message('user').write(st.session_state['user_input'])
        with st.spinner('Loading...'):
            st.session_state['messages'].append({'role': 'user', 'content': st.session_state['user_input']})
            st.session_state['messages'] = generate_ai_response(st.session_state['vetted_files'], st.session_state['model'], True)
            st.session_state['count'] += 1
        st.chat_message('assistant').write_stream(stream_text(st.session_state['messages'][-1]['content']))
        st.rerun()