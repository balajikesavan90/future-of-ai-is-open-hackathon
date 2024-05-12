import streamlit as st

from utils.data_import_helpers import gather_metadata

def render_sample_datasets(page):

    with st.container(border=True):
        st.write(':blue[Or select from the following sample datasets:]')
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                label=':blue[Iris Dataset]',
                use_container_width=True,
                key=f"Iris_{page}"
            ):
                st.session_state['active_page'] = page
                st.session_state['source'] = 'load_iris'
                gather_metadata()
                st.rerun()
            if st.button(
                label=':blue[Diabetes Dataset]',
                use_container_width=True,
                key=f"Diabetes_dataset_{page}"
            ):
                st.session_state['active_page'] = page
                st.session_state['source'] = 'load_diabetes'
                gather_metadata()
                st.rerun()
        with col2:
            if st.button(
                label=':blue[Wine Dataset]',
                use_container_width=True,
                key=f"wine_{page}"
            ):
                st.session_state['active_page'] = page
                st.session_state['source'] = 'load_wine'
                gather_metadata()
                st.rerun()
            if st.button(
                label=':blue[Breast Cancer Dataset]',
                use_container_width=True,
                key=f"breast_cancer_dataset_{page}"
            ):
                st.session_state['active_page'] = page
                st.session_state['source'] = 'load_breast_cancer'
                gather_metadata()
                st.rerun()