import streamlit as st
import re
import json
import pandas as pd

def extract_python_syntax(text):
    pattern = r'```python(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return None

def extract_commentary(text):
    pattern = r'```python.*?```'
    commentary = re.sub(pattern, '', text, flags=re.DOTALL)
    return commentary.strip()

def extract_python_syntax_and_commetary(response):
    try:
        response_dict = json.loads(response)
        python_syntax = response_dict['python_syntax']
        commentary = response_dict['commentary']
    except json.JSONDecodeError as e:
        python_syntax = extract_python_syntax(response)
        commentary = extract_commentary(response)
    return python_syntax, commentary

def check_read_csv_error_and_give_feedback(python_syntax, response):
    if 'read_csv' in python_syntax:
        st.session_state['count'] += 1
        message = {'role': 'assistant', 'content': response, 'error': True}
        st.session_state['messages'].append(message)
        pandas_dataframes = ''
        if len(st.session_state['vetted_files']) > 1:
            for filename in st.session_state['vetted_files']:
                pandas_dataframes += f", {filename}"  
            message = {'role': 'user', 'content': f'{pandas_dataframes} are already loaded as pandas dataframe. Please remove the read_csv statement', 'error': True}
        else:
            message = {'role': 'user', 'content': f'{filename} is already loaded as a pandas dataframe. Please remove the read_csv statement', 'error': True}
        st.session_state['messages'].append(message)
        st.rerun()

def check_read_json_error_and_give_feedback(python_syntax, response):
    if 'read_json' in python_syntax:
        st.session_state['count'] += 1
        message = {'role': 'assistant', 'content': response, 'error': True}
        st.session_state['messages'].append(message)
        pandas_dataframes = ''
        if len(st.session_state['vetted_files']) > 1:
            for filename in st.session_state['vetted_files']:
                pandas_dataframes += f", {filename}"  
            message = {'role': 'user', 'content': f'{pandas_dataframes} are already loaded as pandas dataframe. Please remove the read_json statement', 'error': True}
        else:
            message = {'role': 'user', 'content': f'{filename} is already loaded as a pandas dataframe. Please remove the read_json statement', 'error': True}
        st.session_state['messages'].append(message)
        st.rerun()

def check_function_definition_error_and_give_feedback(python_syntax, response):
    if 'def generate_report():' not in python_syntax:
        st.session_state['count'] += 1
        message = {'role': 'assistant', 'content': response, 'error': True}
        st.session_state['messages'].append(message)
        message = {'role': 'user', 'content': 'The function should be called "generate_report". It must take 0 arguments. The function must return a single pandas DataFrame', 'error': True}
        st.session_state['messages'].append(message)
        st.rerun()

def remove_st_set_page_config(input_string):
    # This regex pattern matches 'st.set_page_config()' and its variants with any arguments
    pattern = r"st\.set_page_config\([^\)]*\)"
    # Substitute the matched pattern with an empty string
    output_string = re.sub(pattern, '', input_string)
    return output_string

def remove_generate_report(input_string):
    """removes the function call (if present) because function call is done deliberately to avoid double outputs"""
    # This regex pattern matches the line 'generate_report()'
    pattern = r"generate_report\(\)\n"
    # Substitute the matched pattern with an empty string
    output_string = re.sub(pattern, '', input_string)
    return output_string

def update_python_syntax_with_correct_dataframe_names(python_syntax):
    for filename in st.session_state['vetted_files']:
        st.session_state['vetted_files'][f"{filename}"]['dataframe_copy'] = st.session_state['vetted_files'][filename]['dataframe'].copy()
        pattern = re.compile(r'\b' + re.escape(filename) + r'\b')
        python_syntax = pattern.sub(f"st.session_state['vetted_files']['{filename}']['dataframe_copy']", python_syntax)
    return python_syntax

def check_outputs_and_give_feedback(output, response):
    if st.session_state['task'] in ['manipulate', 'consult']:
        if isinstance(output, pd.DataFrame):
            st.dataframe(output.reset_index(), use_container_width=True, hide_index=True)
        else:
            st.session_state['count'] += 1
            message = {'role': 'assistant', 'content': response, 'error': True}
            st.session_state['messages'].append(message)
            message = {'role': 'user', 'content': 'The generate_report() function must return a single pandas DataFrame', 'error': True}
            st.session_state['messages'].append(message)
            st.rerun()

def handle_all_other_errors(e, response):
    st.session_state['count'] += 1
    message = {'role': 'assistant', 'content': response, 'error': True}
    st.session_state['messages'].append(message)
    error_message = f"""{type(e).__name__}: {str(e)}
    {e.__traceback__}
    """
    message = {'role': 'user', 'content': error_message, 'error': True}
    st.session_state['messages'].append(message)
    st.rerun()
