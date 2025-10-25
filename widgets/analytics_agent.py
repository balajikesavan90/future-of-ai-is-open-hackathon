import streamlit as st
import logging
import uuid
import time
import json
import pandas as pd

from utils.ai_helpers import construct_welcome_message, generate_ai_response

from widgets.prompt_guide import render_analytics_agent_prompt_guide
from utils.streamlit_helpers import render_ai_prompt, safely_escape_dollars, render_tool_call, render_tool_response, disable_sample_button


def stream_text(text):
    for paragraph in text.split('\n'):
        for word in paragraph.split():
            yield word + " "
            time.sleep(0.05)
        yield "\n"
        
            
def render_analytics_agent():
    logging.info(f'render_analytics_agent - {st.session_state["session_id"]}')
    st.divider()
    st.info('Arctic Analytics AI now has access to files you uploaded. Arctic Analytics will run code to analyze your data and generate insights.')

    if st.secrets['ENV'] == 'dev':
        st.session_state['model'] = st.sidebar.selectbox(
            label = 'Model',
            options = ['gpt-5-nano-2025-08-07', 'gpt-5-mini-2025-08-07', 'gpt-5-2025-08-07'],
            index = 0,
            key='model_select_sidebar',
        )
    else:
        st.session_state['model'] = 'gpt-5-nano-2025-08-07'

    st.info(f'The analytics agent uses the {st.session_state["model"]} model. Agent mode works much better with advanced models like gpt-5-mini or gpt-5. Please get in touch with [me](https://www.linkedin.com/in/balaji-kesavan/) if you want to use the advanced models.')

    if 'messages' not in st.session_state.keys() or not st.session_state['messages']:
        st.session_state['messages'] = [{'role': 'assistant', 'content': construct_welcome_message()}]

    if 'cost' not in st.session_state:
        st.session_state['cost'] = 0
    
    if 'count' not in st.session_state:
        st.session_state['count'] = 0

    if 'show_sample' not in st.session_state:
        st.session_state['show_sample'] = True

    st.session_state['usage_container'] = st.empty()

    with st.session_state['usage_container']:
        st.sidebar.metric(
            label='Usage in this session',
            value=f'${st.session_state["cost"]}',
        )

    render_analytics_agent_prompt_guide()
    render_ai_prompt()

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

    st.session_state['messages_container'] = st.container()

    with st.session_state['messages_container']:
        for msg in st.session_state['messages']:
            if msg['role'] in ['user', 'assistant']:
                if 'content' in msg and msg['content'] != None:
                    st.chat_message(msg['role']).write(safely_escape_dollars(msg['content']))  # Safely escape dollar signs for LaTeX rendering
                if 'tool_calls' in msg:
                    for tool_call in msg['tool_calls']:
                        render_tool_call(tool_call)
            if msg['role'] == 'tool':
                render_tool_response(msg['content'])

    

    st.session_state['spinner_container'] = st.container()

    st.session_state['user_input'] = st.chat_input(
        max_chars = 1000, 
    )

    if st.session_state['show_sample']:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(
                label=':blue[Please find me something interesting in this data and plot it]',
                use_container_width=True,
                on_click=disable_sample_button,
                disabled=st.session_state['disable_sample_button'] if 'disable_sample_button' in st.session_state else False,
            ):
                st.session_state['user_input'] = 'Find me something interesting in this data and plot it'
                st.session_state['show_sample'] = False
        with col2:
            if st.button(
                label=':blue[Please identify interesting patterns and/or correlations in the data and plot them]',
                use_container_width=True,
                on_click=disable_sample_button,
                disabled=st.session_state['disable_sample_button'] if 'disable_sample_button' in st.session_state else False,
            ):
                st.session_state['user_input'] = 'Please identify interesting patterns and/or correlations in the data and plot them'
                st.session_state['show_sample'] = False
        

    if st.session_state['user_input'] is not None and st.session_state['user_input'].strip():
        with st.spinner('Loading...'):
            st.session_state['messages'].append({'role': 'user', 'content': st.session_state['user_input']})
            with st.session_state['messages_container']:
                st.chat_message('user').write(safely_escape_dollars(st.session_state['user_input']))  # Safely escape dollar signs for LaTeX rendering
            st.session_state['messages'] = generate_ai_response(st.session_state['vetted_files'], st.session_state['model'], True)
            st.session_state['count'] += 1
        st.chat_message('assistant').write_stream(stream_text(safely_escape_dollars(st.session_state['messages'][-1]['content'])))
        st.rerun()