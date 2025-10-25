import streamlit as st
import re
import json
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import numpy as np

from utils.streamlit_helpers import render_ai_prompt

def extract_python_syntax(text):
    pattern = r'```(python|json)(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        logging.info(f'extract_python_or_json_syntax - {st.session_state["session_id"]}')
        return json.loads(match.group(2).strip())['python_syntax']
    else:
        return None
    
def extract_commentary(text):
    logging.info(f'extract_commentary - {st.session_state["session_id"]}')
    pattern = r'```(python|json).*?```'
    commentary = re.sub(pattern, '', text, flags=re.DOTALL)
    return commentary.strip()

def add_closing_backticks(s):
    if s.count("```") % 2 != 0:  # If the count of ``` is odd
        logging.info(f'add_closing_backticks - {st.session_state["session_id"]}')
        s += "```"  # Append closing ```
    return s

def extract_python_syntax_and_commetary(response):
    logging.info(f'extract_python_syntax_and_commetary - {st.session_state["session_id"]}') 
    response = add_closing_backticks(response)  
    opening_braces = response.count('{')
    closing_braces = response.count('}')
    if closing_braces < opening_braces:
        response += '}' * (opening_braces - closing_braces)
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
        message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
        st.session_state['messages'].append(message)
        pandas_dataframes = ''
        if len(st.session_state['vetted_files']) >= 1:
            for filename in st.session_state['vetted_files']:
                pandas_dataframes += f", {filename}"
        error_message = f'{pandas_dataframes} are already loaded as pandas dataframe. Please remove the read_csv statement'
        message = {'role': 'user', 'content': json.dumps({'error': error_message}), 'error': True}
        st.session_state['messages'].append(message)
        logging.info(f'rerun - check_read_csv_error_and_give_feedback - failure - {st.session_state["session_id"]}')
        st.rerun()

def check_read_json_error_and_give_feedback(python_syntax, response):
    if 'read_json' in python_syntax:
        st.session_state['count'] += 1
        message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
        st.session_state['messages'].append(message)
        pandas_dataframes = ''
        if len(st.session_state['vetted_files']) >= 1:
            for filename in st.session_state['vetted_files']:
                pandas_dataframes += f", {filename}"  
        error_message = f'{pandas_dataframes} are already loaded as pandas dataframe. Please remove the read_json statement'
        message = {'role': 'user', 'content': json.dumps({'error': error_message}), 'error': True}
        st.session_state['messages'].append(message)
        logging.info(f'rerun - check_read_json_error_and_give_feedback - failure - {st.session_state["session_id"]}')
        st.rerun()

def check_function_definition_error_and_give_feedback(python_syntax, response):
    if 'def generate_report():' not in python_syntax:
        st.session_state['count'] += 1
        message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
        st.session_state['messages'].append(message)
        error_message = 'The function should be called "generate_report". It must take 0 arguments. The function must return a single pandas DataFrame or a single plotly plot'
        message = {'role': 'user', 'content': json.dumps({'error': error_message}), 'error': True}
        st.session_state['messages'].append(message)
        logging.info(f'rerun - check_function_definition_error_and_give_feedback - failure - {st.session_state["session_id"]}')
        st.rerun()

def check_return_statement_error_and_give_feedback(python_syntax, response):
    if 'return ' not in python_syntax:
        st.session_state['count'] += 1
        message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
        st.session_state['messages'].append(message)
        error_message = 'Please add a return statement to the function generate_report() that returns a single pandas DataFrame or a single plotly plot'
        message = {'role': 'user', 'content': json.dumps({'error': error_message}), 'error': True}
        st.session_state['messages'].append(message)
        logging.info(f'rerun - check_return_statement_error_and_give_feedback - failure - {st.session_state["session_id"]}')
        st.rerun()

def remove_st_set_page_config(input_string):
    logging.info(f'remove_st_set_page_config - {st.session_state["session_id"]}')
    # This regex pattern matches 'st.set_page_config()' and its variants with any arguments
    pattern = r"st\.set_page_config\([^\)]*\)"
    # Substitute the matched pattern with an empty string
    output_string = re.sub(pattern, '', input_string)
    return output_string

def remove_generate_report(input_string):
    logging.info(f'remove_generate_report - {st.session_state["session_id"]}')
    """removes the function call (if present) because function call is done deliberately to avoid double outputs"""
    # This regex pattern matches the line 'generate_report()'
    pattern = r"generate_report\(\)\n"
    # Substitute the matched pattern with an empty string
    output_string = re.sub(pattern, '', input_string)
    return output_string

def check_outputs_and_give_feedback(output, commentary, response):
    if output is not None:
        if isinstance(output, pd.DataFrame) or isinstance(output, go.Figure):
            st.session_state['count'] += 1
            if isinstance(output, pd.DataFrame):
                logging.info(f'check_outputs_and_give_feedback - dataframe - success - {st.session_state["session_id"]}')
                st.dataframe(output, width='stretch', hide_index=False)
            elif isinstance(output, go.Figure):
                logging.info(f'check_outputs_and_give_feedback - plot - success - {st.session_state["session_id"]}')
                st.plotly_chart(output, width='stretch')
            if commentary is not None:
                st.caption(commentary)
            render_ai_prompt()
            if st.secrets['ENV'] != 'dev':
                for message in st.session_state['messages']:
                    if 'error' in message.keys():
                        st.session_state['messages'].remove(message)
        else:
            st.session_state['count'] += 1
            message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
            st.session_state['messages'].append(message)
            error_message = 'The generate_report() function must return a single pandas DataFrame or a single plotly plot'
            message = {'role': 'user', 'content': json.dumps({'error': error_message}), 'error': True}
            st.session_state['messages'].append(message)
            logging.info(f'rerun - check_outputs_and_give_feedback - error - {st.session_state["session_id"]}')
            st.rerun()

def check_response_error_and_give_feedback(response):
    if ('return' in response) | ('def generate_report()' in response) | ('commentary' in response):
        st.session_state['count'] += 1
        message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
        st.session_state['messages'].append(message)
        error_message = 'Your output should be JSON string with the keys "python_syntax" and "commentary"'
        message = {'role': 'user', 'content': json.dumps({'error': error_message}), 'error': True}
        st.session_state['messages'].append(message)
        logging.info(f'rerun - check_response_error_and_give_feedback - failure - {st.session_state["session_id"]}')
        st.rerun()

def handle_all_other_errors(e, response):
    st.session_state['count'] += 1
    message = {'role': 'assistant', 'content': response, 'error': True, 'count': st.session_state['count']}
    st.session_state['messages'].append(message)
    error_message = f"""{type(e).__name__}: {str(e)}
    {e.__traceback__}
    """
    message = {'role': 'user', 'content': json.dumps({'error': error_message}), 'error': True}
    st.session_state['messages'].append(message)
    logging.info(f'rerun - handle_all_other_errors - failure - {st.session_state["session_id"]}')
    st.rerun()
