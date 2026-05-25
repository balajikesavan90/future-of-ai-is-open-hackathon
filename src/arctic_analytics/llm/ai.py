import streamlit as st
import logging

from arctic_analytics.llm.openai_responses import OpenAIResponsesUtility

openai_responses_client = OpenAIResponsesUtility()

def construct_welcome_message():
    logging.info(f'construct_welcome_message - {st.session_state["session_id"]}')

    welcome_message = f"""Hello. Arctic Analytics can help generate metadata-aware analysis over your structured data.
I have access to the metadata of the files you uploaded and will use that context to generate inspectable code for constrained execution.
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


def generate_ai_response(vetted_files, model):
    logging.info(f'generate_ai_response - {st.session_state["session_id"]}')
    return openai_responses_client.generate_openai_response(vetted_files, model)
