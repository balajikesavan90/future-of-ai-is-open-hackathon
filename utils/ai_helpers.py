import streamlit as st
import replicate
import os
import re
from transformers import AutoTokenizer

from utils.streamlit_helpers import reset_app

os.environ['REPLICATE_API_TOKEN'] = st.secrets['REPLICATE_API_TOKEN']
temperature = 0.1
top_p = 0.9

welcome_message = f"""What kind of analytics would you like to perform?
"""

def construct_system_message():
    system_message = """You are an automated system that generates python syntax that is executed on a cloud server. 
You must generate your output in JSON format with the keys 'python_syntax' and 'commentary'.
The python version environment has the latest versions of streamlit, pandas and numpy installed.
streamlit, pandas and numpy libraries have already been imported.

Here is the metadata of the files uploaded by the user.
    """

    for filename in st.session_state['vetted_files']:
        system_message += f'\n\n{filename}:\n'
        system_message += f'Description: {st.session_state["vetted_files"][filename]["dataset_description"]}\n'
        system_message += f'Data Dictionary:\n'
        system_message += st.session_state['vetted_files'][filename]['data_dictionary_json']+'\n'
        system_message += f'The dataset has been loaded into a pandas DataFrame named {filename}\n\n'

    system_message += """The 'python_syntax' should be a single python function named 'generate_report' that takes in 0 arguments and must returns a single pandas dataframe.
The 'commentary' should be a string with your message to the user."""


    return system_message

@st.cache_resource(show_spinner=False)
def get_tokenizer():
    """Get a tokenizer to make sure we're not sending too much text
    text to the Model. Eventually we will replace this with ArcticTokenizer
    """
    return AutoTokenizer.from_pretrained('huggyllama/llama-7b')

def get_num_tokens(prompt):
    """Get the number of tokens in a given prompt"""
    tokenizer = get_tokenizer()
    tokens = tokenizer.tokenize(prompt)
    return len(tokens)

def extract_python_syntax(text):
    pattern = r'```python(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return None
    
def construct_prompt(messages):
    prompt = [f'<|im_start|>{construct_system_message()}<|im_end|>']
    for dict_message in messages:
        if dict_message['role'] == 'user':
            prompt.append('<|im_start|>user\n' + dict_message['content'] + '<|im_end|>')
        else:
            prompt.append('<|im_start|>assistant\n' + dict_message['content'] + '<|im_end|>')
    
    prompt.append('<|im_start|>assistant')
    prompt.append('')
    return '\n'.join(prompt)

# Function for generating Snowflake Arctic response
def generate_arctic_response():
    with st.spinner('Thinking...'):
        prompt_str = construct_prompt(st.session_state['messages'])
        token_count = get_num_tokens(prompt_str)
        print(token_count)
        
        if token_count >= 3072:
            st.error('Conversation length too long. Please keep it under 3072 tokens.')
            st.button('Reset', on_click=reset_app, key='reset')
            st.stop()

        events = []
        for event in replicate.stream('snowflake/snowflake-arctic-instruct',
                            input={'prompt': prompt_str,
                                    'prompt_template': r"{prompt}",
                                    'temperature': temperature,
                                    'top_p': top_p,
                                    }):
            events.append(str(event))
        return ''.join(events)