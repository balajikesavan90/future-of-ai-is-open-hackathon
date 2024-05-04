import streamlit as st
import pandas as pd
import itertools

def gather_metadata():
    """
    Gather metadata from uploaded files.
    """
    vetted_files = {}
    for uploaded_file in st.session_state['uploaded_files']:
        filename = uploaded_file.name
        vetted_files[filename] = {}
        df = pd.read_csv(
            filepath_or_buffer=uploaded_file, 
            parse_dates=True,
            low_memory=False)
        df = df.convert_dtypes()
        vetted_files[filename]['columns_names'] = df.columns
        vetted_files[filename]['data_types'] = df.dtypes
        vetted_files[filename]['row_count'] = df.shape[0]
        vetted_files[filename]['primary_key'] = detect_primary_keys(df)
        vetted_files[filename]['dataframe'] = df
    
    del st.session_state['uploaded_files']
    st.session_state['vetted_files'] = vetted_files

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
        vetted_files[filename]['data_dictionary_json'] = vetted_files[filename]['data_dictionary'].to_json(orient='records')
        del st.session_state['vetted_files'][filename]['data_dictionary']

    return vetted_files
    

def check_datatypes(vetted_files):
    """
    Check data types.
    """
    for filename in vetted_files:
        for column in vetted_files[filename]['dataframe'].columns:
            if vetted_files[filename]['dataframe'][column].dtype == 'object':
                vetted_files[filename]['dataframe'][column] = vetted_files[filename]['dataframe'][column].astype('string')
            elif vetted_files[filename]['dataframe'][column].dtype == 'float64':
                vetted_files[filename]['dataframe'][column] = vetted_files[filename]['dataframe'][column].astype('Float64')
            elif vetted_files[filename]['dataframe'][column].dtype == 'int64':
                vetted_files[filename]['dataframe'][column] = vetted_files[filename]['dataframe'][column].astype('Int64')
            elif vetted_files[filename]['dataframe'][column].dtype == 'bool':
                vetted_files[filename]['dataframe'][column] = vetted_files[filename]['dataframe'][column].astype('bool')
            elif vetted_files[filename]['dataframe'][column].dtype == 'datetime64[ns]':
                vetted_files[filename]['dataframe'][column] = vetted_files[filename]['dataframe'][column].astype('datetime64[ns]')
            elif vetted_files[filename]['dataframe'][column].dtype == 'category':
                vetted_files[filename]['dataframe'][column] = vetted_files[filename]['dataframe'][column].astype('category')
    return vetted_files

def process_data_dictionaries(vetted_files):
    """
    Process data dictionaries.
    """
    vetted_files=check_datatypes(vetted_files)
    vetted_files=convert_data_dictionary_to_json(vetted_files)
    st.session_state['vetted_files'] = vetted_files
    st.session_state['data_dictionaries_loaded'] = True
