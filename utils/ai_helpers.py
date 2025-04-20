import streamlit as st
import os
import json
import logging

# from utils.snowflake_arctic_helpers import construct_arctic_prompt, generate_arctic_response
from utils.meta_llama_helpers import MetaLlama
# from utils.mistral_helpers import construct_mistral_prompt, generate_mistral_response
from utils.open_ai_helpers import generate_gpt4o_mini_response
from utils.system_messages import generate_explanation_system_message, generate_docstring_system_message, generate_debugger_system_message

llama_client = MetaLlama()

def construct_welcome_message():
    logging.info(f'construct_welcome_message - {st.session_state["session_id"]}')

    welcome_message = f"""Hello! I am the Arctic Analytics AI. I can help you analyze your data.
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

def generate_ai_response(vetted_files, model):
    logging.info(f'generate_ai_response - {st.session_state["session_id"]}')
    if model == 'meta/llama-4-scout-instruct':
        prompt_str = llama_client.construct_llama_prompt(vetted_files)
        response = llama_client.generate_llama_response(prompt_str)
    elif model == 'gpt-4.1-mini-2025-04-14':
        response = generate_gpt4o_mini_response(vetted_files)
    # elif model == 'mistral':
    #     prompt_str = construct_mistral_prompt(vetted_files)
    #     response = generate_mistral_response(prompt_str)
    # elif model == 'arctic':
    #     prompt_str = construct_arctic_prompt(vetted_files)
    #     response = generate_arctic_response(prompt_str)
    return response



