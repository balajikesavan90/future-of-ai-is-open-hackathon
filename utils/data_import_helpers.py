import streamlit as st
import pandas as pd
import numpy as np
import itertools
import os
import snowflake.connector
# from sklearn.datasets import load_iris, load_diabetes, load_wine, load_breast_cancer
from seaborn import load_dataset
import logging

datasets = {
    'tips': {
        'description': 'This dataset contains data on tips given to waitstaff at a restaurant.',
        'column_descriptions': {
            'total_bill': 'The total bill for the meal.',
            'tip': 'The tip given to the waitstaff.',
            'sex': 'The gender of the person paying the bill',
            'smoker': 'Indicates whether the person was smoking or not',
            'day': 'The day of the week the meal took place.',
            'time': 'The time of day, either Dinner or Lunch.',
            'size': 'The size of the party.'
        }
    },
    'planets': {
        'description': 'This dataset contains data on planets discovered outside of our solar system.',
        'column_descriptions': {
            'method': 'The method used to discover the planet.',
            'number': 'The number of planets in the planetary system',
            'orbital_period': 'The orbital period of the planet in days.',
            'mass': 'The mass of the planet in Jupiter masses.',
            'distance': 'The distance from the planet to its star in parsecs.',
            'year': 'The year the planet was discovered.'
        }
    },
    'penguins': {
        'description': 'This dataset contains data on penguins in the Palmer Archipelago, Antarctica.',
        'column_descriptions': {
            'species': 'The species of penguin.',
            'island': 'The island where the penguin was observed.',
            'bill_length_mm': 'The length of the penguin\'s bill in millimeters.',
            'bill_depth_mm': 'The depth of the penguin\'s bill in millimeters.',
            'flipper_length_mm': 'The length of the penguin\'s flipper in millimeters.',
            'body_mass_g': 'The body mass of the penguin in grams.',
            'sex': 'The sex of the penguin.',
        },
    },
    'car_crashes': {
        'description': 'This dataset contains statistics about car crashes in different US states.',
        'column_descriptions': {
            'total': 'Total number of fatal collisions per billion miles.',
            'speeding': 'Percentage of collisions that involved speeding.',
            'alcohol': 'Percentage of collisions that involved alcohol.',
            'not_distracted': ' Percentage of collisions that were not caused by a distraction.',
            'no_previous': ' Percentage of collisions where the driver had no previous accidents.',
            'ins_premium': 'The average insurance premium in the state.',
            'ins_losses': 'The average insurance losses in the state.',
            'abbrev': 'The state abbreviation.'
        }
    },
    'diamonds': {
        'description': 'This dataset contains data on diamonds.',
        'column_descriptions': {
            'carat': 'Weight of the diamond measured in carats.',
            'cut': 'The quality of the cut.',
            'color': 'The color of the diamond, from J (worst) to D (best)',
            'clarity': 'A measurement of how clear the diamond is (I1 (worst), SI2, SI1, VS2, VS1, VVS2, VVS1, IF (best))',
            'depth': 'Total depth percentage.',
            'table': 'The width of the diamond\'s top relative to its widest point, measured as a percentage.',
            'price': 'The price of the diamond.',
            'x': 'The length of the diamond in mm.',
            'y': 'The width of the diamond in mm.',
            'z': 'The depth of the diamond in mm.'
        }
    },
    'mpg': {
        'description': 'This dataset contains data on fuel economy for cars.',
        'column_descriptions': {
            'mpg': 'Miles per gallon, representing the fuel efficiency of the car.',
            'cylinders': 'The number of cylinders in the engine.',
            'displacement': 'The engine displacement in cubic inches.',
            'horsepower': 'The engine horsepower.',
            'weight': 'The weight of the car.',
            'acceleration': 'The time it takes for the car to accelerate from 0 to 60 mph.',
            'model_year': 'The model year of the car.',
            'origin': 'Region where the car was manufactured.',
            'name': 'The name of the car.'
        }
    }
}

def gather_metadata(params=None):
    logging.info(f'gather_metadata - {st.session_state["session_id"]}')
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
    
    if st.session_state['source'] in ['tips', 'planets', 'penguins', 'car_crashes', 'diamonds', 'mpg']:
        filename = st.session_state['source']
        df = load_dataset(filename)
        df = df.convert_dtypes()
        vetted_files[filename] = {}
        vetted_files[filename]['dataset_description'] = datasets[st.session_state['source']]['description']

        vetted_files[filename]['columns_names'] = df.columns
        vetted_files[filename]['data_types'] = df.dtypes
        vetted_files[filename]['pandas_describe'] = df.describe(include='all')
        vetted_files[filename]['primary_key'] = []
        vetted_files[filename]['dataframe'] = df
    
    st.session_state['vetted_files'] = vetted_files

# Function is too slow for larger datasets. Need to optimize. Not being used currently.
def detect_primary_keys(df):
    logging.info(f'detect_primary_keys - {st.session_state["session_id"]}')
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
    logging.info(f'convert_data_dictionary_to_json - {st.session_state["session_id"]}')
    """
    Convert data dictionary to JSON.
    """
    for filename in vetted_files:
        vetted_files[filename]['data_dictionary_json'] = vetted_files[filename]['data_dictionary'].to_json(orient='index')
        del st.session_state['vetted_files'][filename]['data_dictionary']

    return vetted_files

def check_datatypes(vetted_files):
    logging.info(f'check_datatypes - {st.session_state["session_id"]}')
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
    logging.info(f'process_data_dictionaries - {st.session_state["session_id"]}')
    """
    Process data dictionaries.
    """
    vetted_files=check_datatypes(vetted_files)
    vetted_files=convert_data_dictionary_to_json(vetted_files)
    # st.session_state['active_page'] = page
    st.session_state['vetted_files'] = vetted_files
    st.session_state['data_dictionaries_loaded'] = True