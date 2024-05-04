import streamlit as st

def render_data_analysis():
    for filename in st.session_state['vetted_files']:
        df = st.session_state['vetted_files'][filename]['dataframe']
        st.dataframe(df)

    
