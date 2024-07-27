import streamlit as st

import warnings
# Suppress specific FutureWarning from pandas
warnings.filterwarnings(action='ignore', category=FutureWarning, message="The default of observed=False is deprecated")

from utils.ai_helpers import construct_welcome_message, generate_ai_response
from utils.data_analyst_and_chart_builder_helpers import *

from widgets.prompt_guide import render_chart_builder_prompt_guide

def render_chart_builder():
    st.divider()
    st.subheader('📊 :blue[Chart Builder]')
    st.success(':green[Arctic Analytics AI now has access to the metadata of the files you uploaded. Arctic Analytics will use that to generate code snippets.]')
    st.info(':blue[The code generated by the AI will be executed in a sandbox environment. The results will be displayed here. The AI does not have access to the results.]')

    welcome_message = construct_welcome_message('chart_builder')

    render_chart_builder_prompt_guide()

    if 'messages' not in st.session_state.keys() or not st.session_state['messages']:
        st.session_state['messages'] = [{'role': 'assistant', 'content': welcome_message, 'count': 0}]
        st.session_state['count'] = 0   


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

    with st.form(key='chart_builder_form'):

        st.write(welcome_message)
        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            x_axis_description = st.text_input(
                label='Describe what you want on the X-axis:',
            )
        with col2:
            y_axis_description = st.text_input(
                label='Describe what you want on the Y-axis:',
            )
        col1, col2, col3 = st.columns([1,1,3])
        with col1:
            chart_type = st.selectbox(
                label='Select the chart type:',
                options=['Bar', 'Line', 'Scatter', 'Area'],
            )
        with col2:
            color = st.color_picker(
                label='Select a color for the chart:',
                value='#1f77b4'
            )

        with col3:
            additional_instructions = st.text_input(
                label='Additional Instructions (Optional):',
            )
        if st.form_submit_button(
            label=':green[Generate Chart]',
            use_container_width=True
        ):
            st.session_state['active_page'] = 'chart_builder'
            st.session_state['messages'] = [{'role': 'assistant', 'content': welcome_message, 'count': 0}]
            st.session_state['count'] = 0   
            if x_axis_description.strip() == '' or y_axis_description.strip() == '':
                st.warning('Please provide a description for the X-axis and Y-axis.')
                st.stop()
            inputs = {
                'x_axis_description': x_axis_description,
                'y_axis_description': y_axis_description,
                'chart_type': chart_type,
                'color': color,
                'additional_instructions': additional_instructions
            }
            chart_builder_inputs = {k: v for k, v in inputs.items() if v != '' or k in ['x_axis_description', 'y_axis_description', 'chart_type']}
            st.session_state['messages'].append({'role': 'user', 'content': chart_builder_inputs})
        chart_container = st.container()

    with chart_container:
        # Generate a new response if last message is not from assistant
        if st.session_state['messages'][-1]['role'] != 'assistant':
            with st.spinner('Building Chart...'):
                response = generate_ai_response('chart_builder', st.session_state['vetted_files'], model='llama')
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
                    with st.spinner('Running the code snippet...'):
                        try:
                            exec(python_syntax)
                            plot = eval('generate_report()')
                            output = None
                        except (SyntaxError, ValueError, TypeError, KeyError, AttributeError, IndexError, NameError, ModuleNotFoundError) as e:
                            handle_all_other_errors(e, response)

                check_outputs_and_give_feedback(output, commentary, plot, response)
            message = {'role': 'assistant', 'content': response, 'count': st.session_state['count'], 'raw_python': raw_python, 'python_syntax': python_syntax, 'commentary': commentary, 'output': output, 'plot': plot}
            st.session_state['messages'].append(message)