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

def construct_system_message(page, vetted_files):
    print('construct_system_message')
    system_message = """You are an automated system that generates python syntax that is executed on a cloud server. 
The python virtual environment has the latest versions of streamlit, pandas, numpy.
\n\n"""

    system_message += """Your task is to complete this code snippet with the appropriate python syntax.\n
import streamlit as st\n
import pandas as pd\n
import numpy as np\n
\n\n"""

    for filename in vetted_files:
        system_message += f'{filename} = pd.read_csv("{filename}.csv")\n\n'
    

    if page == 'data_analyst':
        system_message += """Your input will be a JSON string with the key 'user_input' and the value as a string of the user's request.

Your ouput must be a JSON string with the keys 'python_syntax' and 'commentary'.
The 'python_syntax' should be a single python function named 'generate_report' that takes in 0 arguments. 
The 'generate_report' function must return a single pandas DataFrame. 
This is a very serious requirement for all of your responses.\n\n"""
    elif page == 'chart_builder':
        system_message += """Your input will be a JSON string with the keys 'x_axis_description', 'y_axis_description', 'chart_type', 'color'.
Your input could also contain the optional key 'additional_instuctions'.

Your ouput must be a JSON string with the keys 'python_syntax' and 'commentary'.
The 'python_syntax' should be a single python function named 'generate_report' that takes in 0 arguments. 
The 'generate_report' function must generate plots using the streamlit chart API elements with appropriate subheaders. 
The 'generate_report' function must return a single Streamlit Chart element.
You can use one of the following Streamlit Chart elements: st.bar_chart, st.line_chart, st.area_chart, st.scatter_chart.
This is a very serious requirement for all of your responses.\n\n"""
    
    system_message += """The 'commentary should be a string with your message to the user. 
In the commentary you must explain your thought process to the user.
You must use the commentary to respond to the user's error messages. 
You must focus your attention on the reasoning and the logic used to create the 'generate_report' function instead of the syntax itself. 
This is a very serious requirement for all of your responses.\n\n"""

    system_message += "Here is the metadata of the files uploaded by the user.\n"
    for filename in vetted_files:
        system_message += f'\n\n{filename}:\n'
        system_message += f'Description: {vetted_files[filename]["dataset_description"]}\n'
        system_message += f'Data Dictionary:\n'
        system_message += vetted_files[filename]['data_dictionary_json']+'\n'
        # system_message += f'Pandas Describe:\n'
        # system_message += st.session_state['vetted_files'][filename]['dataframe'].describe().to_json(orient='index')+'\n'
        system_message += f'First 5 rows of the dataset:\n'
        system_message += vetted_files[filename]['dataframe'].head().to_json(orient='index')+'\n'
        # system_message += f'Last 5 rows of the dataset:\n'
        # system_message += st.session_state['vetted_files'][filename]['dataframe'].tail().to_json(orient='index')+'\n'
        # system_message += f'The dataset has already been loaded as a pandas DataFrame named {filename}\n\n'
    
    system_message += "You must use this metadata to generate your response.\n"

    # st.session_state['system_message'] = system_message

    return system_message
