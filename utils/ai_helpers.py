import streamlit as st
import replicate
import os
from transformers import AutoTokenizer

from utils.streamlit_helpers import reset

os.environ['REPLICATE_API_TOKEN'] = st.secrets['REPLICATE_API_TOKEN']
temperature = 0.3
top_p = 0.9

welcome_message = 'Hi. I\'m Arctic, a new, efficient, intelligent, and truly open language model created by Snowflake AI Research. Ask me anything.'

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

# Function for generating Snowflake Arctic response
def generate_arctic_response():
    with st.spinner('Thinking...'):
        prompt = []
        for dict_message in st.session_state['messages']:
            if dict_message['role'] == 'user':
                prompt.append('<|im_start|>user\n' + dict_message['content'] + '<|im_end|>')
            else:
                prompt.append('<|im_start|>assistant\n' + dict_message['content'] + '<|im_end|>')
        
        prompt.append('<|im_start|>assistant')
        prompt.append('')
        prompt_str = '\n'.join(prompt)
        
        if get_num_tokens(prompt_str) >= 3072:
            st.error('Conversation length too long. Please keep it under 3072 tokens.')
            st.button('Reset', on_click=reset, key='reset')
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