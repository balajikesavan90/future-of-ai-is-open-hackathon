import streamlit as st
import replicate
import tiktoken
import json
import logging
import requests
import os

from utils.system_messages import construct_system_message
from utils.streamlit_helpers import reset_data_analyst

enc_gpt4 = tiktoken.encoding_for_model("gpt-4")

temperature = 0.1
top_p = 0.1


def token_count_message(message):
    str = ''
    for msg in message:
        if 'content'in msg:
            str = f"{str}role: {msg['role']}, message: {msg['content']}\n"
        elif 'tool_calls' in msg:
            for tool_call in msg['tool_calls']:
                str = f"{str}role: {msg['role']}, tool_call: {tool_call['function']['name']}, arguments: {tool_call['function']['arguments']}\n"
    return len(enc_gpt4.encode(str))


class MetaLlama:
    def __init__(self):
        self.session = requests.Session()
        os.environ['REPLICATE_API_TOKEN'] = st.secrets['REPLICATE_API_TOKEN']
        enc_gpt4 = tiktoken.encoding_for_model("gpt-4")


    # def construct_llama_prompt(self, vetted_files):
    #     logging.info(f'construct_llama_prompt - {st.session_state["session_id"]}')

    #     prompt = [f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{construct_system_message(vetted_files)}<|eot_id|>"]
    #     for dict_message in st.session_state['messages']:
    #         if dict_message['role'] == 'user':
    #             user_input = json.dumps({'user_input': dict_message['content']})
    #             prompt.append('<|start_header_id|>user<|end_header_id|>\n' + user_input + '<|eot_id|>\n')
    #         else:
    #             prompt.append('<|start_header_id|>assistant<|end_header_id|>\n' + dict_message['content'] + '<|eot_id|>\n')
        
    #     prompt.append('<|start_header_id|>assistant<|end_header_id|>\n')
    #     prompt.append('')
    #     return '\n'.join(prompt)

    def generate_llama_response(self, vetted_files):
        logging.info(f'generate_llama_response - {st.session_state["session_id"]}')

        system_message = construct_system_message(vetted_files)

        prompt = [{'role': 'system', 'content': system_message}]

        for dict_message in st.session_state['messages']:
            prompt.append({'role': dict_message['role'], 'content': dict_message['content']})

        token_count = token_count_message(prompt)
        logging.info(f'token_count - {token_count} - {st.session_state["session_id"]}')

        error_count = 0
        for message in st.session_state['messages']:
            if 'error' in message.keys():
                if message['role'] == 'assistant':
                    error_count += 1
        
        if error_count >= 3:
            st.error('Oops! Something went wrong. Try rephrasing your prompt in a different way. Or try using the OpenAI model from the sidebar.')
            st.button(':red[Reset Data Analyst]', on_click=reset_data_analyst, key='reset')
            if st.secrets['ENV'] == 'dev':
                st.write(st.session_state['messages'])
            st.stop()

        if token_count >= 10000:
            st.error('Conversation length too long. Please keep it under 10000 tokens.')
            st.button(':red[Reset Data Analyst]', on_click=reset_data_analyst, key='reset')
            if st.secrets['ENV'] == 'dev':
                st.write(st.session_state['messages'])
            st.stop()
        
        events = []
        st.session_state['prompt_str'] = ""
        for dict_message in prompt:
            st.session_state['prompt_str'] += f"role: {dict_message['role']}\ncontent: {dict_message['content']}\n--\n"
        for event in replicate.stream('meta/llama-4-maverick-instruct',
                            input={'prompt': st.session_state['prompt_str'],
                                    # 'prompt_template': r"{prompt}",
                                    'temperature': 0,
                                    'top_p': top_p,
                                    }):
            events.append(str(event))
        return ''.join(events)

    def token_count_message(self, prompt_str):
        return len(enc_gpt4.encode(prompt_str))
