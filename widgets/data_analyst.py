import streamlit as st

import warnings
# Suppress specific FutureWarning from pandas
warnings.filterwarnings(action='ignore', category=FutureWarning, message="The default of observed=False is deprecated")

from utils.ai_helpers import construct_welcome_message, generate_ai_response
from utils.data_analyst_and_chart_builder_helpers import *
from widgets.prompt_guide import render_data_analyst_prompt_guide

def render_data_analyst():
    st.divider()
    st.subheader('🔍 :blue[Data Analyst]')
    st.success(':green[Arctic Analytics AI now has access to the metadata of the files you uploaded. Arctic Analytics will use that to generate code snippets.]')
    st.info(':blue[The code generated by the AI will be executed in a sandbox environment. The results will be displayed here. The AI does not have access to the results.]')

    if 'messages' not in st.session_state.keys() or not st.session_state['messages']:
        st.session_state['messages'] = [{'role': 'assistant', 'content': construct_welcome_message('data_analyst'), 'count': 0}]
        st.session_state['count'] = 0   

    render_data_analyst_prompt_guide()

    with st.expander('See uploaded Datasets'):
        for filename in st.session_state['vetted_files']:
            st.subheader(f':blue[{filename}]')
            data_filter = st.selectbox(
                label='Select the number of rows to display',
                options=['First 5 rows', 'Last 5 rows', 'Random 5 rows'],
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
                            if message['output'] is not None:
                                hide_index = st.checkbox('Hide Index', key=str(message['count']), value=False)
                                st.dataframe(message['output'], hide_index=hide_index, use_container_width=True)
                            if message['plot'] is not None:
                                st.write(message['plot'])
                                # st.pyplot(message['plot'])
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
                response = generate_ai_response('data_analyst')
                python_syntax, commentary = extract_python_syntax_and_commetary(response)
                
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
                    python_syntax = update_python_syntax_with_correct_dataframe_names(python_syntax)
                else:
                    check_response_error_and_give_feedback(response)
                    raw_python = None
                    output = None
                    plot = None
                    st.write(response)

                if python_syntax is not None:
                    try:
                        exec(python_syntax)
                        output = eval('generate_report()')
                        plot = None
                    except (SyntaxError, ValueError, TypeError, KeyError, AttributeError, IndexError, NameError, ModuleNotFoundError) as e:
                        handle_all_other_errors(e, response)

                check_outputs_and_give_feedback(output, plot, response)

        message = {'role': 'assistant', 'content': response, 'count': st.session_state['count'], 'raw_python': raw_python, 'python_syntax': python_syntax, 'commentary': commentary, 'output': output, 'plot': plot}
        st.session_state['messages'].append(message)