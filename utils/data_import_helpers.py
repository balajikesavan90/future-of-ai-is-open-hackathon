import streamlit as st
import pandas as pd
import itertools
import os
import snowflake.connector
from sklearn.datasets import load_iris, load_diabetes, load_wine, load_breast_cancer

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
        if st.session_state['source'] == 'load_iris':
            df = pd.DataFrame(load_iris().data, columns=load_iris().feature_names)
            filename = 'iris_data'
            vetted_files[filename] = {}
            vetted_files[filename]['dataset_description'] = 'The dataset contains 150 samples from each of three species of Iris flowers (Iris setosa, Iris virginica, and Iris versicolor), with four features measured from each sample: the lengths and the widths of the sepals and petals.'
        elif st.session_state['source'] == 'load_diabetes':
            df = pd.DataFrame(load_diabetes().data, columns=load_diabetes().feature_names)
            filename = 'diabetes_data'
            vetted_files[filename] = {}
            vetted_files[filename]['dataset_description'] = 'Dataset consists of 442 patients, each characterized by 10 baseline variables: age, sex, body mass index, average blood pressure, and six blood serum measurements.'
        elif st.session_state['source'] == 'load_wine':
            df = pd.DataFrame(load_wine().data, columns=load_wine().feature_names)
            filename = 'wine_data'
            vetted_files[filename] = {}
            vetted_files[filename]['dataset_description'] = 'The data is the results of a chemical analysis of wines grown in the same region in Italy but derived from three different cultivars.'
        elif st.session_state['source'] == 'load_breast_cancer':
            df = pd.DataFrame(load_breast_cancer().data, columns=load_breast_cancer().feature_names)
            filename = 'breast_cancer_data'
            vetted_files[filename] = {}
            vetted_files[filename]['dataset_description'] = 'The data contains 569 samples of malignant and benign tumor cells. The first two columns in the dataset store the unique ID numbers of the samples and the corresponding diagnosis (M=malignant, B=benign), respectively.'

        df = df.convert_dtypes()
        vetted_files[filename]['columns_names'] = df.columns
        print(df.dtypes)
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