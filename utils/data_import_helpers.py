import streamlit as st
import pandas as pd
import numpy as np
import itertools
import os
import snowflake.connector
# from sklearn.datasets import load_iris, load_diabetes, load_wine, load_breast_cancer
from seaborn import load_dataset

def gather_metadata(params=None):
    """
    Gather metadata from uploaded files.
    """
    vetted_files = {}
    if st.session_state['source'] == 'uploader':
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
            vetted_files[filename]['primary_key'] = []
            vetted_files[filename]['dataframe'] = df
    
    if st.session_state['source'] == 'snowflake':
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
        vetted_files[filename]['primary_key'] = []
        vetted_files[filename]['dataframe'] = df
    
    else:
        if st.session_state['source'] == 'tips':
            df = load_dataset('tips')
            filename = 'tips'
            vetted_files[filename] = {}
            vetted_files[filename]['dataset_description'] = 'This dataset contains data on tips given to waitstaff at a restaurant.'
        elif st.session_state['source'] == 'planets':
            df = load_dataset('planets')
            filename = 'planets'
            vetted_files[filename] = {}
            vetted_files[filename]['dataset_description'] = 'This dataset contains data on planets discovered outside of our solar system.'
        elif st.session_state['source'] == 'penguins':
            df = load_dataset('penguins')
            filename = 'penquins'
            vetted_files[filename] = {}
            vetted_files[filename]['dataset_description'] = 'This dataset contains data on penguins in the Palmer Archipelago, Antarctica.'
        elif st.session_state['source'] == 'car_crashes':
            df = load_dataset('car_crashes')
            filename = 'car_crashes'
            vetted_files[filename] = {}
            vetted_files[filename]['dataset_description'] = 'This dataset contains data on car crashes in the United States.'
        elif st.session_state['source'] == 'diamonds':
            df = load_dataset('diamonds')
            filename = 'diamonds'
            vetted_files[filename] = {}
            vetted_files[filename]['dataset_description'] = 'This dataset contains data on diamonds.'
        elif st.session_state['source'] == 'mpg':
            df = load_dataset('mpg')
            filename = 'mpg'
            vetted_files[filename] = {}
            vetted_files[filename]['dataset_description'] = 'This dataset contains data on fuel economy for cars.'

        df = df.convert_dtypes()
        vetted_files[filename]['columns_names'] = df.columns
        vetted_files[filename]['data_types'] = df.dtypes
        vetted_files[filename]['pandas_describe'] = df.describe(include='all')
        vetted_files[filename]['primary_key'] = []
        vetted_files[filename]['dataframe'] = df
    
    st.session_state['vetted_files'] = vetted_files

# Function is too slow for larger datasets. Need to optimize. Not being used currently.
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

def process_data_dictionaries(vetted_files, page):
    """
    Process data dictionaries.
    """
    vetted_files=check_datatypes(vetted_files)
    vetted_files=convert_data_dictionary_to_json(vetted_files)
    st.session_state['active_page'] = page
    st.session_state['vetted_files'] = vetted_files
    st.session_state['data_dictionaries_loaded'] = True