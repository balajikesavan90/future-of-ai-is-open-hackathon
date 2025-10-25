import streamlit as st
import logging

generate_explanation_system_message = """You are an automated system that explains the computer code inputted by the user.
You must explain the code in a way that is easy to understand for a non-technical audience.
You must explain the purpose of the code, the logic behind the code, and the expected output of the code.
You must use simple language and avoid technical jargon.
You must generate your output in bullet points with short sentences.
Your output must be in github markdown format.
"""

generate_docstring_system_message = """You are an automated system that generates comments and docstrings for the computer code inputted by the user.
Your output must be a version of the user's code with comments and docstrings added.
The doc strings must include the function name, the purpose of the function, and the input and output parameters.
The comments must explain the logic and reasoning behind the code.
You must include comments for each line of code.
The comments must be written in a way that is easy to understand for someone who is not familiar with the code.
"""

generate_debugger_system_message = """You are an automated system that generates a response to a user's code snippet and error message.
You must generate a response that helps the user debug their code.
You must provide a detailed explanation of the error message and suggest possible solutions.
You must generate your output in markdown format.
You must include code snippets and explanations in your response.
You must focus on helping the user understand the error message and how to fix it.
"""

def get_base_system_message(agent_model):
    """Generate the base system message depending on model type."""
    if agent_model:
        return """You are an automated system that queries the user's data and generates actionable insights from it.
You can run tool calls to query the data and provide answers to the user.
You can pass a python expression to run_python_expression tool which will execute the code and return the result.
You can pass a python function to run_python_function tool which will execute the function and return the result.
You can pass a python function to run_python_plot_function tool which will execute the function and return the matplotlib figure.
Your goal is to analyze the user's data and generate insights from it.
You might need to run multiple tool calls to get the final result.

Use the run_python_expression tool to run small single line code snippets like 
 - df.groupby(['col1', 'col2', 'col3', ...])['col4'].mean()
 - df['col_name'].value_counts()
 - df['col_name'].isna().sum()
 - df['col_name'].median()
 - df['col_name'].min()
 - df['col_name'].max()
 - df['col_name'].nunique()
 - df['col_name'].unique()
 - df.sort_values('col_name').head(5)
 - df[df['col_name'] > 0].shape[0]
 - df['col_name'].str.contains("pattern", case=False, na=False).sum()
Avoid using the run_python_expression tool for complex multi-line logic or data manipulations.

Use the run_python_function tool to run complex multi-line code and/or data manipulations like
def generate_report():
    # Your complex multi-line data manipulation code here
    return df_result

Your response to the user must include the actionable insights from the thought process behind the analysis.
Generate your response in markdown format.
\n\n
"""
    else:
        return """You are an automated system that generates python syntax that is executed on a cloud server. 
The python virtual environment has the latest versions of streamlit, pandas, numpy and plotly.
\n\n"""

def add_code_snippet_instructions(system_message, vetted_files):
    """Add code snippet and dataset loading instructions for non-agent models."""
    system_message += """Your task is to complete this code snippet with the appropriate python syntax.\n
import streamlit as st\n
import pandas as pd\n
import numpy as np\n
import plotly.express as px\n
\n\n"""

    for filename in vetted_files:
        system_message += f'{filename} = pd.read_csv("{filename}.csv")\n\n'
    
    system_message += """Your input will be a JSON string with the key 'user_input' and the value as a string of the user's request.
Your ouput must be a JSON string with the keys 'python_syntax' and 'commentary'. Respond only with valid JSON.

The 'python_syntax' should be a single python function named 'generate_report' that takes in 0 arguments.
The 'generate_report' function must return either a single pandas DataFrame whose index and column names have been set appropriately or a single plotly plot that has been formatted neatly.
This is a very serious requirement for all of your responses.\n\n"""
    
    system_message += """The 'commentary' should be a string with your message to the user. 
In the commentary you must explain your thought process behing the generated 'generate_report' function.
You must focus your attention on the reasoning and the logic used to create the 'generate_report' function instead of the syntax itself. 
You must not use the commentary to respond to error messages, rather the commentary must be written for the user to consume. 
This is a very serious requirement for all of your responses.\n\n"""

    return system_message

def add_file_metadata(system_message, vetted_files):
    """Add metadata for each file to the system message."""
    system_message += "Here is the metadata of the files uploaded by the user.\n"
    for filename in vetted_files:
        system_message += f'\n\n{filename}:\n\n'
        system_message += f'Shape: {vetted_files[filename]["dataframe"].shape}\n\n'
        system_message += f'Description: {vetted_files[filename]["dataset_description"]}\n\n'
        system_message += f'Data Dictionary:\n\n'
        system_message += vetted_files[filename]['data_dictionary_json']+'\n\n'
        system_message += f'Pandas Describe:\n\n'
        system_message += vetted_files[filename]['dataframe'].describe(include='all').T.to_json(orient='index')+'\n\n'
        system_message += f'Missing Values by Column:\n\n'
        missing_values = vetted_files[filename]["dataframe"].isna().sum().to_json()
        system_message += missing_values + '\n\n'
        system_message += f'First 5 rows of the dataset:\n\n'
        system_message += vetted_files[filename]['dataframe'].head().to_json(orient='index')+'\n\n'
        system_message += f'Last 5 rows of the dataset:\n\n'
        system_message += vetted_files[filename]['dataframe'].tail().to_json(orient='index')+'\n\n'
        system_message += f'The dataset has already been loaded as a pandas DataFrame named {filename}\n\n'
    
    system_message += "You must use this metadata to generate your response.\n"
    return system_message
def construct_system_message(vetted_files, agent_model):
    """Construct the system message based on the model and available files."""
    logging.info(f'construct_system_message - {st.session_state["session_id"]}')
    
    system_message = get_base_system_message(agent_model)
    
    if not agent_model:
        system_message = add_code_snippet_instructions(system_message, vetted_files)
    
    system_message = add_file_metadata(system_message, vetted_files)
    
    return system_message
