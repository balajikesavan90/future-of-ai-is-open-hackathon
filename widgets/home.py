import streamlit as st

from utils.ai_helpers import welcome_message, generate_arctic_response
from utils.data_analysis import gather_metadata

def render_home():
    if 'messages' not in st.session_state.keys() or not st.session_state['messages']:
        st.session_state['messages'] = [{'role': 'assistant', 'content': welcome_message}]      
    
    if 'vetted_files' not in st.session_state.keys():
        st.session_state['vetted_files'] = {}

    # Display or clear chat messages
    for message in st.session_state['messages']:
        with st.chat_message(message['role']):
            st.write(message['content'])

    st.session_state['uploaded_files'] = st.file_uploader(
        label="Upload Your Files in .csv format:", 
        type=['csv'],
        accept_multiple_files=True
    )

    # User-provided prompt
    if prompt := st.chat_input():
        gather_metadata()
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