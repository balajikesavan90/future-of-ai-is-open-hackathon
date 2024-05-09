import streamlit as st

from utils.ai_helpers import generate_explanation_response, generate_documentation_response

def render_create_documentation():
    
    code_snippet_col, output_col = st.columns(2)

    with code_snippet_col:
        code_snippet = st.text_area(
            label='Codebase',
            placeholder='Add your code snippet here',
            height=250,
            label_visibility='collapsed'
        )
        with st.expander('Add Error Message'):
            st.text_area(
                label='Error Message',
                placeholder='Add the error message here',
                height=100,
                key='error_message'
            )
    with output_col:
        st.session_state['output_container'] = st.container()

    with code_snippet_col:
        explain_col, document_col = st.columns(2)
        with explain_col:
            if st.button(
                label=':green[Explain the code snippet]',
                use_container_width=True
            ):
                response = generate_explanation_response(code_snippet)
                with st.session_state['output_container']:
                    st.markdown(response)
                    st.button(
                        label=':red[Clear]',
                        use_container_width=True,
                        on_click=lambda: st.session_state.pop('output_container')
                    )
        with document_col:
            if st.button(
                label=':blue[Generate Docstrings]',
                use_container_width=True
            ):
                response = generate_documentation_response(code_snippet)
                with st.session_state['output_container']:
                    st.code(response)
                    st.button(
                        label=':red[Clear]',
                        use_container_width=True,
                        on_click=lambda: st.session_state.pop('output_container')
                    )
