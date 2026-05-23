import streamlit as st
import logging
import io
import pandas as pd
import re
import os

from utils.data_import_helpers import gather_metadata

def is_valid_csv(file):
    """Validate if file is a proper CSV and not malicious"""
    # Check file size (10MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    if file.size > MAX_FILE_SIZE:
        return False, "File size exceeds 10MB limit"
    
    # Define suspicious patterns (e.g., script tags, executable commands)
    suspicious_patterns = [
        r'<script.*?>',
        r'\bexec\s*\(["\']',  # exec function call with string argument
        r'\beval\s*\(["\']',  # eval function call with string argument
        r'\bsystem\s*\(["\']',  # system function call with string argument
        r'^=cmd\|',  # Excel formula with cmd
        r'^=.*\|\|',  # Excel formula with pipes
        r'^=.*DDE\s*\(',  # Only match formulas that start with = and have DDE function call
        r'^=[+@-]'  # Common Excel formula injection markers at start
    ]
    pattern_regex = re.compile('|'.join(suspicious_patterns), re.IGNORECASE)
    
    # Basic content validation
    try:
        # First do a quick check of the beginning of the file
        pos = file.tell()
        content_sample = file.read(1024).decode('utf-8', 'ignore')
        file.seek(pos)
        
        for pattern in suspicious_patterns:
            if re.search(pattern, content_sample, re.IGNORECASE):
                return False, "Suspicious content detected in file header"
        
        # Now check if file can be parsed as CSV
        try:
            df = pd.read_csv(file)
            file.seek(0)  # Reset file pointer
        except Exception as e:
            return False, f"Invalid CSV format: {str(e)}"
        
        # Check each cell in the DataFrame for suspicious patterns
        for column in df.columns:
            # Convert column to string if it's not already
            if df[column].dtype != 'object':
                continue  # Skip numeric columns
                
            # Check each cell in string columns
            for value in df[column].astype(str):
                match = pattern_regex.search(value)
                if match:
                    matched_pattern = match.group(0)
                    return False, f"Suspicious content detected in cell: '{value[:50]}{'...' if len(value) > 50 else ''}' (matched pattern: '{matched_pattern}')"
        
        return True, ""
    except Exception as e:
        return False, f"Error validating CSV: {str(e)}"

def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal attacks"""
    return os.path.basename(filename)

def render_uploader():
    logging.info(f'render_uploader - {st.session_state["session_id"]}')
    with st.form(key=f'upload_files'):
        st.caption('📁:blue[or upload your own csv files]')
        uploaded_files = st.file_uploader(
            label='Upload Your Files in .csv format:', 
            type=['csv'],
            accept_multiple_files=True,
            label_visibility='collapsed'
        )

        if st.form_submit_button(
            label=':green[Lets Go!]',
            width='stretch',
        ):
            if uploaded_files:
                # Validate all files before processing
                all_files_valid = True
                for file in uploaded_files:
                    # Sanitize filename
                    file.name = sanitize_filename(file.name)
                    
                    # Validate file content
                    is_valid, error_msg = is_valid_csv(file)
                    if not is_valid:
                        all_files_valid = False
                        st.error(f"Error in file {file.name}: {error_msg}")
                        break
                
                if all_files_valid:
                    st.session_state['uploaded_files'] = uploaded_files
                    st.session_state['source'] = 'uploader'
                    gather_metadata()
                    st.rerun()
            else:
                st.warning("Please upload at least one CSV file.")
