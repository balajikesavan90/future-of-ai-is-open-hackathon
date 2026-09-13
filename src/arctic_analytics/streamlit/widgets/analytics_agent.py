import streamlit as st
import logging
import time
import os

from arctic_analytics.config import DEFAULT_OPENAI_MODEL, MAX_MODEL_CONTEXT_TOKENS, has_openai_api_key
from arctic_analytics.llm.ai import construct_welcome_message, generate_ai_response
from arctic_analytics.core.system_messages import construct_system_message
from arctic_analytics.core.trace_resume import replace_resumed_system_message

from arctic_analytics.streamlit.widgets.prompt_guide import render_tool_calling_analysis_prompt_guide
from arctic_analytics.streamlit.helpers import render_ai_prompt, render_researcher_notes, safely_escape_dollars, render_tool_call, render_tool_response, select_sample_prompt
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

    st.session_state.setdefault('model', DEFAULT_OPENAI_MODEL)
    st.session_state.setdefault('agent_turn_state', 'idle')
    agent_turn_state = st.session_state['agent_turn_state']
    agent_turn_active = agent_turn_state != 'idle'

    st.caption(f"Uploaded data is analyzed through visible tool calls and constrained generated code. Review tool calls, generated code, and outputs before relying on the analysis. This analysis uses the {st.session_state['model']} model.")

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
    elif st.session_state.pop('rebuild_system_message', False):
        st.session_state['messages'] = replace_resumed_system_message(
            st.session_state['messages'], construct_system_message(st.session_state['vetted_files'])
        )

    st.session_state['system_message'] = st.session_state['messages'][0]['content'][0]['text']

    if 'cost' not in st.session_state:
        st.session_state['cost'] = 0
    
    if 'count' not in st.session_state:
        st.session_state['count'] = 0

    if 'show_sample' not in st.session_state:
        st.session_state['show_sample'] = True

    if 'context_window_usage' not in st.session_state:
        st.session_state['context_window_usage'] = 0
    if 'context_window_tokens' not in st.session_state:
        st.session_state['context_window_tokens'] = 0

    st.session_state['usage_container'] = st.empty()

    with st.session_state['usage_container']:
        st.sidebar.metric(
            label='Usage in this session',
            value=f'${st.session_state["cost"]}',
        )

    render_researcher_notes(disabled=agent_turn_active)
    render_ai_prompt()
    render_tool_calling_analysis_prompt_guide()

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
        for message_index, msg in enumerate(st.session_state['messages']):
            # The completed answer is rendered by ``write_stream`` below while
            # the turn is still locked. Avoid rendering it twice on that pass.
            if (
                agent_turn_state == 'streaming'
                and message_index == len(st.session_state['messages']) - 1
                and msg['type'] == 'message'
                and msg['role'] == 'assistant'
            ):
                continue
            if msg['type'] == 'message':
                if msg['role'] in ['user', 'assistant']:
                    text = msg['content'][0]['text']
                    st.chat_message(msg['role']).write(safely_escape_dollars(text))  # Safely escape dollar signs for LaTeX rendering
            elif msg['type'] == 'reasoning':
                if msg['summary'] != []:
                    summary_list = msg['summary']
                    with st.chat_message('assistant'):
                        for summary in summary_list:
                            with st.expander("🧠 Agent reasoning", expanded=True):
                                st.write(safely_escape_dollars(summary['text']))  # Safely escape dollar signs for LaTeX rendering
            elif msg['type'] == 'function_call':
                with st.chat_message('assistant'):
                    render_tool_call(msg)
            elif msg['type'] == 'function_call_output':
                with st.chat_message('assistant'):
                    display_output = msg.get('display_output', msg['output'])
                    if isinstance(display_output, str):
                        render_tool_response(display_output)
                    elif isinstance(display_output, list):
                        for output_item in display_output:
                            image_url = output_item.get('image_url') if isinstance(output_item, dict) else None
                            if isinstance(image_url, str):
                                render_tool_response(image_url)
                            else:
                                st.caption('Historical media output was omitted from the exported trace.')

    streaming_completed = False
    if agent_turn_state == 'streaming':
        # Render the live answer before the context-usage element so it has
        # the same visual order as the stable post-stream rerun.
        st.chat_message('assistant').write_stream(
            stream_text(safely_escape_dollars(st.session_state['messages'][-1]['content'][0]['text']))
        )
        streaming_completed = True

    st.session_state['spinner_container'] = st.container()

    context_window_tokens = st.session_state['context_window_tokens']
    context_window_usage = min(max(context_window_tokens / MAX_MODEL_CONTEXT_TOKENS, 0), 1)
    if context_window_tokens > 0:
        st.progress(
            value=context_window_usage,
            text=(
                f'Model context usage: {context_window_tokens:,} / '
                f'{MAX_MODEL_CONTEXT_TOKENS:,} tokens ({context_window_usage * 100:.2f}%)'
            ),
        )

    if context_window_usage > 0.5:
        st.warning(
            f'Context usage is above 50% of the {MAX_MODEL_CONTEXT_TOKENS:,}-token limit. '
            'Consider starting a new session.'
        )

    if not is_dev_environment():
        MAX_CHARS = 1000
    else:
        MAX_CHARS = None
    api_key_available = has_openai_api_key(secrets=st.secrets, environ=os.environ, session_state=st.session_state)
    if not api_key_available:
        st.warning("Configure `OPENAI_API_KEY` before running agent analysis.")
    user_input = st.chat_input(
        max_chars = MAX_CHARS, 
        disabled=(not api_key_available) or agent_turn_active,
        submit_mode='disable',
    )

    if st.session_state['show_sample']:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.button(
                label=':blue[Please find me something interesting in this data and plot it]',
                width='stretch',
                on_click=select_sample_prompt,
                args=('Find me something interesting in this data and plot it',),
                disabled=(not api_key_available) or agent_turn_active or (st.session_state['disable_sample_button'] if 'disable_sample_button' in st.session_state else False),
            )
        with col2:
            st.button(
                label=':blue[Please identify interesting patterns/correlations in the data and plot them]',
                width='stretch',
                on_click=select_sample_prompt,
                args=('Please identify interesting patterns/correlations in the data and plot them',),
                disabled=(not api_key_available) or agent_turn_active or (st.session_state['disable_sample_button'] if 'disable_sample_button' in st.session_state else False),
            )
        
    if agent_turn_state == 'idle':
        user_input = user_input or st.session_state.pop('pending_sample_prompt', None)
        if user_input is not None and user_input.strip():
            st.session_state['pending_agent_prompt'] = user_input
            st.session_state['agent_turn_state'] = 'queued'
            st.rerun()

    if agent_turn_state == 'queued':
        user_input = st.session_state.pop('pending_agent_prompt', None)
        if user_input is None:
            user_input = st.session_state.pop('pending_sample_prompt', None)
        if not isinstance(user_input, str) or not user_input.strip():
            st.session_state['agent_turn_state'] = 'idle'
            st.rerun()
        with st.spinner('Loading...'):
            st.session_state['messages'].append(
                {
                    'role': 'user', 
                    'content': [
                        {
                            'text': user_input,
                            'type': 'input_text'
                        },
                    ],
                    'type': 'message'
                }
            )
            with st.session_state['messages_container']:
                st.chat_message('user').write(safely_escape_dollars(user_input))  # Safely escape dollar signs for LaTeX rendering
            try:
                st.session_state['messages'] = generate_ai_response(st.session_state['vetted_files'], st.session_state['model'])
                st.session_state['count'] += 1
            except Exception:
                st.session_state['agent_turn_state'] = 'idle'
                raise
        st.session_state['agent_turn_state'] = 'streaming'
        st.rerun()

    if streaming_completed:
        st.session_state['agent_turn_state'] = 'idle'
        st.rerun()
