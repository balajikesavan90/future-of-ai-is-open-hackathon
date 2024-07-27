import streamlit as st
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

from utils.system_messages import construct_system_message
# from utils.streamlit_helpers import reset_data_analyst, reset_chart_builder

client = OpenAI()

@retry(wait=wait_random_exponential(min=5, max=10), stop=stop_after_attempt(5))
def completion_with_backoff(**kwargs):
    print('completion_with_backoff')
    return client.chat.completions.create(**kwargs)

def chatcompletion_APICall(message, temperature = 0, model='gpt-4o-mini', response_format = None, max_tokens=None, session_id=''):
    print('chatcompletion_APICall')
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



def generate_gpt4o_mini_response(page, vetted_files):
    print('generate_gpt4o_mini_response')

    system_message = construct_system_message(page, vetted_files)

    message = [{'role': 'system', 'content': system_message}]

    for dict_message in st.session_state['messages']:
        message.append({'role': dict_message['role'], 'content': dict_message['content']})

    response, cost = chatcompletion_APICall(message, model='gpt-4o-mini', temperature=0.1)
    st.session_state['prompt_str'] = ""
    for dict_message in message:
        st.session_state['prompt_str'] += f"role: {dict_message['role']}\ncontent: {dict_message['content']}\n--\n"
    return response