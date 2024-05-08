import streamlit as st

from utils.data_analysis_helpers import gather_metadata

def render_uploader():
    with st.form(key='upload_files'):
        st.write(':blue[or upload your csv files to get started!]')
        st.session_state['uploaded_files'] = st.file_uploader(
            label='Upload Your Files in .csv format:', 
            type=['csv'],
            accept_multiple_files=True,
            label_visibility='collapsed'
        )

        st.form_submit_button(
            label=':green[Lets Go!]',
            on_click=gather_metadata,
            use_container_width=True,
            args=('upload',)
        )
