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

task_identifier_system_message = """You are an automated system that identifies is the user wants to manipulate the data or generate a plot. You must returns the string 'manipulate' if the user wants to manipulate the data and 'plot' if the user wants to generate a plot."""

def construct_analyst_system_message(task):
    system_message = """You are an automated system that generates python syntax that is executed on a cloud server. 
You must generate your output in JSON format with the keys 'python_syntax' and 'commentary'.
The python version environment has the latest versions of streamlit, pandas, numpy, scikit-learn installed.
You must generate plots using the streamlit chart elements API.

Here is the metadata of the files uploaded by the user.
    """

    for filename in st.session_state['vetted_files']:
        system_message += f'\n\n{filename}:\n'
        system_message += f'Description: {st.session_state["vetted_files"][filename]["dataset_description"]}\n'
        system_message += f'Data Dictionary:\n'
        system_message += st.session_state['vetted_files'][filename]['data_dictionary_json']+'\n'
        system_message += f'Pandas Describe:\n'
        system_message += st.session_state['vetted_files'][filename]['pandas_describe_json']+'\n'
        system_message += f'First 5 rows of the dataset:\n'
        system_message += st.session_state['vetted_files'][filename]['dataframe'].head().to_json(orient='index')+'\n'
        # system_message += f'Last 5 rows of the dataset:\n'
        # system_message += st.session_state['vetted_files'][filename]['dataframe'].tail().to_json(orient='index')+'\n'
        system_message += f'The dataset has already been loaded as a pandas DataFrame named {filename}\n\n'

    if task == 'manipulate':
        system_message += "The 'python_syntax' should be a single python function named 'generate_report' that takes in 0 arguments and must return a single pandas DataFrame.\n\n"
    elif task == 'plot':
        system_message += "The 'python_syntax' should be a single python function named 'generate_report' that takes in 0 arguments generates plots using the streamlit chart API elements with appropriate subheaders. The function must return None.\n\n"
    system_message += "The 'commentary' should be a string with your message to the user."

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

def identify_task(text):
    with st.spinner('Thinking...'):
        prompt = [f'<|im_start|>{task_identifier_system_message}<|im_end|>']
        prompt.append('<|im_start|>user\n' + text + '<|im_end|>')
        prompt.append('<|im_start|>assistant')
        prompt.append('')
        prompt_str = '\n'.join(prompt)
        if get_num_tokens(prompt_str) >= 3072:
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
    

def extract_python_syntax(text):
    pattern = r'```python(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return None

def extract_commentary(text):
    pattern = r'```python.*?```'
    commentary = re.sub(pattern, '', text, flags=re.DOTALL)
    return commentary.strip()
    
def construct_prompt(messages):
    if 'error' not in messages[-1]:
        task = identify_task(messages[-1]['content'])
        if 'plot' in task:
            st.session_state['task'] = 'plot'
            prompt = [f"<|im_start|>{construct_analyst_system_message('plot')}<|im_end|>"]
        else:
            st.session_state['task'] = 'manipulate'
            prompt = [f"<|im_start|>{construct_analyst_system_message('manipulate')}<|im_end|>"]
    else:
        prompt = [f"<|im_start|>{construct_analyst_system_message(st.session_state['task'])}<|im_end|>"]
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
    with st.spinner('Generating Python Syntax...'):
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