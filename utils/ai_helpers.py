import streamlit as st
import replicate
import os
import re
from transformers import AutoTokenizer
import json

from utils.streamlit_helpers import reset_data_analyst, reset_chart_builder

os.environ['REPLICATE_API_TOKEN'] = st.secrets['REPLICATE_API_TOKEN']
temperature = 0
top_p = 0.9

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

def construct_system_message(page):
    print('construct_system_message')
    system_message = """You are an automated system that generates python syntax that is executed on a cloud server. 
The python virtual environment has the latest versions of streamlit, pandas, numpy.
\n\n"""

    system_message += """Your task is to complete this code snippet with the appropriate python syntax.\n
import streamlit as st\n
import pandas as pd\n
import numpy as np\n
\n\n"""

    for filename in st.session_state['vetted_files']:
        system_message += f'{filename} = pd.read_csv("{filename}.csv")\n\n'
    

    if page == 'data_analyst':
        system_message += """Your input will be a JSON string with the key 'user_input' and the value as a string of the user's request.

Your ouput must be a JSON string with the keys 'python_syntax' and 'commentary'.
The 'python_syntax' should be a single python function named 'generate_report' that takes in 0 arguments. 
The 'generate_report' function must return a single pandas DataFrame. 
This is a very serious requirement for all of your responses.\n\n"""
    elif page == 'chart_builder':
        system_message += """Your input will be a JSON string with the keys 'x_axis_description', 'y_axis_description', 'chart_type', 'color'.
Your input could also contain the optional key 'additional_instuctions'.

Your ouput must be a JSON string with the keys 'python_syntax' and 'commentary'.
The 'python_syntax' should be a single python function named 'generate_report' that takes in 0 arguments. 
The 'generate_report' function must generate plots using the streamlit chart API elements with appropriate subheaders. 
The 'generate_report' function must return a single Streamlit Chart element.
You can use one of the following Streamlit Chart elements: st.bar_chart, st.line_chart, st.area_chart, st.scatter_chart.
This is a very serious requirement for all of your responses.\n\n"""
    
    system_message += """The 'commentary should be a string with your message to the user. 
In the commentary you must explain your thought process to the user.
You must use the commentary to respond to the user's error messages. 
You must focus your attention on the reasoning and the logic used to create the 'generate_report' function instead of the syntax itself. 
This is a very serious requirement for all of your responses.\n\n"""

    system_message += "Here is the metadata of the files uploaded by the user.\n"
    for filename in st.session_state['vetted_files']:
        system_message += f'\n\n{filename}:\n'
        system_message += f'Description: {st.session_state["vetted_files"][filename]["dataset_description"]}\n'
        system_message += f'Data Dictionary:\n'
        system_message += st.session_state['vetted_files'][filename]['data_dictionary_json']+'\n'
        # system_message += f'Pandas Describe:\n'
        # system_message += st.session_state['vetted_files'][filename]['dataframe'].describe().to_json(orient='index')+'\n'
        system_message += f'First 5 rows of the dataset:\n'
        system_message += st.session_state['vetted_files'][filename]['dataframe'].head().to_json(orient='index')+'\n'
        # system_message += f'Last 5 rows of the dataset:\n'
        # system_message += st.session_state['vetted_files'][filename]['dataframe'].tail().to_json(orient='index')+'\n'
        # system_message += f'The dataset has already been loaded as a pandas DataFrame named {filename}\n\n'
    
    system_message += "You must use this metadata to generate your response.\n"

    st.session_state['system_message'] = system_message

    return system_message


def generate_ai_response(page):
    print('generate_ai_response')
    prompt_str = construct_prompt(page)
    response = generate_arctic_response(prompt_str)
    return response
    
def construct_prompt(page):
    print('construct_prompt')

    prompt = [f"<|im_start|>system\n{construct_system_message(page)}<|im_end|>"]
    if page == 'data_analyst':
        for dict_message in st.session_state['messages']:
            if dict_message['role'] == 'user':
                user_input = json.dumps({'user_input': dict_message['content']})
                prompt.append('<|im_start|>user\n' + user_input + '<|im_end|>\n')
            else:
                prompt.append('<|im_start|>assistant\n' + dict_message['content'] + '<|im_end|>\n')
    
    elif page == 'chart_builder':
        for dict_message in st.session_state['messages']:
            if dict_message['role'] == 'user':
                if 'error' not in dict_message.keys():
                    prompt.append('<|im_start|>user\n' + json.dumps(dict_message['content']) + '<|im_end|>\n')
                else:
                    prompt.append('<|im_start|>user\n' + dict_message['content'] + '<|im_end|>\n')
            else:
                prompt.append('<|im_start|>assistant\n' + dict_message['content'] + '<|im_end|>\n')

    prompt.append('<|im_start|>assistant\n')
    prompt.append('')
    return '\n'.join(prompt)

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

def generate_arctic_response(prompt_str):
        print('generate_arctic_response')
        token_count = get_num_tokens(prompt_str)
        print(token_count)

        if st.session_state['active_page'] == 'data_analyst':
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
        
        if st.session_state['active_page'] == 'chart_builder':
            error_count = 0
            for message in st.session_state['messages']:
                if 'error' in message.keys():
                    if message['role'] == 'assistant':
                        error_count += 1

            if error_count >= 3:
                st.error('Oops! Something went wrong. Try rephrasing your instructions in a different way.')
                st.form_submit_button(':red[Reset Chart Builder]', on_click=reset_chart_builder)
                if st.secrets['ENV'] == 'dev':
                    st.write(st.session_state['messages'])
                st.stop()

            if token_count >= 3072:
                st.error('Instructions too long. Please keep it under 3072 tokens.')
                st.form_submit_button(':red[Reset Chart Builder]', on_click=reset_chart_builder)
                st.stop()

        events = []
        st.session_state['prompt_str'] = prompt_str
        for event in replicate.stream('snowflake/snowflake-arctic-instruct',
                            input={'prompt': prompt_str,
                                    'prompt_template': r"{prompt}",
                                    'temperature': 0,
                                    'top_p': top_p,
                                    }):
            events.append(str(event))
        return ''.join(events)


def get_num_tokens(prompt):
    print('get_num_tokens')
    """Get the number of tokens in a given prompt"""
    tokenizer = get_tokenizer()
    tokens = tokenizer.tokenize(prompt)
    return len(tokens)

@st.cache_resource(show_spinner=False)
def get_tokenizer():
    print('get_tokenizer')
    """Get a tokenizer to make sure we're not sending too much text
    text to the Model. Eventually we will replace this with ArcticTokenizer
    """
    return AutoTokenizer.from_pretrained('huggyllama/llama-7b')