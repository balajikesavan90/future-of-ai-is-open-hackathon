import streamlit as st
import logging

from utils.streamlit_helpers import goto_data_dictionary_widget, goto_data_analysis_widget

def render_uploaded_data():
    logging.info(f'render_uploaded_data - {st.session_state["session_id"]}')
    st.divider()
    st.subheader(':blue[Uploaded Data]')
    st.toast(':blue[Data Dictionaries have been saved!]')
    st.success(':green[Make sure your data looks good especially if you changed the data types]')

    for filename in st.session_state['vetted_files']:
        df = st.session_state['vetted_files'][filename]['dataframe']
        st.subheader(f':blue[{filename}]')
        data_filter = st.selectbox(
            label='Select the number of rows to display',
            options=['First 50 rows', 'Last 50 rows', 'Random 50 rows', 'All rows'],
            key=f'{filename}_data_filter',
        )
        if data_filter == 'First 50 rows':
            df = df.head(50)
        elif data_filter == 'Last 50 rows':
            df = df.tail(50)
        elif data_filter == 'Random 50 rows':
            df = df.sample(50)
        st.dataframe(
            data=df,
            hide_index=True,
            height=250,
            use_container_width=True
        )
        st.divider()
    
    back_col, proceed_col = st.columns(2)
    with back_col:
        st.button(
            label=':red[Go Back]',
            on_click=goto_data_dictionary_widget,
            use_container_width=True
        )
    with proceed_col:
        st.button(
            label=':green[Proceed to Data Analyst]',
            on_click=goto_data_analysis_widget,
            use_container_width=True
        )