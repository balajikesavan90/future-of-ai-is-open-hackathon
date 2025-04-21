import streamlit as st
import os
import json
import logging
from pydantic import BaseModel, Field

# from utils.snowflake_arctic_helpers import construct_arctic_prompt, generate_arctic_response
from utils.meta_llama_helpers import MetaLlama
# from utils.mistral_helpers import construct_mistral_prompt, generate_mistral_response
from utils.system_messages import construct_system_message
from utils.open_ai_helpers import chatcompletion_APICall, token_count_message
from utils.streamlit_helpers import reset_data_analyst

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


class ResponseFormat(BaseModel):
    python_syntax: str = Field(..., description="The generated python syntax.")
    commentary: str = Field(..., description="The commentary for the user.")

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


def generate_gpt4o_mini_response(vetted_files):
    logging.info(f'generate_gpt4o_mini_response - {st.session_state["session_id"]}')

    system_message = construct_system_message(vetted_files)

    prompt = [{'role': 'system', 'content': system_message}]

    for dict_message in st.session_state['messages']:
        prompt.append({'role': dict_message['role'], 'content': dict_message['content']})

    token_count = token_count_message(prompt)
    logging.info(f'token_count - {token_count} - {st.session_state["session_id"]}')

    error_count = 0
    for message in st.session_state['messages']:
        if 'error' in message.keys():
            if message['role'] == 'assistant':
                error_count += 1

    if error_count >= 3:
        st.error('Oops! Something went wrong. Try rephrasing your prompt in a different way.')
        st.button(':red[Reset Data Analyst]', on_click=reset_data_analyst, key='reset')
        if st.secrets['ENV'] == 'dev':
            st.write(st.session_state['messages'])
        st.stop()

    if token_count >= 3072:
        st.error('Conversation length too long. Please keep it under 3072 tokens.')
        st.button(':red[Reset Data Analyst]', on_click=reset_data_analyst, key='reset')
        if st.secrets['ENV'] == 'dev':
            st.write(st.session_state['messages'])
        st.stop()

    response, cost = chatcompletion_APICall(prompt, model='gpt-4.1-mini-2025-04-14', temperature=0.1, response_format=ResponseFormat)
    st.session_state['prompt_str'] = ""
    for dict_message in prompt:
        st.session_state['prompt_str'] += f"role: {dict_message['role']}\ncontent: {dict_message['content']}\n--\n"
    return response
