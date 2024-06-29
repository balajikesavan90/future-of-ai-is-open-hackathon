import streamlit as st
import os
import json

from utils.snowflake_arctic_helpers import construct_arctic_prompt, generate_arctic_response

os.environ['REPLICATE_API_TOKEN'] = st.secrets['REPLICATE_API_TOKEN']

generate_explanation_system_message = """You are an automated system that explains the computer code inputted by the user.
You must explain the code in a way that is easy to understand for a non-technical audience.
You must explain the purpose of the code, the logic behind the code, and the expected output of the code.
You must use simple language and avoid technical jargon.
You must generate your output in bullet points with short sentences.
Your output must be in github markdown format.
"""

generate_docstring_system_message = """You are an automated system that generates comments and docstrings for the computer code inputted by the user.
Your output must be a version of the user's code with comments and docstrings added.
The doc strings must include the function name, the purpose of the function, and the input and output parameters.
The comments must explain the logic and reasoning behind the code.
You must include comments for each line of code.
The comments must be written in a way that is easy to understand for someone who is not familiar with the code.
"""

generate_debugger_system_message = """You are an automated system that generates a response to a user's code snippet and error message.
You must generate a response that helps the user debug their code.
You must provide a detailed explanation of the error message and suggest possible solutions.
You must generate your output in markdown format.
You must include code snippets and explanations in your response.
You must focus on helping the user understand the error message and how to fix it.
"""

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


def generate_ai_response(page):
    print('generate_ai_response')
    prompt_str = construct_arctic_prompt(page)
    response = generate_arctic_response(prompt_str)
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




