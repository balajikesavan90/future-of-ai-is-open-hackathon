import streamlit as st
import os
import json

from utils.snowflake_arctic_helpers import construct_arctic_prompt, generate_arctic_response
from utils.meta_llama_helpers import construct_llama_prompt, generate_llama_response
from utils.mistral_helpers import construct_mistral_prompt, generate_mistral_response
from utils.open_ai_helpers import generate_gpt4o_mini_response
from utils.system_messages import generate_explanation_system_message, generate_docstring_system_message, generate_debugger_system_message

os.environ['REPLICATE_API_TOKEN'] = st.secrets['REPLICATE_API_TOKEN']

def construct_welcome_message(page):
    print('construct_welcome_message')

    if page == 'data_analyst':
        welcome_message = f"""Hello! I am the Arctic Analytics AI. I can help you analyze your data.
I have access to the metadata of the files you uploaded. I will use that to generate code snippets and execute them in a sandbox environment.
\n\n"""
    elif page == 'chart_builder':
        welcome_message = f"""Hello! I am the Arctic Analytics AI. I can help you generate plots from your data.
I have access to the metadata of the files you uploaded. I will use that to generate code snippets and execute them in a sandbox environment.
\n\n"""
    
    if len(st.session_state['vetted_files']) == 1:
        welcome_message += 'I have found the following pandas dataframes:\n'
        for file_name in st.session_state['vetted_files']:
            column_names = ', '.join(st.session_state["vetted_files"][file_name]["columns_names"])
            welcome_message += f'The pandas dataframe :blue[{file_name}] has the columns: :blue[{column_names}].'
    else:
        welcome_message += 'I have detected the following pandas dataframes:\n'
        for file_name in st.session_state['vetted_files']:
            column_names = ', '.join(st.session_state["vetted_files"][file_name]["columns_names"])
            welcome_message += f'\n- The pandas dataframe :blue[{file_name}] has the columns: :blue[{column_names}].'


    return welcome_message


def generate_ai_response(page, vetted_files, model):
    print('generate_ai_response')
    if model == 'arctic':
        prompt_str = construct_arctic_prompt(page, vetted_files)
        response = generate_arctic_response(prompt_str)
    elif model == 'llama-3.1':
        prompt_str = construct_llama_prompt(page, vetted_files)
        response = generate_llama_response(prompt_str)
    elif model == 'mistral':
        prompt_str = construct_mistral_prompt(page, vetted_files)
        response = generate_mistral_response(prompt_str)
    elif model == 'gpt-4o-mini':
        response = generate_gpt4o_mini_response(page, vetted_files)
    return response
    
def generate_explanation_response(code_snippet):
    print('generate_explanation_response')
    with st.session_state['output_container']:
        with st.spinner('Generating Explanation...'):
            prompt = [f"<|im_start|>system\n{generate_explanation_system_message}<|im_end|>"]
            prompt.append('<|im_start|>user\n' + code_snippet + '<|im_end|>')
            prompt.append('<|im_start|>assistant')
            prompt.append('')
            prompt_str = '\n'.join(prompt)
            return generate_arctic_response(prompt_str)
    
def generate_docstring_response(code_snippet):
    print('generate_docstring_response')
    with st.session_state['output_container']:
        with st.spinner('Generating Docstrings...'):
            prompt = [f"<|im_start|>system\n{generate_docstring_system_message}<|im_end|>"]
            prompt.append('<|im_start|>user\n' + code_snippet + '<|im_end|>')
            prompt.append('<|im_start|>assistant')
            prompt.append('')
            prompt_str = '\n'.join(prompt)
            return generate_arctic_response(prompt_str)

def generate_debugger_response(code_snippet, error_message):
    print('generate_debugger_response')
    with st.session_state['output_container']:
        with st.spinner('Generating Debugger Response...'):
            prompt = [f"<|im_start|>system\n{generate_debugger_system_message}<|im_end|>"]
            input = {'code_snippet': code_snippet, 'error_message': error_message}
            input_json = json.dumps(input)
            prompt.append('<|im_start|>user\n' + input_json + '<|im_end|>')
            prompt.append('<|im_start|>assistant')
            prompt.append('')
            prompt_str = '\n'.join(prompt)
            return generate_arctic_response(prompt_str)




