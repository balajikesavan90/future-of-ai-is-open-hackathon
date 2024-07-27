import streamlit as st
import replicate
from transformers import AutoTokenizer
import json

from utils.system_messages import construct_system_message
from utils.streamlit_helpers import reset_data_analyst

temperature = 0.1
top_p = 0.1

def construct_llama_prompt(vetted_files):
    print('construct_llama_prompt')

    prompt = [f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{construct_system_message(vetted_files)}<|eot_id|>"]
    for dict_message in st.session_state['messages']:
        if dict_message['role'] == 'user':
            user_input = json.dumps({'user_input': dict_message['content']})
            prompt.append('<|start_header_id|>user<|end_header_id|>\n' + user_input + '<|eot_id|>\n')
        else:
            prompt.append('<|start_header_id|>assistant<|end_header_id|>\n' + dict_message['content'] + '<|eot_id|>\n')
    
    prompt.append('<|start_header_id|>assistant<|end_header_id|>\n')
    prompt.append('')
    return '\n'.join(prompt)

def generate_llama_response(prompt_str):
        print('generate_llama_response')
        token_count = get_num_tokens(prompt_str)
        print(token_count)

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
        
        events = []
        st.session_state['prompt_str'] = prompt_str
        for event in replicate.stream('meta/meta-llama-3.1-405b-instruct',
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