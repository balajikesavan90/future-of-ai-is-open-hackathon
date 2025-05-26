# import streamlit as st
# import logging
# import re
# import time
# from datetime import datetime, timedelta

# from utils.data_import_helpers import gather_metadata

# def is_valid_input(input_str, field_type):
#     """Validate input based on field type"""
#     if not input_str:
#         return False, "Field cannot be empty"
    
#     patterns = {
#         'username': r'^[a-zA-Z0-9_\-\.@]+$',
#         'account': r'^[a-zA-Z0-9_\-\.]+$',
#         'warehouse': r'^[a-zA-Z0-9_\-\.]+$',
#         'database': r'^[a-zA-Z0-9_\-\.]+$',
#         'schema': r'^[a-zA-Z0-9_\-\.]+$',
#     }
    
#     if field_type in patterns:
#         if not re.match(patterns[field_type], input_str):
#             return False, f"Invalid {field_type} format"
    
#     # Special check for SQL to prevent injection
#     if field_type == 'sql':
#         # Check for potentially dangerous patterns in SQL
#         dangerous_patterns = [
#             r';\s*DROP\s+', 
#             r';\s*DELETE\s+',
#             r';\s*TRUNCATE\s+',
#             r';\s*ALTER\s+',
#             r';\s*CREATE\s+',
#             r';\s*INSERT\s+',
#             r';\s*UPDATE\s+',
#             r';\s*GRANT\s+',
#             r';\s*EXEC\s+',
#             r'--',  # SQL comment
#             r'/\*'  # Multi-line comment start
#         ]
        
#         for pattern in dangerous_patterns:
#             if re.search(pattern, input_str, re.IGNORECASE):
#                 return False, "Potentially harmful SQL detected"
    
#     return True, ""

# def check_rate_limit():
#     """Basic rate limiting for connection attempts"""
#     # Initialize or get the attempt tracking
#     if 'snowflake_attempts' not in st.session_state:
#         st.session_state['snowflake_attempts'] = []
    
#     # Clean up old attempts (older than 1 hour)
#     current_time = datetime.now()
#     st.session_state['snowflake_attempts'] = [
#         attempt for attempt in st.session_state['snowflake_attempts']
#         if current_time - attempt < timedelta(hours=1)
#     ]
    
#     # Check if too many attempts
#     MAX_ATTEMPTS = 5
#     if len(st.session_state['snowflake_attempts']) >= MAX_ATTEMPTS:
#         return False, f"Too many connection attempts. Please try again later."
    
#     # Record this attempt
#     st.session_state['snowflake_attempts'].append(current_time)
#     return True, ""

# def render_snowflake_connection():
#     logging.info(f'render_snowflake_connection - {st.session_state["session_id"]}')
#     with st.form(key=f'connect_to_snowflake'):
#         with st.expander('❄️:blue[or import your data from Snowflake]'):
#             col1, col2 = st.columns(2)
#             username = col1.text_input('Enter your username:')
#             password = col2.text_input('Enter your password:', type='password')
#             account = col1.text_input('Enter your account:')
#             warehouse = col2.text_input('Enter your warehouse:')
#             database = col1.text_input('Enter your database:')
#             schema = col2.text_input('Enter your schema:')
#             sql = st.text_area('Enter your SQL query (SELECT statements only):', height=100)

#             if st.form_submit_button(
#                 label=':green[Connect to Snowflake]',
#                 use_container_width=True
#             ):
#                 # Check rate limiting first
#                 can_proceed, rate_limit_msg = check_rate_limit()
#                 if not can_proceed:
#                     st.error(rate_limit_msg)
#                     return
                
#                 # Validate all inputs
#                 validation_errors = []
#                 for field_name, field_value in [
#                     ('username', username),
#                     ('account', account),
#                     ('warehouse', warehouse),
#                     ('database', database),
#                     ('schema', schema),
#                     ('sql', sql)
#                 ]:
#                     is_valid, error_msg = is_valid_input(field_value, field_name)
#                     if not is_valid:
#                         validation_errors.append(f"{field_name.capitalize()}: {error_msg}")
                
#                 # Check if password was provided
#                 if not password:
#                     validation_errors.append("Password: Field cannot be empty")
                
#                 # Show errors if any
#                 if validation_errors:
#                     for error in validation_errors:
#                         st.error(error)
#                     return
                
#                 # If all validations pass, proceed with connection
#                 logging.info(f"Snowflake connection attempt by user: {username} to account: {account}")
                
#                 st.session_state['source'] = 'snowflake'
#                 try:
#                     gather_metadata(
#                         params={
#                             'username': username,
#                             'password': password,  # In production, consider using a secure vault service
#                             'account': account,
#                             'warehouse': warehouse,
#                             'database': database,
#                             'schema': schema,
#                             'sql': sql
#                         }
#                     )
#                     st.rerun()
#                 except Exception as e:
#                     logging.error(f"Snowflake connection failed: {str(e)}")
#                     st.error("Failed to connect to Snowflake. Please check your credentials and try again.")
