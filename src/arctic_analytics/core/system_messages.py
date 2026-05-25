import streamlit as st
import logging

def get_base_system_message():
    """Generate the system message for Tool-Calling Analysis."""
    return """You support metadata-aware analysis over structured data.
You can request tool calls to query the data and provide reviewable answers to the user.
You can pass a python expression to run_python_expression tool which will execute the code and return the result.
You can pass a python function to run_python_function tool which will execute the function and return the result.
You can pass a python function to generate_plot tool which will execute the function and return the matplotlib figure.
Your goal is to analyze the user's data and generate reviewable findings from it.
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

Use the generate_plot tool to run complex multi-line code that generates plots like
def generate_plot():
    # Your complex multi-line plotting code here
    return fig_result
When generating plots, ensure that the plots are well-formatted with appropriate titles, labels, and legends.
When generating plots, ensure the labels and legends fit well within the plot area and are clearly readable. Avoid overlapping text.
Use the run_python_expression and/or the run_python_function to generate any supporting information needed for the plot.

Your response to the user must include the findings and enough analysis detail for human review.
**DO NOT** include the URL of the plot in your response. 
The UI will handle displaying the plot separately.
Generate your response in markdown format.
\n\n
"""

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

def construct_system_message(vetted_files):
    """Construct the Tool-Calling Analysis system message."""
    logging.info(f'construct_system_message - {st.session_state["session_id"]}')
    
    system_message = get_base_system_message()
    system_message = add_file_metadata(system_message, vetted_files)
    
    return system_message
