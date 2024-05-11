import streamlit as st

from utils.data_import_helpers import gather_metadata

def render_uploader(page):
    with st.form(key=f'upload_files_{page}'):
        st.caption(':blue[or upload your csv files]')
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
            st.session_state['active_page'] = page
            gather_metadata(source='upload')
            st.rerun()
