import streamlit as st

from utils.data_analysis import gather_metadata

def render_uploader():
        st.subheader(':blue[Auto Analytics is your one stop shop for all your data analysis needs!]')
        st.write(':blue[Upload your csv files to get started!]')

        st.session_state['uploaded_files'] = st.file_uploader(
            label='Upload Your Files in .csv format:', 
            type=['csv'],
            accept_multiple_files=True,
            label_visibility='collapsed'
        )

        st.button(
            label=':green[Lets Go!]',
            on_click=gather_metadata,
            use_container_width=True
        )
