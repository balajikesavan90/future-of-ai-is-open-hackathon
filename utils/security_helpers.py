import streamlit as st
import threading
import ast
import logging
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

# Common data science libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objs as go
import plotly.express as px
import datetime
import warnings
import math

class SecurityError(Exception):
    """Exception raised for security violations in code execution."""
    pass

def validate_code_security(python_syntax):
    """
    Validate the security of Python code before execution.
    
    Args:
        python_syntax (str): The Python code to validate
        
    Returns:
        None: If code passes security checks
        
    Raises:
        SecurityError: If code contains potentially dangerous operations
        SyntaxError: If code has syntax errors
    """
    forbidden_modules = ['os', 'subprocess', 'sys', 'shutil', 'importlib', 'builtins', 
                       '__builtin__', 'pickle', 'socket', 'requests']
    forbidden_functions = ['eval', 'exec', 'compile', 'open', 'input', '__import__', 'globals']
    
    # Parse the code to check for security issues
    try:
        parsed_ast = ast.parse(python_syntax)
        
        # Check for imports
        for node in ast.walk(parsed_ast):
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name in forbidden_modules:
                        raise SecurityError(f"Import of potentially dangerous module '{name.name}' is not allowed")
            elif isinstance(node, ast.ImportFrom):
                if node.module in forbidden_modules:
                    raise SecurityError(f"Import from potentially dangerous module '{node.module}' is not allowed")
            
            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in forbidden_functions:
                    raise SecurityError(f"Use of potentially dangerous function '{node.func.id}' is not allowed")
                elif isinstance(node.func, ast.Attribute) and node.func.attr in forbidden_functions:
                    raise SecurityError(f"Use of potentially dangerous method '{node.func.attr}' is not allowed")
    except SyntaxError as e:
        raise SyntaxError(f"Invalid code: {str(e)}")
        
    return None

def create_safe_execution_environment(vetted_files):
    """
    Create a restricted global environment for code execution.
    
    Args:
        vetted_files (dict): Dictionary of vetted files with their dataframes
        
    Returns:
        dict: Safe globals dictionary for code execution
    """
    
    safe_globals = {
        'pd': pd,
        'np': np,
        'plt': plt,
        'go': go,
        'px': px,
        'datetime': datetime,
        'warnings': warnings,
        'math': math,
        'print': print,
        'st': st, 
    }
    
    # Add the dataframes from vetted files to the globals
    for filename in vetted_files:
        df_name = filename
        safe_globals[df_name] = vetted_files[filename]['dataframe'].copy()
    
    # Add a function to get original filenames directly from vetted_files
    safe_globals['get_dataframe_names'] = lambda: list(vetted_files.keys())
    
    return safe_globals

def is_expression(code):
    """
    Check if code is a single expression that can be evaluated.
    
    Args:
        code (str): The Python code to check
        
    Returns:
        bool: True if code is a single expression, False otherwise
    """
    try:
        parsed = ast.parse(code)
        return (len(parsed.body) == 1 and 
                isinstance(parsed.body[0], ast.Expr))
    except SyntaxError:
        return False

def execute_with_timeout(code, globals_dict, report_function, timeout_sec=10):
    """
    Execute code with a timeout to prevent infinite loops or resource exhaustion.
    
    Args:
        code (str): The Python code to execute
        globals_dict (dict): The global environment for execution
        report_function (str): The name of the function to call for the result
        timeout_sec (int): Maximum execution time in seconds
        
    Returns:
        tuple: (result, stdout_output)
        
    Raises:
        TimeoutError: If code execution exceeds the timeout
        Exception: Any exception raised during code execution
    """
    result = [None]
    error = [None]
    output_buffer = StringIO()
    
    def target():
        try:
            # Execute the code in the restricted environment
            with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
                # Check if code is a single expression that can be evaluated directly
                if is_expression(code):
                    result[0] = eval(code, globals_dict)
                else:
                    exec(code, globals_dict)
                    # Only try to call the report function if we executed statements
                    if report_function:
                        result[0] = eval(f'{report_function}()', globals_dict)
        except Exception as e:
            error[0] = e
    
    # Start the execution in a separate thread that we can timeout
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_sec)
    
    if thread.is_alive():
        # If the thread is still running after the timeout
        raise TimeoutError(f"Code execution timed out after {timeout_sec} seconds")
    
    if error[0]:
        raise error[0]
        
    return result[0], output_buffer.getvalue()

def safely_execute_code(python_syntax, vetted_files, report_function):
    """
    Safely execute Python code with security validation and timeout.
    
    Args:
        python_syntax (str): The Python code to execute
        vetted_files (dict): Dictionary of vetted files with their dataframes
        report_function (str): The name of the function to call for results
        
    Returns:
        tuple: (output, stdout_output, error_message)
    """
    output = None
    stdout_output = None
    error_message = None
    
    try:
        # Validate code security
        validate_code_security(python_syntax)
        
        # Create safe execution environment
        safe_globals = create_safe_execution_environment(vetted_files)
        
        # Execute the code with timeout and security restrictions
        output, stdout_output = execute_with_timeout(python_syntax, safe_globals, report_function)
        
    except TimeoutError as e:
        error_message = str(e)
        logging.error(f"Code execution timeout: {error_message}")
    except SecurityError as e:
        error_message = f"Security violation: {str(e)}"
        logging.error(f"Security violation in code execution: {str(e)}")
    except Exception as e:
        error_message = str(e)
        logging.error(f"Error in code execution: {str(e)}")
    
    return output, stdout_output, error_message
