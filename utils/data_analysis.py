import streamlit as st
import pandas as pd
import itertools

def gather_metadata():
    """
    Gather metadata from uploaded files.
    """
    for uploaded_file in st.session_state['uploaded_files']:
        filename = uploaded_file.name
        st.session_state['vetted_files'][filename] = {}
        df = pd.read_csv(uploaded_file)
        st.session_state['vetted_files'][filename]['columns_names'] = df.columns
        st.session_state['vetted_files'][filename]['row_count'] = df.shape[0]
        st.session_state['vetted_files'][filename]['primary_key'] = detect_primary_keys(df)
        st.session_state['vetted_files'][filename]['dataframe'] = df
    
    del st.session_state['uploaded_files']

def detect_primary_keys(df):
    """
    Detect the primary key(s) of a pandas DataFrame.
    """
    primary_keys = []
    for column in df.columns:
        if df[column].is_unique:
            primary_keys.append(column)
    
    if not primary_keys:
        n_cols = len(df.columns)
        for r in range(2, n_cols+1):
            for columns in itertools.combinations(df.columns, r):
                if df[list(columns)].duplicated().sum() == 0:
                    primary_keys.extend(columns)
                    break
            if primary_keys:
                break

    return primary_keys

def convert_data_dictionary_to_json(vetted_files):
    """
    Convert data dictionary to JSON.
    """
    for filename in vetted_files:
        st.session_state['vetted_files'][filename]['data_dictionary_json'] = st.session_state['vetted_files'][filename]['data_dictionary'].to_json(orient='records')
        del st.session_state['vetted_files'][filename]['data_dictionary']
    
    st.session_state['data_dictionaries_loaded'] = True