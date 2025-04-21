import streamlit as st
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
import tiktoken
import logging

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
    return client.beta.chat.completions.parse(**kwargs)

def chatcompletion_APICall(message, temperature = 0, model='gpt-4.1-mini-2025-04-14', response_format = None, max_tokens=None, session_id=''):
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

    cost_USD = 0.1*prompt_tokens/1000000 + 0.4*completion_tokens/1000000
    logging.info(f'cost_USD - {cost_USD} - {st.session_state["session_id"]}')

    # api_call_dict = {'env': st.secrets['env'], 'id': st.session_state['id'], 'page': page, 'session_id': session_id, 'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens, 'cost_USD': cost_USD, 'model': model}

    # supabase_client.table('api_calls_open_ai_chatcompletions').upsert(api_call_dict).execute()

    return [content, cost_USD]



