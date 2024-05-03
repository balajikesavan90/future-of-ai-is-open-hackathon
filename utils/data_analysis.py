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
        print(f"Metadata for {filename} gathered successfully.")