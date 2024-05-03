import streamlit as st
import pandas as pd

from utils.data_analysis import convert_data_dictionary_to_json

def render_data_dictionary_widget():
    st.write(':blue[Your files have been uploaded!]')
    uploaded_file_count = len(st.session_state['vetted_files'])
    if uploaded_file_count == 1:
        st.write(':blue[Lets create a data dictionary for your file]')
    else:
        st.write(':blue[Lets create data dictionaries for your files]')

    for filename in st.session_state['vetted_files']:
        st.divider()
        st.caption(f':blue[{filename}]')
        df = pd.DataFrame({
            'Column Name': st.session_state['vetted_files'][filename]['columns_names'],
            'Description': [None]*len(st.session_state['vetted_files'][filename]['columns_names']),
        })
        df['Primary Key'] = df['Column Name'].apply(lambda x: x in st.session_state['vetted_files'][filename]['primary_key'])
        st.session_state['vetted_files'][filename]['data_dictionary'] = st.data_editor(
            data=df,
            use_container_width=True,
            hide_index=True,
            key=filename,
            column_config={
                'Column Name': {'disabled': True},
            }
        )
    
    st.button(
        label=':green[Save Data Dictionary and Proceed to Analysis]',
        on_click=convert_data_dictionary_to_json,
        use_container_width=True,
        args=(st.session_state['vetted_files'],)
    )
