import streamlit as st
import logging

from utils.data_import_helpers import gather_metadata

def render_uploader():
    logging.info(f'render_uploader - {st.session_state["session_id"]}')
    with st.form(key=f'upload_files'):
        st.caption('📁:blue[or upload your own csv files]')
        st.session_state['uploaded_files'] = st.file_uploader(
            label='Upload Your Files in .csv format:', 
            type=['csv'],
            accept_multiple_files=True,
            label_visibility='collapsed'
        )

        if st.form_submit_button(
            label=':green[Lets Go!]',
            use_container_width=True,
        ):
            st.session_state['source'] = 'uploader'
            gather_metadata()
            st.rerun()
