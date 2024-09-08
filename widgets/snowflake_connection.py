import streamlit as st
import logging

from utils.data_import_helpers import gather_metadata

def render_snowflake_connection():
    logging.info(f'render_snowflake_connection - {st.session_state["session_id"]}')
    with st.form(key=f'connect_to_snowflake'):
        with st.expander('❄️:blue[or import your data from Snowflake]'):
            col1, col2 = st.columns(2)
            username = col1.text_input('Enter your username:')
            password = col2.text_input('Enter your password:', type='password')
            account = col1.text_input('Enter your account:')
            warehouse = col2.text_input('Enter your warehouse:')
            database = col1.text_input('Enter your database:')
            schema = col2.text_input('Enter your schema:')
            sql = st.text_area('Enter your SQL query:', height=100)

            if st.form_submit_button(
                label=':green[Connect to Snowflake]',
                use_container_width=True
            ):  
                st.session_state['source'] = 'snowflake'
                gather_metadata(
                    params={
                        'username': username,
                        'password': password,
                        'account': account,
                        'warehouse': warehouse,
                        'database': database,
                        'schema': schema,
                        'sql': sql
                    }
                )
                st.rerun()
