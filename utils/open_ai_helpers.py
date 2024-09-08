import streamlit as st
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
import tiktoken
import logging
from utils.system_messages import construct_system_message
from utils.streamlit_helpers import reset_data_analyst

client = OpenAI()
enc_gpt4 = tiktoken.encoding_for_model("gpt-4")

def token_count_message(message):
    str = ''
    for msg in message:
        if 'content'in msg:
            str = f"{str}role: {msg['role']}, message: {msg['content']}\n"
        elif 'tool_calls' in msg:
            for tool_call in msg['tool_calls']:
                str = f"{str}role: {msg['role']}, tool_call: {tool_call['function']['name']}, arguments: {tool_call['function']['arguments']}\n"
    return len(enc_gpt4.encode(str))

@retry(wait=wait_random_exponential(min=5, max=10), stop=stop_after_attempt(5))
def completion_with_backoff(**kwargs):
    logging.info(f'completion_with_backoff - {st.session_state["session_id"]}')
    return client.chat.completions.create(**kwargs)

def chatcompletion_APICall(message, temperature = 0, model='gpt-4o-mini', response_format = None, max_tokens=None, session_id=''):
    logging.info(f'chatcompletion_APICall - {st.session_state["session_id"]}')
    """
    Runs the chat completion API call
    Args:
        model: The model to use
        message: The message to send to the model
        temperature: The temperature to use
    Returns:
        The response from the API call
    """

    response = completion_with_backoff(
        model=model,
        messages=message,
        temperature = temperature,
        max_tokens=max_tokens,
        response_format = response_format,
    )
    
    content = response.choices[0].message.content
    prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens

    cost_USD = 0.15*prompt_tokens/1000000 + 0.6*completion_tokens/1000000

    # api_call_dict = {'env': st.secrets['env'], 'id': st.session_state['id'], 'page': page, 'session_id': session_id, 'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens, 'cost_USD': cost_USD, 'model': model}

    # supabase_client.table('api_calls_open_ai_chatcompletions').upsert(api_call_dict).execute()

    return [content, cost_USD]



def generate_gpt4o_mini_response(vetted_files):
    logging.info(f'generate_gpt4o_mini_response - {st.session_state["session_id"]}')

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

    response, cost = chatcompletion_APICall(prompt, model='gpt-4o-mini', temperature=0.1)
    st.session_state['prompt_str'] = ""
    for dict_message in prompt:
        st.session_state['prompt_str'] += f"role: {dict_message['role']}\ncontent: {dict_message['content']}\n--\n"
    return response