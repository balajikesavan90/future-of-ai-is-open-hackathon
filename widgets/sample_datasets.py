import streamlit as st

from utils.data_import_helpers import gather_metadata

def render_sample_datasets(page):

    with st.container(border=True):
        st.write(':blue[Or select from the following sample datasets:]')
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                label=':blue[Tips Dataset]',
                use_container_width=True,
                key=f"tips_{page}"
            ):
                st.session_state['active_page'] = page
                st.session_state['source'] = 'tips'
                gather_metadata()
                st.rerun()

            if st.button(
                label=':blue[Planets Dataset]',
                use_container_width=True,
                key=f"Planets_{page}"
            ):
                st.session_state['active_page'] = page
                st.session_state['source'] = 'planets'
                gather_metadata()
                st.rerun()
            
            if st.button(
                label=':blue[Penguins Dataset]',
                use_container_width=True,
                key=f"penguins_{page}"
            ):
                st.session_state['active_page'] = page
                st.session_state['source'] = 'penguins'
                gather_metadata()
                st.rerun()
        with col2:
            if st.button(
                label=':blue[Car Crashes Dataset]',
                use_container_width=True,
                key=f"car_crashes_{page}"
            ):
                st.session_state['active_page'] = page
                st.session_state['source'] = 'car_crashes'
                gather_metadata()
                st.rerun()
            if st.button(
                label=':blue[Diamonds Dataset]',
                use_container_width=True,
                key=f"diamonds_{page}"
            ):
                st.session_state['active_page'] = page
                st.session_state['source'] = 'diamonds'
                gather_metadata()
                st.rerun()
            if st.button(
                label=':blue[MPG]',
                use_container_width=True,
                key=f"mpg_{page}"
            ):
                st.session_state['active_page'] = page
                st.session_state['source'] = 'mpg'
                gather_metadata()
                st.rerun()