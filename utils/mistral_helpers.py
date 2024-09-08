# import streamlit as st
# import replicate
# from transformers import AutoTokenizer
# import json
# import logging

# from utils.system_messages import construct_system_message
# from utils.streamlit_helpers import reset_data_analyst

# temperature = 0.1
# top_p = 0.1

# def construct_mistral_prompt(vetted_files):
#     logging.info(f'construct_mistral_prompt - {st.session_state["session_id"]}')

#     prompt = [f"<s>[INST]{construct_system_message(vetted_files)}[/INST]\n"]
#     for dict_message in st.session_state['messages'][:-1]:
#         if dict_message['role'] == 'user':
#             user_input = json.dumps({'user_input': dict_message['content']})
#             prompt.append('[INST]' + user_input + '[/INST]\n')
#         else:
#             prompt.append(dict_message['content'] + '\n')
#     prompt.append('</s>\n')
#     last_message = st.session_state['messages'][-1]
#     user_input = json.dumps({'user_input': last_message['content']})
#     prompt.append('[INST]' + user_input + '[/INST]\n')

#     return '\n'.join(prompt)

# def generate_mistral_response(prompt_str):
#         logging.info(f'generate_mistral_response - {st.session_state["session_id"]}')
#         token_count = get_num_tokens(prompt_str)
#         logging.info(f'token_count - {token_count} - {st.session_state["session_id"]}')

#         error_count = 0
#         for message in st.session_state['messages']:
#             if 'error' in message.keys():
#                 if message['role'] == 'assistant':
#                     error_count += 1
        
#         if error_count >= 3:
#             st.error('Oops! Something went wrong. Try rephrasing your prompt in a different way.')
#             st.button(':red[Reset Data Analyst]', on_click=reset_data_analyst, key='reset')
#             if st.secrets['ENV'] == 'dev':
#                 st.write(st.session_state['messages'])
#             st.stop()

#         if token_count >= 3072:
#             st.error('Conversation length too long. Please keep it under 3072 tokens.')
#             st.button(':red[Reset Data Analyst]', on_click=reset_data_analyst, key='reset')
#             if st.secrets['ENV'] == 'dev':
#                 st.write(st.session_state['messages'])
#             st.stop()
        
#         events = []
#         st.session_state['prompt_str'] = prompt_str
#         for event in replicate.stream('mistralai/mixtral-8x7b-instruct-v0.1',
#                             input={'prompt': prompt_str,
#                                     'temperature': 0.1,
#                                     'top_p': 0.1,
#                                     'max_tokens': 1024,
#                                     'length_penalty': 3,
#                                     }):
#             events.append(str(event))
#         return ''.join(events)



# def get_num_tokens(prompt):
#     """Get the number of tokens in a given prompt"""
#     tokenizer = get_tokenizer()
#     tokens = tokenizer.tokenize(prompt)
#     return len(tokens)

# @st.cache_resource(show_spinner=False)
# def get_tokenizer():
#     logging.info(f'get_tokenizer - {st.session_state["session_id"]}')
#     """Get a tokenizer to make sure we're not sending too much text
#     text to the Model. Eventually we will replace this with ArcticTokenizer
#     """
#     return AutoTokenizer.from_pretrained('huggyllama/llama-7b')