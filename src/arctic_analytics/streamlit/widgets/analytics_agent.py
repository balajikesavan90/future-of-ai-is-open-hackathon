import streamlit as st
import logging
import time
import os

from arctic_analytics.config import get_openai_api_key, has_openai_api_key
from arctic_analytics.llm.ai import construct_welcome_message, generate_ai_response
from arctic_analytics.core.system_messages import construct_system_message

from arctic_analytics.streamlit.widgets.prompt_guide import render_tool_calling_analysis_prompt_guide
from arctic_analytics.streamlit.helpers import render_ai_prompt, render_researcher_notes, safely_escape_dollars, render_tool_call, render_tool_response, disable_sample_button
from arctic_analytics.streamlit.helpers import is_dev_environment


def stream_text(text):
    for paragraph in text.split('\n'):
        for word in paragraph.split():
            yield word + " "
            time.sleep(0.05)
        yield "\n"
        
            
def render_analytics_agent():
    logging.info(f'render_analytics_agent - {st.session_state["session_id"]}')
    st.divider()
    st.info('Uploaded data is analyzed through visible tool calls and constrained generated code.')

    if not is_dev_environment():
        st.session_state['model'] = 'gpt-5.4-mini-2026-03-17'
    else:
        st.session_state['model'] = st.sidebar.selectbox(
            label = 'Model',
            options = ['gpt-5.4-nano-2026-03-17', 'gpt-5.4-mini-2026-03-17', 'gpt-5.4-2026-03-05', 'gpt-5.5-2026-04-23'],
            index = 0,
            key='model_select_sidebar',
        )

    st.info(f'This analysis uses the {st.session_state["model"]} model. Review tool calls, generated code, and outputs before relying on the analysis.')

    if 'messages' not in st.session_state.keys() or not st.session_state['messages']:
        system_message = construct_system_message(st.session_state['vetted_files'])
        st.session_state['messages'] = [
            {
                'role': 'system', 
                'content': [
                    {
                        'text': system_message, 
                        'type': 'input_text'
                    }
                ], 
                'type': 'message'
            },
            {
                'role': 'assistant', 
                'content': [
                    {
                        'text': construct_welcome_message(),
                        'type': 'output_text'
                    }
                ],
                'type': 'message'
            }
        ]

    st.session_state['system_message'] = st.session_state['messages'][0]['content'][0]['text']

    if 'cost' not in st.session_state:
        st.session_state['cost'] = 0
    
    if 'count' not in st.session_state:
        st.session_state['count'] = 0

    if 'show_sample' not in st.session_state:
        st.session_state['show_sample'] = True

    if 'context_window_usage' not in st.session_state:
        st.session_state['context_window_usage'] = 0

    st.session_state['usage_container'] = st.empty()

    with st.session_state['usage_container']:
        st.sidebar.metric(
            label='Usage in this session',
            value=f'${st.session_state["cost"]}',
        )

    render_researcher_notes()
    render_tool_calling_analysis_prompt_guide()
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
                st.dataframe(st.session_state['vetted_files'][filename]['dataframe'].head(), width='stretch')
            elif data_filter == 'Last 5 rows':
                st.dataframe(st.session_state['vetted_files'][filename]['dataframe'].tail(), width='stretch')
            elif data_filter == 'Random 5 rows':
                st.dataframe(st.session_state['vetted_files'][filename]['dataframe'].sample(5), width='stretch')

    st.session_state['messages_container'] = st.container()

    with st.session_state['messages_container']:
        for msg in st.session_state['messages']:
            if msg['type'] == 'message':
                if msg['role'] in ['user', 'assistant']:
                    text = msg['content'][0]['text']
                    st.chat_message(msg['role']).write(safely_escape_dollars(text))  # Safely escape dollar signs for LaTeX rendering
            elif msg['type'] == 'reasoning':
                if msg['summary'] != []:
                    summary_list = msg['summary']
                    for summary in summary_list:
                        with st.expander("Reasoning", expanded=True):
                            st.write(safely_escape_dollars(summary['text']))  # Safely escape dollar signs for LaTeX rendering
            elif msg['type'] == 'function_call':
                render_tool_call(msg)
            elif msg['type'] == 'function_call_output':
                if isinstance(msg['output'], str):
                    render_tool_response(msg['output'])
                elif isinstance(msg['output'], list):
                    for output_item in msg['output']:
                        render_tool_response(output_item['image_url'])

    st.session_state['spinner_container'] = st.container()

    if st.session_state['context_window_usage'] > 0:
        st.progress(
            value=st.session_state['context_window_usage'],
            text=f'Model Context Usage: {st.session_state["context_window_usage"]*100:.2f}%'
        )

    if st.session_state['context_window_usage'] > 0.5:
        st.warning('LLMs are known to degrade in performance when context window usage gets higher than 50%. Consider starting a new session.')

    if not is_dev_environment():
        MAX_CHARS = 1000
    else:
        MAX_CHARS = None
    api_key = get_openai_api_key(secrets=st.secrets, environ=os.environ, session_state=st.session_state)
    if api_key:
        os.environ.setdefault("OPENAI_API_KEY", api_key)
    api_key_available = has_openai_api_key(secrets=st.secrets, environ=os.environ, session_state=st.session_state)
    if not api_key_available:
        st.warning("Configure `OPENAI_API_KEY` before running agent analysis.")
    st.session_state['user_input'] = st.chat_input(
        max_chars = MAX_CHARS, 
        disabled=not api_key_available,
    )

    if st.session_state['show_sample']:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(
                label=':blue[Please find me something interesting in this data and plot it]',
                width='stretch',
                on_click=disable_sample_button,
                disabled=(not api_key_available) or (st.session_state['disable_sample_button'] if 'disable_sample_button' in st.session_state else False),
            ):
                st.session_state['user_input'] = 'Find me something interesting in this data and plot it'
                st.session_state['show_sample'] = False
        with col2:
            if st.button(
                label=':blue[Please identify interesting patterns/correlations in the data and plot them]',
                width='stretch',
                on_click=disable_sample_button,
                disabled=(not api_key_available) or (st.session_state['disable_sample_button'] if 'disable_sample_button' in st.session_state else False),
            ):
                st.session_state['user_input'] = 'Please identify interesting patterns/correlations in the data and plot them'
                st.session_state['show_sample'] = False
        

    if st.session_state['user_input'] is not None and st.session_state['user_input'].strip():
        with st.spinner('Loading...'):
            st.session_state['messages'].append(
                {
                    'role': 'user', 
                    'content': [
                        {
                            'text': st.session_state['user_input'],
                            'type': 'input_text'
                        },
                    ],
                    'type': 'message'
                }
            )
            with st.session_state['messages_container']:
                st.chat_message('user').write(safely_escape_dollars(st.session_state['user_input']))  # Safely escape dollar signs for LaTeX rendering
            st.session_state['messages'] = generate_ai_response(st.session_state['vetted_files'], st.session_state['model'])
            st.session_state['count'] += 1
        st.chat_message('assistant').write_stream(stream_text(safely_escape_dollars(st.session_state['messages'][-1]['content'][0]['text'])))  # Safely escape dollar signs for LaTeX rendering
        st.rerun()
