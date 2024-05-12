import streamlit as st
import pandas as pd

from utils.data_import_helpers import process_data_dictionaries

def render_data_dictionary_widget():
    if st.session_state['active_page'] == 'data_analyst':
        st.subheader(':blue[Data Analyst]')
    elif st.session_state['active_page'] == 'chart_builder':
        st.subheader(':blue[Chart Builder]')
    uploaded_file_count = len(st.session_state['vetted_files'])
    if uploaded_file_count == 1:
        st.toast(':green[Lets create a data dictionary for your file]')
    else:
        st.toast(':green[Lets create data dictionaries for your files]')
    st.toast(':blue[Your files have been uploaded!]')

    st.divider()
    for filename in st.session_state['vetted_files']:
        df = pd.DataFrame({
            'Column Name': st.session_state['vetted_files'][filename]['columns_names'],
            'Data Type': st.session_state['vetted_files'][filename]['data_types']
        })
        df['Data Type'] = df['Data Type'].astype(str)
        df['Primary Key'] = df['Column Name'].apply(lambda x: x in st.session_state['vetted_files'][filename]['primary_key'])
        df['Description'] = df['Column Name']
        df = df[['Primary Key', 'Column Name', 'Data Type', 'Description']]

        st.subheader(f':blue[{filename}]')
        with st.expander('See uploaded Dataset'):
            st.dataframe(st.session_state['vetted_files'][filename]['dataframe'], use_container_width=True)
        if st.session_state['source'] in (['snowflake', 'uploader']):
            value = ''
        else:
            value = st.session_state['vetted_files'][filename]['dataset_description']
        st.session_state['vetted_files'][filename]['dataset_description'] = st.text_input(
            label='Dataset Description:',
            placeholder='Enter a description for the dataset',
            key=f'{filename}_dataset_description',
            label_visibility='collapsed',
            value=value,
        )
        st.session_state['vetted_files'][filename]['data_dictionary'] = st.data_editor(
            data=df,
            use_container_width=True,
            hide_index=True,
            key=filename,
            height=250,
            column_config={
                'Column Name': {'disabled': True},
                'Data Type': st.column_config.SelectboxColumn(
                    label='Data Type',
                    help='Select the data type for the column.',
                    required=True,
                    options=['Int64', 'Float64', 'datetime64[ns]', 'string', 'bool', 'category', 'object'],
                ),
                'Primary Key': st.column_config.CheckboxColumn(
                    label='Primary Key',
                    help='Check if the column is a primary key.',
                ),
            }
        )
        st.divider()
    
    st.button(
        label=':green[Save Data Dictionary and Proceed to Analysis]',
        on_click=process_data_dictionaries,
        use_container_width=True,
        args=(st.session_state['vetted_files'],st.session_state['active_page'])
    )
