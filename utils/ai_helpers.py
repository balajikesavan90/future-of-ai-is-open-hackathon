import streamlit as st
import logging

from utils.meta_llama_helpers import MetaLlama
from utils.open_ai_helpers import OpenAIUtility

llama_client = MetaLlama()
openai_client = OpenAIUtility()

def construct_welcome_message():
    logging.info(f'construct_welcome_message - {st.session_state["session_id"]}')

    welcome_message = f"""Hello! I am the Arctic Analytics AI. I can help you analyze your data.
I have access to the metadata of the files you uploaded. I will use that to generate code snippets and execute them in a sandbox environment.
\n\n"""
    
    if len(st.session_state['vetted_files']) == 1:
        welcome_message += 'I have detected the following pandas dataframe:\n\n'
        for file_name in st.session_state['vetted_files']:
            column_names = ', '.join(st.session_state["vetted_files"][file_name]["columns_names"])
            welcome_message += f'The pandas dataframe :blue[{file_name}] has :blue[{st.session_state['vetted_files'][file_name]['dataframe'].shape[0]}] rows with columns: :blue[{column_names}].\n\n'
    else:
        welcome_message += 'I have detected the following pandas dataframes:\n\n'
        for file_name in st.session_state['vetted_files']:
            column_names = ', '.join(st.session_state["vetted_files"][file_name]["columns_names"])
            welcome_message += f'The pandas dataframe :blue[{file_name}] has :blue[{st.session_state['vetted_files'][file_name]['dataframe'].shape[0]}] rows with columns: :blue[{column_names}].\n\n'
    return welcome_message


def generate_ai_response(vetted_files, model, agent_model=False):
    logging.info(f'generate_ai_response - {st.session_state["session_id"]}')
    
    if 'meta' in model.lower() or 'llama' in model.lower():
        response = llama_client.generate_llama_response(vetted_files, model, False)
    else:
        response = openai_client.generate_openai_response(vetted_files, model, agent_model)
        
    return response

