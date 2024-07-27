# import streamlit as st
# import logging

# from utils.ai_helpers import generate_debugger_response, generate_explanation_response, generate_docstring_response
# from utils.streamlit_helpers import render_ai_prompt

# def render_document_and_debug_code_widget():
#     logging.info(f'render_document_and_debug_code_widget - {st.session_state["session_id"]}')
    
#     st.session_state['model'] = st.sidebar.selectbox('Select the model:', ['llama-3.1', 'gpt-4o-mini'], index=0)
#     code_snippet_container = st.container()
#     st.session_state['output_container'] = st.container()
    
#     with code_snippet_container:
#         code_snippet = st.text_area(
#             label='Codebase',
#             placeholder='Add your code snippet here',
#             height=250,
#             label_visibility='collapsed'
#         )
#         with st.expander('Add error message (to debug code snippet)'):
#             error_message = st.text_area(
#                 label='Error Message',
#                 placeholder='Add the error message here',
#                 height=100,
#                 label_visibility='collapsed'
#             )
#             if st.button(
#                 label=':green[Debug]',
#                 use_container_width=True,
#             ):
#                 st.session_state['active_page'] = 'debugger'
#                 if code_snippet and error_message:
#                     response = generate_debugger_response(code_snippet, error_message, st.session_state['model'])
#                     with st.session_state['output_container']:
#                         st.markdown(response)
#                         st.button(
#                             label=':red[Clear]',
#                             use_container_width=True,
#                             on_click=lambda: st.session_state.pop('output_container')
#                         )
#                     render_ai_prompt()
#                 else:
#                     st.error('Please provide a code snippet and error message to debug')
#     with code_snippet_container:
#         explain_col, document_col = st.columns(2)
#         with explain_col:
#             if st.button(
#                 label=':green[Explain the code snippet]',
#                 use_container_width=True
#             ):
#                 st.session_state['active_page'] = 'explainer'
#                 if code_snippet:
#                     response = generate_explanation_response(code_snippet, st.session_state['model'])
#                     with st.session_state['output_container']:
#                         st.markdown(response)
#                         st.button(
#                             label=':red[Clear]',
#                             use_container_width=True,
#                             on_click=lambda: st.session_state.pop('output_container')
#                         )
#                     render_ai_prompt()
#                 else:
#                     st.error('Please provide a code snippet to explain')
#         with document_col:
#             if st.button(
#                 label=':green[Generate Docstrings]',
#                 use_container_width=True
#             ):
#                 st.session_state['active_page'] = 'docstrings_generator'
#                 if code_snippet:
#                     response = generate_docstring_response(code_snippet, st.session_state['model'])
#                     with st.session_state['output_container']:
#                         st.code(response)
#                         st.button(
#                             label=':red[Clear]',
#                             use_container_width=True,
#                             on_click=lambda: st.session_state.pop('output_container')
#                         )
#                     render_ai_prompt()
#                 else:
#                     st.error('Please provide a code snippet to generate docstrings')