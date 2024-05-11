import streamlit as st
import re
import json
import pandas as pd

def extract_python_syntax(text):
    pattern = r'```(python|json)(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        print('extract_python_or_json_syntax')
        return match.group(2).strip()
    else:
        return None
    
def extract_commentary(text):
    print('extract_commentary')
    pattern = r'```(python|json).*?```'
    commentary = re.sub(pattern, '', text, flags=re.DOTALL)
    return commentary.strip()

def extract_python_syntax_and_commetary(response):
    print('extract_python_syntax_and_commetary')
    try:
        response_dict = json.loads(response)
        python_syntax = response_dict['python_syntax']
        commentary = response_dict['commentary']
    except json.JSONDecodeError as e:
        python_syntax = extract_python_syntax(response)
        commentary = extract_commentary(response)

    print(python_syntax)
    return python_syntax, commentary

def check_read_csv_error_and_give_feedback(python_syntax, response):
    if 'read_csv' in python_syntax:
        print('check_read_csv_error_and_give_feedback')
        st.session_state['count'] += 1
        message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
        st.session_state['messages'].append(message)
        pandas_dataframes = ''
        if len(st.session_state['vetted_files']) >= 1:
            for filename in st.session_state['vetted_files']:
                pandas_dataframes += f", {filename}"  
            message = {'role': 'user', 'content': f'{pandas_dataframes} are already loaded as pandas dataframe. Please remove the read_csv statement', 'error': True}
        st.session_state['messages'].append(message)
        print('rerun - check_read_csv_error_and_give_feedback - failure')
        st.rerun()

def check_read_json_error_and_give_feedback(python_syntax, response):
    if 'read_json' in python_syntax:
        print('check_read_json_error_and_give_feedback')
        st.session_state['count'] += 1
        message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
        st.session_state['messages'].append(message)
        pandas_dataframes = ''
        if len(st.session_state['vetted_files']) >= 1:
            for filename in st.session_state['vetted_files']:
                pandas_dataframes += f", {filename}"  
            message = {'role': 'user', 'content': f'{pandas_dataframes} are already loaded as pandas dataframe. Please remove the read_json statement', 'error': True}
        st.session_state['messages'].append(message)
        print('rerun - check_read_json_error_and_give_feedback - failure')
        st.rerun()

def check_function_definition_error_and_give_feedback(python_syntax, response):
    if 'def generate_report():' not in python_syntax:
        print('check_function_definition_error_and_give_feedback')
        st.session_state['count'] += 1
        message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
        st.session_state['messages'].append(message)
        message = {'role': 'user', 'content': 'The function should be called "generate_report". It must take 0 arguments. The function must return a single pandas DataFrame', 'error': True}
        st.session_state['messages'].append(message)
        print('rerun - check_function_definition_error_and_give_feedback - failure')
        print()
        st.rerun()

def remove_st_set_page_config(input_string):
    print('remove_st_set_page_config')
    # This regex pattern matches 'st.set_page_config()' and its variants with any arguments
    pattern = r"st\.set_page_config\([^\)]*\)"
    # Substitute the matched pattern with an empty string
    output_string = re.sub(pattern, '', input_string)
    return output_string

def remove_generate_report(input_string):
    print('remove_generate_report')
    """removes the function call (if present) because function call is done deliberately to avoid double outputs"""
    # This regex pattern matches the line 'generate_report()'
    pattern = r"generate_report\(\)\n"
    # Substitute the matched pattern with an empty string
    output_string = re.sub(pattern, '', input_string)
    return output_string

def update_python_syntax_with_correct_dataframe_names(python_syntax):
    for filename in st.session_state['vetted_files']:
        print('update_python_syntax_with_correct_dataframe_names')
        st.session_state['vetted_files'][f"{filename}"]['dataframe_copy'] = st.session_state['vetted_files'][filename]['dataframe'].copy()
        pattern = re.compile(r'\b' + re.escape(filename) + r'\b')
        python_syntax = pattern.sub(f"st.session_state['vetted_files']['{filename}']['dataframe_copy']", python_syntax)
    return python_syntax

def check_outputs_and_give_feedback(output, plot, response):
    if output is not None:
        if isinstance(output, pd.DataFrame):
            print(f'check_outputs_and_give_feedback - success - {st.session_state["active_page"]}')
            st.session_state['count'] += 1
            hide_index = st.checkbox('Hide Index', key=str(st.session_state['count']), value=False)
            st.dataframe(output, use_container_width=True, hide_index=hide_index)
            # if st.secrets['ENV'] == 'dev':
            #     for message in st.session_state['messages']:
            #         if 'error' in message.keys():
            #             st.session_state['messages'].remove(message)
        else:
            print(f'check_outputs_and_give_feedback - error - {st.session_state["active_page"]}')
            st.session_state['count'] += 1
            message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
            st.session_state['messages'].append(message)
            message = {'role': 'user', 'content': 'The generate_report() function must return a single pandas DataFrame', 'error': True}
            st.session_state['messages'].append(message)
            print('rerun - check_outputs_and_give_feedback - failure')
            st.rerun()
    if plot is not None:
        print(type(plot))
        if isinstance(plot, st.delta_generator.DeltaGenerator):
            print(f'check_outputs_and_give_feedback - success - {st.session_state["active_page"]}')
            if st.secrets['EVN'] == 'dev':
                for message in st.session_state['messages']:
                    if 'error' in message.keys():
                        st.session_state['messages'].remove(message)
            plot
        else:
            print(f'check_outputs_and_give_feedback - error - {st.session_state["active_page"]}')
            st.session_state['count'] += 1
            message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
            st.session_state['messages'].append(message)
            message = {'role': 'user', 'content': 'The generate_report() function must return a single Streamlit Chart element', 'error': True}
            st.session_state['messages'].append(message)
            print('rerun - check_outputs_and_give_feedback - failure')
            st.rerun()

def check_response_error_and_give_feedback(response):
    if ('return' in response) | ('def generate_report()' in response) | ('commentary' in response):
        print('check_response_error_and_give_feedback')
        st.session_state['count'] += 1
        message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
        st.session_state['messages'].append(message)
        message = {'role': 'user', 'content': 'Your output should be JSON string with the keys "python_syntax" and "commentary"', 'error': True}
        st.session_state['messages'].append(message)
        print('rerun - check_response_error_and_give_feedback - failure')
        st.rerun()

def handle_all_other_errors(e, response):
    print('handle_all_other_errors')
    st.session_state['count'] += 1
    message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
    st.session_state['messages'].append(message)
    error_message = f"""{type(e).__name__}: {str(e)}
    {e.__traceback__}
    """
    message = {'role': 'user', 'content': error_message, 'error': True}
    st.session_state['messages'].append(message)
    print(f'rerun - {type(e).__name__}: {str(e)}\n\n{e.__traceback__}')
    st.rerun()