import streamlit as st

from utils.ai_helpers import welcome_message
from utils.ai_helpers import generate_arctic_response

def render_home():
    if 'messages' not in st.session_state.keys() or not st.session_state['messages']:
        st.session_state['messages'] = [{'role': 'assistant', 'content': welcome_message}]      
          
    # Display or clear chat messages
    for message in st.session_state['messages']:
        with st.chat_message(message['role']):
            st.write(message['content'])

    # User-provided prompt
    if prompt := st.chat_input():
        st.session_state['messages'].append({'role': 'user', 'content': prompt})
        with st.chat_message('user'):
            st.write(prompt)

    # Generate a new response if last message is not from assistant
    if st.session_state['messages'][-1]['role'] != 'assistant':
        with st.chat_message('assistant'):
            response = generate_arctic_response()
            st.write(response)
        message = {'role': 'assistant', 'content': response}
        st.session_state.messages.append(message)