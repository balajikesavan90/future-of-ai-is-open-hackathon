import streamlit as st
import replicate
import os
import re
from transformers import AutoTokenizer

from utils.streamlit_helpers import reset_app

os.environ['REPLICATE_API_TOKEN'] = st.secrets['REPLICATE_API_TOKEN']
temperature = 0
top_p = 0.9

welcome_message = f"""Hello! I am the Arctic Analytics AI. I can help you analyze your data and generate plots.
"""

task_identifier_system_message = """You are an automated system that detects if the task requested by the user.
You must generate one of these outputs: 'manipulate', 'plot', or 'consult'.
1. 'manipulate' if the user's request can be fulfilled by generating a pandas DataFrame.
2. 'plot' if the user's request can be fulfilled by generating a plot.
3. 'consult' if the user's request is a question that requires a text response.
"""

generate_explanation_system_message = """You are an automated system that explains the computer code inputted by the user.
You must explain the code in a way that is easy to understand for a non-technical audience.
You must explain the purpose of the code, the logic behind the code, and the expected output of the code.
You must use simple language and avoid technical jargon.
You must generate your output in bullet points with short sentences.
Your output must be in github markdown format.
"""

generate_documentation_system_message = """You are an automated system that generates comments and docstrings for the computer code inputted by the user.
Your output must be a version of the user's code with comments and docstrings added.
The doc strings must include the function name, the purpose of the function, and the input and output parameters.
The comments must explain the logic and reasoning behind the code.
You must include comments for each line of code.
The comments must be written in a way that is easy to understand for someone who is not familiar with the code.
"""

def construct_arctic_analyst_system_message(task):
    system_message = """You are an automated system that generates python syntax that is executed on a cloud server. 
The python virtual environment has the latest versions of streamlit, pandas, numpy, scikit-learn installed.

You must always generate your output in JSON format with the keys 'python_syntax' and 'commentary'. 
This is a very serious requirement for all of your responses. 
    """

    if task in ['manipulate', 'consult']:
        system_message += """The 'python_syntax' should be a single python function named 'generate_report' that takes in 0 arguments. 
The 'generate_report' function must return a single pandas DataFrame. 
This is a very serious requirement for all of your responses.\n\n"""
    elif task == 'plot':
        system_message += """The 'python_syntax' should be a single python function named 'generate_report' that takes in 0 arguments. 
The 'generate_report' function must generate plots using the streamlit chart API elements with appropriate subheaders. 
The 'generate_report' function must return None. 
This is a very serious requirement for all of your responses.\n\n"""
    
    system_message += """The 'commentary should be a string with your message to the user. 
In the commentary you must explain your thought process to the user. 
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
        system_message += f'The dataset has already been loaded as a pandas DataFrame named {filename}\n\n'

    return system_message

def generate_arctic_analyst_response():
    with st.spinner('Generating Python Syntax...'):
        prompt_str = construct_arctic_analyst_prompt(st.session_state['messages'])
        return generate_arctic_response(prompt_str)
    
def construct_arctic_analyst_prompt(messages):
    if 'error' not in messages[-1]:
        task = identify_task(messages[-1]['content'])

        if any(x in task for x in ['plot', '2']):
            st.session_state['task'] = 'plot'
            prompt = [f"<|im_start|>system\n{construct_arctic_analyst_system_message('plot')}<|im_end|>"]

        elif any(x in task for x in ['manipulate', '1']):
            st.session_state['task'] = 'manipulate'
            prompt = [f"<|im_start|>system\n{construct_arctic_analyst_system_message('manipulate')}<|im_end|>"]

        elif any(x in task for x in ['consult', '3']):
            st.session_state['task'] = 'consult'
            prompt = [f"<|im_start|>system\n{construct_arctic_analyst_system_message('consult')}<|im_end|>"]

        else:
            st.session_state['task'] = 'consult'
            prompt = [f"<|im_start|>system\n{construct_arctic_analyst_system_message('consult')}<|im_end|>"]

    else:
        prompt = [f"<|im_start|>system\n{construct_arctic_analyst_system_message(st.session_state['task'])}<|im_end|>"]

    for dict_message in messages:
        if dict_message['role'] == 'user':
            prompt.append('<|im_start|>user\n' + dict_message['content'] + '<|im_end|>')
        else:
            prompt.append('<|im_start|>assistant\n' + dict_message['content'] + '<|im_end|>')
    
    prompt.append('<|im_start|>assistant')
    prompt.append('')
    return '\n'.join(prompt)

def identify_task(text):
    with st.spinner('Thinking...'):
        prompt = [f'<|im_start|>system\n{task_identifier_system_message}<|im_end|>']
        prompt.append('<|im_start|>user\n' + text + '<|im_end|>')
        prompt.append('<|im_start|>assistant')
        prompt.append('')
        prompt_str = '\n'.join(prompt)
        return generate_arctic_response(prompt_str)

def generate_explanation_response():
    with st.session_state['output_container']:
        with st.spinner('Generating Explanation...'):
            prompt = [f"<|im_start|>system\n{generate_explanation_system_message}<|im_end|>"]
            prompt.append('<|im_start|>user\n' + st.session_state['code_snippet'] + '<|im_end|>')
            prompt.append('<|im_start|>assistant')
            prompt.append('')
            prompt_str = '\n'.join(prompt)
            return generate_arctic_response(prompt_str)
    
def generate_documentation_response():
    with st.session_state['output_container']:
        with st.spinner('Generating Documentation...'):
            prompt = [f"<|im_start|>system\n{generate_documentation_system_message}<|im_end|>"]
            prompt.append('<|im_start|>user\n' + st.session_state['code_snippet'] + '<|im_end|>')
            prompt.append('<|im_start|>assistant')
            prompt.append('')
            prompt_str = '\n'.join(prompt)
            return generate_arctic_response(prompt_str)

def generate_arctic_response(prompt_str):
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
                                    'temperature': 0,
                                    'top_p': top_p,
                                    }):
            events.append(str(event))
        return ''.join(events)


def get_num_tokens(prompt):
    """Get the number of tokens in a given prompt"""
    tokenizer = get_tokenizer()
    tokens = tokenizer.tokenize(prompt)
    return len(tokens)

@st.cache_resource(show_spinner=False)
def get_tokenizer():
    """Get a tokenizer to make sure we're not sending too much text
    text to the Model. Eventually we will replace this with ArcticTokenizer
    """
    return AutoTokenizer.from_pretrained('huggyllama/llama-7b')

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