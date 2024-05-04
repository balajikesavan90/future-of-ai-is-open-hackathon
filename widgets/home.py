import streamlit as st
import pandas as pd

from widgets.uploader import render_uploader
from widgets.data_dictionary import render_data_dictionary_widget
from widgets.uploaded_data import render_uploaded_data

def setup_home():
    if 'vetted_files' not in st.session_state.keys():
        st.session_state['vetted_files'] = {}
    
    if 'data_dictionaries_loaded' not in st.session_state.keys():
        st.session_state['data_dictionaries_loaded'] = False    
    
    if 'datasets_vetted' not in st.session_state.keys():
        st.session_state['datasets_vetted'] = False

def render_home():
    # if 'messages' not in st.session_state.keys() or not st.session_state['messages']:
    #     st.session_state['messages'] = [{'role': 'assistant', 'content': welcome_message}]      

    # # Display or clear chat messages
    # for message in st.session_state['messages']:
    #     with st.chat_message(message['role']):
    #         st.write(message['content'])

    st.title(':blue[Auto Analytics]')
    st.divider()

    if st.session_state['vetted_files'] == {}:
        render_uploader()

    else:
        if not st.session_state['data_dictionaries_loaded']:
            render_data_dictionary_widget()

        else:
            if not st.session_state['datasets_vetted']:
                render_uploaded_data()
            else:
                st.write('Data have been vetted')


    # # User-provided prompt
    # if prompt := st.chat_input():
    #     gather_metadata()
    #     st.session_state['messages'].append({'role': 'user', 'content': prompt})
    #     with st.chat_message('user'):
    #         st.write(prompt)

    # # Generate a new response if last message is not from assistant
    # if st.session_state['messages'][-1]['role'] != 'assistant':
    #     with st.chat_message('assistant'):
    #         response = generate_arctic_response()
    #         st.write(response)
    #     message = {'role': 'assistant', 'content': response}
    #     st.session_state.messages.append(message)