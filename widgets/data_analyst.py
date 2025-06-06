import streamlit as st
import plotly.graph_objs as go
import logging
import warnings
# Suppress specific FutureWarning from pandas
warnings.filterwarnings(action='ignore', category=FutureWarning, message="The default of observed=False is deprecated")

from utils.ai_helpers import construct_welcome_message, generate_ai_response
from utils.data_analyst_helpers import *
from widgets.prompt_guide import render_data_analyst_prompt_guide
from utils.security_helpers import SecurityError, safely_execute_code

def render_data_analyst():
    logging.info(f'render_data_analyst - {st.session_state["session_id"]}')
    st.divider()
    st.info('Arctic Analytics AI now has access to the metadata of the files you uploaded. Arctic Analytics will use that to generate code snippets.')
    st.info('The code generated by the AI will be executed in a sandbox environment. The results will be displayed here. The AI does not have access to the results.')

    if 'messages' not in st.session_state.keys() or not st.session_state['messages']:
        st.session_state['messages'] = [{'role': 'assistant', 'content': construct_welcome_message(), 'count': 0}]
        st.session_state['count'] = 0   

    if 'cost' not in st.session_state:
        st.session_state['cost'] = 0

    st.session_state['model'] = st.sidebar.selectbox('Select the model:', ['meta/llama-4-scout-instruct', 'gpt-4.1-nano-2025-04-14'], index=1)

    st.session_state['usage_container'] = st.empty()

    render_data_analyst_prompt_guide()

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

    for message in st.session_state['messages']:
        if 'error' not in message.keys():
            with st.chat_message(message['role']):
                if message['role'] == 'user':
                    st.write(message['content'])
                if message['role'] == 'assistant':
                    if 'python_syntax' in message.keys():
                        if message['python_syntax'] is not None:
                            with st.expander('See Python Syntax'):
                                st.write(message['raw_python'])
                                st.write(message['commentary'])
                            if message['output'] is not None:
                                if isinstance(message['output'], pd.DataFrame):
                                    st.dataframe(message['output'], use_container_width=True, hide_index=False)
                                elif isinstance(message['output'], go.Figure):
                                    st.plotly_chart(message['output'], use_container_width=True)
                            if 'commentary' in message.keys():
                                if message['commentary'] is not None:
                                    st.caption(message['commentary'])
                        else:
                            st.write(message['content'])
                    else:
                        st.write(message['content'])

    if user_input := st.chat_input():
        st.session_state['messages'].append({'role': 'user', 'content': user_input})
        with st.chat_message('user'):
            st.write(user_input)

    # Generate a new response if last message is not from assistant
    if st.session_state['messages'][-1]['role'] != 'assistant':
        with st.chat_message('assistant'):
            with st.spinner('Generating response...'):
                response = generate_ai_response(st.session_state['vetted_files'], st.session_state['model'], False)
                python_syntax, commentary = extract_python_syntax_and_commetary(response)

                logging.info(f'python_syntax - {python_syntax}')
                logging.info(f'commentary - {commentary}')
                
                if python_syntax is not None:
                    check_read_csv_error_and_give_feedback(python_syntax, response)
                    check_read_json_error_and_give_feedback(python_syntax, response)
                    check_function_definition_error_and_give_feedback(python_syntax, response)
                    check_return_statement_error_and_give_feedback(python_syntax, response)

                    python_syntax = remove_st_set_page_config(python_syntax)
                    python_syntax = remove_generate_report(python_syntax)
                    raw_python = "```python"+"\n"+python_syntax+"\n```"

                    with st.expander('See Python Syntax'):
                        st.write(raw_python)
                else:
                    check_response_error_and_give_feedback(response)
                    raw_python = None
                    output = None
                    plot = None
                    st.write(response)

                if python_syntax is not None:
                    try:
                        # Use the security helper to safely execute code
                        output, stdout_output, error_message = safely_execute_code(python_syntax, st.session_state['vetted_files'], 'generate_report')
                        
                        if error_message:
                            # Raise RuntimeError to go through the exception block
                            raise RuntimeError(f"error_message: {error_message}\n\nCode output: {stdout_output}")
                            
                    except (SyntaxError, ValueError, TypeError, KeyError, AttributeError, IndexError, NameError, ModuleNotFoundError, RuntimeError) as e:
                        handle_all_other_errors(e, response)

                check_outputs_and_give_feedback(output, commentary, response)

        message = {'role': 'assistant', 'content': response, 'count': st.session_state['count'], 'raw_python': raw_python, 'python_syntax': python_syntax, 'commentary': commentary, 'output': output}
        st.session_state['messages'].append(message)

    with st.session_state['usage_container']:
        st.sidebar.metric(
            label='Usage in this session',
            value=f'${st.session_state["cost"]}',
        )
