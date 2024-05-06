import streamlit as st
import pandas as pd
import itertools
import os
import snowflake.connector

def gather_metadata(source, params=None):
    """
    Gather metadata from uploaded files.
    """
    vetted_files = {}
    if source == 'upload':
        for uploaded_file in st.session_state['uploaded_files']:
            filename, _ = os.path.splitext(uploaded_file.name)
            filename = filename.replace(' ', '_').replace('-', '_').lower()
            vetted_files[filename] = {}
            df = pd.read_csv(
                filepath_or_buffer=uploaded_file, 
                parse_dates=True,
                low_memory=False)
            df = df.convert_dtypes()
            vetted_files[filename]['columns_names'] = df.columns
            vetted_files[filename]['data_types'] = df.dtypes
            vetted_files[filename]['pandas_describe'] = df.describe(include='all')
            vetted_files[filename]['primary_key'] = detect_primary_keys(df)
            vetted_files[filename]['dataframe'] = df
    
    if source == 'snowflake':
        con = snowflake.connector.connect(
            user=params['username'],
            password=params['password'],
            account=params['account'],
            warehouse=params['warehouse'],
            database=params['database'],
            schema=params['schema']
        )
        cur = con.cursor()
        cur.execute(params['sql'])
        df = cur.fetch_pandas_all()
        filename = 'snowflake_data'
        df = df.convert_dtypes()
        vetted_files = {}
        vetted_files[filename] = {}
        vetted_files[filename]['columns_names'] = df.columns
        vetted_files[filename]['data_types'] = df.dtypes
        vetted_files[filename]['pandas_describe'] = df.describe(include='all')
        vetted_files[filename]['primary_key'] = detect_primary_keys(df)
        vetted_files[filename]['dataframe'] = df
    
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
        vetted_files[filename]['data_dictionary_json'] = vetted_files[filename]['data_dictionary'].to_json(orient='index')
        del st.session_state['vetted_files'][filename]['data_dictionary']

    return vetted_files

def check_datatypes(vetted_files):
    """
    Check data types.
    """
    for filename in vetted_files:
        vetted_files[filename]['data_dictionary'] = pd.DataFrame(vetted_files[filename]['data_dictionary'])
        for column in vetted_files[filename]['data_dictionary']['Column Name']:

            if vetted_files[filename]['data_dictionary'].loc[column]['Data Type'] == 'object':
                vetted_files[filename]['dataframe'][column] = vetted_files[filename]['dataframe'][column].astype('string')

            elif vetted_files[filename]['data_dictionary'].loc[column]['Data Type'] == 'float64':
                vetted_files[filename]['dataframe'][column] = vetted_files[filename]['dataframe'][column].astype('Float64')

            elif vetted_files[filename]['data_dictionary'].loc[column]['Data Type'] == 'int64':
                vetted_files[filename]['dataframe'][column] = vetted_files[filename]['dataframe'][column].astype('Int64')

            elif vetted_files[filename]['data_dictionary'].loc[column]['Data Type'] == 'datetime64[ns]':
                vetted_files[filename]['dataframe'][column] = pd.to_datetime(vetted_files[filename]['dataframe'][column])

            elif vetted_files[filename]['data_dictionary'].loc[column]['Data Type'] == 'bool':
                vetted_files[filename]['dataframe'][column] = vetted_files[filename]['dataframe'][column].astype('bool')

            elif vetted_files[filename]['data_dictionary'].loc[column]['Data Type'] == 'category':
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