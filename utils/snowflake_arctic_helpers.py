import streamlit as st
import replicate
from transformers import AutoTokenizer
import json

temperature = 0.1
top_p = 0.1

from utils.system_messages import construct_system_message
from utils.streamlit_helpers import reset_data_analyst, reset_chart_builder


def construct_arctic_prompt(page, vetted_files):
    print('construct_arctic_prompt')

    prompt = [f"<|im_start|>system\n{construct_system_message(page, vetted_files)}<|im_end|>"]
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