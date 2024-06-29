import streamlit as st
import replicate
from transformers import AutoTokenizer
import json

temperature = 0
top_p = 0.9

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

def construct_arctic_prompt(page):
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