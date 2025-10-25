import streamlit as st
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
import tiktoken
import logging
import json
import re
import numpy as np
import traceback  # Add traceback module import
from pydantic import BaseModel, Field
import pandas as pd
import plotly.graph_objects as go
import io
import base64
import matplotlib.pyplot as plt
import matplotlib.figure as mfigure
import openai  # Added to catch BadRequestError

from utils.system_messages import construct_system_message
from utils.streamlit_helpers import reset_data_analyst, safely_escape_dollars, render_tool_call, render_tool_response, reset_analytics_agent
from utils.security_helpers import safely_execute_code


class ResponseFormat(BaseModel):
    python_syntax: str = Field(..., description="The generated python syntax.")
    commentary: str = Field(..., description="The commentary for the user.")


class OpenAIUtility:
    def __init__(self):
        self.client = OpenAI()
        self.enc_gpt4 = tiktoken.encoding_for_model("gpt-4")


    def token_count_message(self, message):
        str = ''
        for msg in message:
            if 'content'in msg:
                str = f"{str}role: {msg['role']}, message: {msg['content']}\n"
            elif 'tool_calls' in msg:
                for tool_call in msg['tool_calls']:
                    str = f"{str}role: {msg['role']}, tool_call: {tool_call['function']['name']}, arguments: {tool_call['function']['arguments']}\n"
        return len(self.enc_gpt4.encode(str))

    def _calculate_cost(self, prompt_tokens, completion_tokens=0, model=''):
        """
        Calculate API cost based on token usage and model
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens (default 0 for embeddings)
            model: Model name used for the API call
        Returns:
            cost_USD: Cost in USD
        """
        # Standard rates for common models (these can be updated as pricing changes)
        if model == 'text-embedding-3-small':
            # Embedding models
            return prompt_tokens * 0.02/1000000
        elif model == 'gpt-4.1-nano-2025-04-14':
            return 0.1*prompt_tokens/1000000 + 0.4*completion_tokens/1000000
        elif model == 'gpt-4.1-mini-2025-04-14':
            return 0.4*prompt_tokens/1000000 + 1.6*completion_tokens/1000000
        elif model == 'o4-mini-2025-04-16':
            return 1.1*prompt_tokens/1000000 + 4.4*completion_tokens/1000000
        elif model == 'gpt-4.1-2025-04-14':
            return 2*prompt_tokens/1000000 + 8*completion_tokens/1000000
        elif model == 'o3-2025-04-16':
            return 2*prompt_tokens/1000000 + 8*completion_tokens/1000000
        elif model == 'o3-pro-2025-06-10':
            return 20*prompt_tokens/1000000 + 80*completion_tokens/1000000
        elif model == 'gpt-5-nano-2025-08-07':
            return 0.05*prompt_tokens/1000000 + 0.4*completion_tokens/1000000
        elif model == 'gpt-5-mini-2025-08-07':
            return 0.25*prompt_tokens/1000000 + 2*completion_tokens/1000000
        elif model == 'gpt-5-2025-08-07':
            return 1.25*prompt_tokens/1000000 + 10*completion_tokens/1000000
        else:
            st.error(f"Model {model} not recognized for cost calculation.")

    # @retry(wait=wait_random_exponential(min=5, max=10), stop=stop_after_attempt(5))
    def _completion_with_backoff(self, **kwargs):
        logging.info(f'completion_with_backoff - {st.session_state["session_id"]}')
        try:
            return self.client.beta.chat.completions.parse(**kwargs)
        except openai.BadRequestError as e:
            # Detect the specific "context_length_exceeded" error
            err_code = getattr(e, "code", None)
            # Some versions include details in e.response or only in str(e)
            try:
                if not err_code and hasattr(e, "response") and isinstance(e.response, dict):
                    err_code = e.response.get("error", {}).get("code")
            except Exception:
                pass
            err_text = str(e)
            if (
                err_code == "context_length_exceeded"
                or "context_length_exceeded" in err_text
                or "Input tokens exceed the configured limit" in err_text
            ):
                logging.error(f'Context length exceeded: {err_text}')
                st.error('Conversation length too long. LLMs have a context window limit which has been exceeded. Please reset and start a new conversation. Alternatively, get in touch with [me](https://www.linkedin.com/in/balaji-kesavan/) and I can help you set up a custom solution.')
                st.stop()
            # Re-raise other BadRequestError cases
            raise

    def _prepare_api_args(self, messages, model, temperature, response_format, reasoning_effort, tools, tool_choice):
        """Prepares the arguments for the chat completion API call"""
        args = {'messages': messages, 'model': model, 'temperature': temperature, }
        
        if response_format:
            args['response_format'] = response_format
        
        if reasoning_effort:
            args['reasoning_effort'] = reasoning_effort

        if tools:
            args['tools'] = tools
            args['tool_choice'] = tool_choice
            args['parallel_tool_calls'] = False
            if 'o3' in args['model'] or 'o4' in args['model']:
                # remove parallel_tool_calls for o3 and o4 models
                args.pop('parallel_tool_calls', None)

        if 'o3' in model or 'o4' in model or 'gpt-5' in model:
            # remove temperature for o3 and o4 models
            args.pop('temperature', None)            
        return args
        
    def _handle_tool_calls(self, tool_calls, tool_handlers, messages):
        """Processes tool calls and updates messages with tool responses"""
        for tool_call in tool_calls:
            logging.info(f'Calling tool: {tool_call.function.name}')
            
            try:
                tool_name = tool_call.function.name
                args_dict = json.loads(tool_call.function.arguments)
                
                if tool_name in tool_handlers:
                    tool_response = tool_handlers[tool_name](args_dict)
                else:
                    tool_response = f"Tool '{tool_name}' not implemented or not available."
                
                messages.append({
                    'role': 'tool', 
                    'content': str(tool_response), 
                    'tool_call_id': tool_call.id
                })
                with st.session_state['messages_container']:
                    render_tool_response(str(tool_response))

            except Exception as e:
                # Log the full traceback for debugging purposes
                full_traceback = traceback.format_exc()
                logging.error(f"Error executing tool {tool_call.function.name}: {full_traceback}")
                
                # Provide a clean error message with exception type and message
                # but without potentially sensitive path information
                error_type = type(e).__name__
                error_message = f"Error executing tool {tool_call.function.name}: {error_type}: {str(e)}"
                
                # Extract line information from the traceback for better debugging help
                tb_lines = full_traceback.splitlines()
                for line in tb_lines:
                    if "line" in line and ", in " in line:
                        # This captures the line number information without file paths
                        error_message += "\n" + line.split(", in ")[-1]
                        
                messages.append({
                    'role': 'tool', 
                    'content': error_message, 
                    'tool_call_id': tool_call.id
                })
                with st.session_state['messages_container']:
                    with st.expander(f"🛠️ See Tool Response"):
                        st.write(safely_escape_dollars(str(error_message)))
        
        return messages

    def _extract_tools_and_handlers(self, tool_config):
        """Extracts tool specifications and handlers from tool_config"""
        tools = None
        tool_handlers = {}
        
        if tool_config:
            # Extract tool specs for API call
            tools = [item['spec'] for item in tool_config if 'spec' in item]
            
            # Create mapping from tool names to handlers
            for item in tool_config:
                if 'spec' in item and 'handler' in item and 'function' in item['spec'] and 'name' in item['spec']['function']:
                    tool_name = item['spec']['function']['name']
                    tool_handlers[tool_name] = item['handler']
        
        return tools, tool_handlers
    
    def _process_api_response(self, response, messages, session_id, model):
        """Processes an API response and updates stats"""
        content = response.choices[0].message.content
        tool_calls = response.choices[0].message.tool_calls
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens

        logging.info(f'Prompt tokens: {prompt_tokens}')
        logging.info(f'Completion tokens: {completion_tokens}')
        
        # Calculate cost using the new method
        cost_USD = self._calculate_cost(prompt_tokens, completion_tokens, model)
        
        # Add content to messages if not None
        if content is not None:
            messages.append({'role': 'assistant', 'content': content})

        return content, tool_calls, cost_USD, messages
    
    def _serialize_tool_calls(self, tool_calls):
        """Converts tool_calls to proper message format"""
        return [{
            'id': tc.id,
            'type': tc.type,
            'function': {'name': tc.function.name, 'arguments': tc.function.arguments}
        } for tc in tool_calls]
    
    def _process_tool_call_loop(self, tool_calls, content, messages, tool_handlers, args, session_id, model):
        """Handles the recursive tool call processing"""
        tool_cost = 0
        
        while tool_calls != []:
            # Serialize tool calls for the message
            serialized_tool_calls = self._serialize_tool_calls(tool_calls)
            if content is not None:
                messages.append({'role': 'assistant', 'content': content, 'tool_calls': serialized_tool_calls})
                with st.session_state['messages_container']:
                    st.chat_message('assistant').write(safely_escape_dollars(content))
                    for tool_call in serialized_tool_calls:
                        render_tool_call(tool_call)
            else:
                messages.append({'role': 'assistant', 'tool_calls': serialized_tool_calls})
                with st.session_state['messages_container']:
                    for tool_call in serialized_tool_calls:
                        render_tool_call(tool_call)
            
            # Process tool calls and get updated messages
            messages = self._handle_tool_calls(tool_calls, tool_handlers, messages)
            
            logging.info(f'Calling completion with backoff with tool call')

            # Update messages in args and set tool_choice to auto for follow-up call
            args['messages'] = messages
            args['tool_choice'] = 'auto'
            response = self._completion_with_backoff(**args)

            # Process the follow-up response
            content, tool_calls, cost_USD_inner, messages = self._process_api_response(
                response, messages, session_id, model
            )
            
            tool_cost += cost_USD_inner
            
            if tool_calls is None:
                tool_calls = []
                
        return content, messages, tool_cost
        
    def chatcompletion_APICall(self, messages, session_id='', temperature = 0.8, model='gpt-5-nano-2025-08-07', response_format = None, reasoning_effort = None, tool_config = None, tool_choice = 'required'):
        """
        Runs the chat completion API call
        Args:
            model: The model to use
            messages: The messages to send to the model
            temperature: The temperature to use
            response_format: The format for the response
            reasoning_effort: The reasoning effort parameter for the model
            tool_config: List of dictionaries containing tool specs and handlers
                         Each dict should have: 
                         - 'spec': The tool specification object
                         - 'handler': Function to handle the tool call
        Returns:
            The response from the API call
        """
        
        # Extract tool specs and handlers
        tools, tool_handlers = self._extract_tools_and_handlers(tool_config)

        # Prepare API arguments
        args = self._prepare_api_args(messages, model, temperature, response_format, reasoning_effort, tools, tool_choice)
        
        response = self._completion_with_backoff(**args)

        # Process the initial response
        content, tool_calls, cost_USD_initial, messages = self._process_api_response(
            response, messages, session_id, model
        )
            
        # Handle tool calls if present
        cost_USD_tool = 0
        if tool_calls is not None and tool_calls != []:
            content, messages, cost_USD_tool = self._process_tool_call_loop(
                tool_calls, content, messages, tool_handlers, args, session_id, model
            )
            
        # Calculate total cost at the end
        cost_USD = cost_USD_initial + cost_USD_tool
        
        logging.info(f'Final cost: ${cost_USD}')
        return [content, messages, cost_USD]
    
    def run_python_function(self, python_code, reason, vetted_files, report_function):
        """
        Run a python function in a sandboxed environment
        Args:
            python_code: The code snippet to run
            vetted_files: The vetted files to use
        Returns:
            The result of the code execution
        """

        # check if the code is a valid function definition
        if report_function == 'generate_report':
            if not python_code.strip().startswith('def generate_report():'):
                logging.error(f'Invalid function definition: {python_code}')
                return "The python function must be named generate_report and intake 0 arguments. The function must return a single pandas DataFrame or a pandas Series or a python dictionary. You can only use the pandas, numpy, datetime and math libraries."
        elif report_function == 'generate_plot':
            if not python_code.strip().startswith('def generate_plot():'):
                logging.error(f'Invalid function definition: {python_code}')
                return "The python function must be named generate_plot and intake 0 arguments. The function must return a single matplotlib.figure.Figure. You can only use the pandas, numpy, seaborn, matplotlib, datetime and math libraries."

        # # Check for any code outside the function definition
        # # Get all lines of code and indent levels
        # lines = python_code.strip().split('\n')
        
        # # If there are unindented non-comment lines after the function definition, reject
        # for i, line in enumerate(lines):
        #     # Skip the function definition line and allow comment lines
        #     stripped_line = line.strip()
        #     if (i > 0 and not line.startswith(' ') and not line.startswith('\t') and stripped_line and not stripped_line.startswith('#')):
        #         logging.error(f'Code exists outside of function: {line}')
        #         return "All code must be within the generate_report function. No code should exist outside the function definition."
        
        # # Make sure the function ends with a return statement
        # indented_lines = [line for line in lines[1:] if line.strip()]  # Skip function def line
        # if not indented_lines:
        #     logging.error("Empty function body")
        #     return "The function body is empty. It must contain code and end with a return statement."
        
        # last_code_line = indented_lines[-1].strip()
        # if not last_code_line.startswith('return '):
        #     logging.error(f'Function does not end with return statement: {last_code_line}')
        #     return "The function must end with a return statement that returns a pandas DataFrame, Series, or dictionary."
        
        # If we got here, function definition is acceptable
        return self.run_python_code(
            python_code=python_code,
            reason=reason,
            vetted_files=vetted_files,
            report_function=report_function
        )
        

    def run_python_code(self, python_code, reason, vetted_files, report_function):
        """
        Run a code snippet in a sandboxed environment
        Args:
            code_snippet: The code snippet to run
            df: The dataframe to use
        Returns:
            The result of the code execution
        """
        logging.info(f'run_python_code - {st.session_state["session_id"]}')

        # Execute the code with a timeout - pass None for report_function 
        # to let execute_with_timeout decide how to handle the result
        result, stdout_output, error_message = safely_execute_code(python_code, vetted_files, report_function)

        logging.info(f'Stdout output - {stdout_output} - {st.session_state["session_id"]}')

        if error_message:
            logging.error(f'Error executing code: {error_message}')
            result = f"Error executing code: {error_message}\n\nStdout Output: {stdout_output}"
            return result

        if report_function == 'generate_report' or report_function is None:
            # parse result to check if it is a DataFrame or Plotly figure
            if isinstance(result, pd.DataFrame):
                logging.info('Result is a DataFrame')
                # Only do one conversion to JSON, not two
                result = result.to_json(orient='index')

            elif isinstance(result, pd.Series):
                logging.info('Result is a pandas Series')
                result = result.to_json(orient='index')

            elif isinstance(result, dict):
                logging.info('Result is a dict')
                # Convert dict to DataFrame
                result = pd.DataFrame.from_dict(result, orient='index').to_json(orient='index')

            elif isinstance(result, (int, float)) or (hasattr(result, 'dtype') and np.issubdtype(result.dtype, np.number)):
                # Handle both Python and NumPy numeric types
                logging.info(f'Result is a number: {result}')
                # Convert NumPy types to native Python types if needed
                if hasattr(result, 'item'):
                    result = result.item()
                result = pd.DataFrame({'result': [result]}).to_json(orient='index')

            elif isinstance(result, list):
                logging.info(f'Result is a list: {result}')
                # Convert list to DataFrame
                result = pd.DataFrame(result).to_json(orient='index')

            elif isinstance(result, mfigure.Figure):
                logging.info('Result is a Matplotlib Figure, but it was created using the wrong tool')
                result = f"Code execution returned a Matplotlib Figure, but it was created using the wrong tool. Please use the generate_plot tool to create plots."

            elif result is None:
                logging.info('Result is None')
                if report_function  == 'generate_report':
                    result = "Code execution returned None. The code execution must return a pandas DataFrame or a pandas Series or a python dictionary. You can only use the pandas, numpy, datetime and math libraries."
                elif report_function is None:
                    result = "Code execution returned None. This could happen if the python expression is multiple lines long. The python expression must be a small single line code snippet. Use the run_python_function tool for complex multi-line code."

            else:
                logging.info(f'Result is not a pandas df or a pandas series or a python dictionary: {type(result)}')
                result = f"Code execution returned an object of type {type(result)}. The code execution must return a pandas DataFrame or a pandas Series or a python dictionary. You can only use the pandas, numpy, datetime and math libraries."

        elif report_function == 'generate_plot':
            if isinstance(result, mfigure.Figure):
                logging.info('Result is a Matplotlib Figure')
                # convert to URL
                buf = io.BytesIO()
                result.savefig(buf, format='png')
                plt.close(result)
                buf.seek(0)
                img_bytes = buf.getvalue()
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                img_url = f'data:image/png;base64,{img_b64}'
                result = img_url
            else:
                logging.info(f'Result is not a matplotlib.figure.Figure: {type(result)}')
                result = f"Code execution returned an object of type {type(result)}. The code execution must return a matplotlib.figure.Figure. You can only use the pandas, numpy, seaborn, matplotlib, datetime and math libraries."

        logging.info(f'Final execution result - {result[:100]}... - {st.session_state["session_id"]}' 
                    if len(str(result)) > 100 else f'Final execution result - {result} - {st.session_state["session_id"]}')

        # calculate token count for the result
        token_count = len(self.enc_gpt4.encode(str(result)))
        logging.info(f'Token count for tool response - {token_count} - {st.session_state["session_id"]}')

        if token_count >= 5000 and report_function != 'generate_plot':
            logging.error(f"Code execution returned a result of {token_count} tokens. Please refactor the code to keep the result under 5000 tokens.")
            result = f"Code execution returned a result of {token_count} tokens. Please refactor the code to keep the result under 5000 tokens."

        return result

    def generate_openai_response(self, vetted_files, model, agent_model):
        logging.info(f'generate_openai_response - {st.session_state["session_id"]}')

        system_message = construct_system_message(vetted_files, agent_model)

        st.session_state['system_message'] = system_message

        prompt = [{'role': 'system', 'content': system_message}]

        for dict_message in st.session_state['messages']:
            if dict_message['role'] != 'system':
                if dict_message['role'] in ['assistant', 'user'] and 'content' in dict_message:
                    prompt.append({
                        'role': dict_message['role'], 
                        'content': dict_message['content']
                    })
                if dict_message['role'] == 'assistant' and 'tool_calls' in dict_message:
                    prompt.append({
                        'role': dict_message['role'],
                        'tool_calls': dict_message['tool_calls']
                    })
                if dict_message['role'] == 'tool':
                    prompt.append({
                        'role': dict_message['role'],
                        'content': dict_message['content'],
                        'tool_call_id': dict_message['tool_call_id']
                    })


        token_count = self.token_count_message(prompt)
        logging.info(f'token_count - {token_count} - {st.session_state["session_id"]}')

        error_count = 0
        for message in st.session_state['messages']:
            if 'error' in message.keys():
                if message['role'] == 'assistant':
                    error_count += 1

        if error_count >= 3:
            st.error('Oops! Something went wrong. Try rephrasing your prompt in a different way.')
            st.button(':red[Reset Data Analyst]', on_click=reset_data_analyst, key='reset')
            if st.secrets['ENV'] == 'dev':
                st.write(st.session_state['messages'])
            st.stop()

        if token_count >= 200000:
            st.error('Conversation length too long. LLMs have a context window limit which has been exceeded. Please reset and start a new conversation. Alternatively, get in touch with [me](https://www.linkedin.com/in/balaji-kesavan/) and I can help you set up a custom solution.')
            if agent_model:
                st.button(':red[Reset Analytics Agent]', on_click=reset_analytics_agent, key='reset')
            else:
                st.button(':red[Reset Data Analyst]', on_click=reset_data_analyst, key='reset')
            if st.secrets['ENV'] == 'dev':
                st.write(st.session_state['messages'])
            st.stop()

        if agent_model:
            run_python_expression_toolspec = {
                "type": "function",
                "function": {
                    "name": "run_python_expression",
                    "description": "Run a python expression and return the result. The python expression must be a single expression that returns a pandas DataFrame or a pandas Series or a python dictionary. You can only use the pandas, numpy, datetime and math libraries.",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "python_expression": {
                                "type": "string",
                                "description": "The python expression to run. The python expression must be a single expression that returns a pandas DataFrame or a pandas Series or a python dictionary. You can only use the pandas, numpy, datetime and math libraries."
                            },
                            "reason": {
                                "type": "string",
                                "description": "The reason for running the python expression. This will be used to provide context for the code execution and help the user understand the purpose of the code snippet."
                            }
                        },
                        "additionalProperties": False,
                        "required": ["python_expression", "reason"],
                    },
                }
            }

            run_python_function_toolspec = {
                "type": "function",
                "function": {
                    "name": "run_python_function",
                    "description": "Run a python function called generate_report. The function must intake 0 arguments and return a single pandas DataFrame or a pandas Series or a python dictionary. You can only use the pandas, numpy, datetime and math libraries.",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "function_definition": {
                                "type": "string",
                                "description": "The python function definition to run. The function must be named generate_report and intake 0 arguments. The function must return a single pandas DataFrame or a pandas Series or a python dictionary. You can only use the pandas, numpy, datetime and math libraries."
                            },
                            "reason": {
                                "type": "string",
                                "description": "The reason for running the python function. This will be used to provide context for the code execution and help the user understand the purpose of the code snippet."
                            }
                        },
                        "additionalProperties": False,
                        "required": ["function_definition", "reason"],
                    },
                }
            }

            generate_seaborn_plot_toolspec = {
                "type": "function",
                "function": {
                    "name": "generate_plot",
                    "description": "Run a python function to generate a Seaborn plot. The function must intake 0 arguments and return a single matplotlib.figure.Figure. You can only use the pandas, numpy, seaborn, matplotlib, datetime and math libraries.",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "function_definition": {
                                "type": "string",
                                "description": "The python function definition to run. The function must be named generate_plot and intake 0 arguments. The function must return a single matplotlib.figure.Figure. You can only use the pandas, numpy, seaborn, matplotlib, datetime and math libraries."
                            },
                            "reason": {
                                "type": "string",
                                "description": "The design decisions made for the plot. This will be used to provide context for the code execution and help the user understand the purpose of the code snippet."
                            }
                        },
                        "additionalProperties": False,
                        "required": ["function_definition", "reason"],
                    },
                }
            }

            # Define tool config with both specs and handlers
            tool_config = [
                {
                    'spec': run_python_expression_toolspec,
                    'handler': lambda args_dict: self.run_python_code(
                        python_code=args_dict.get('python_expression'),
                        reason=args_dict.get('reason'),
                        vetted_files=vetted_files,
                        report_function=None,
                    )
                },
                {
                    'spec': run_python_function_toolspec,
                    'handler': lambda args_dict: self.run_python_function(
                        python_code=args_dict.get('function_definition'),
                        reason=args_dict.get('reason'),
                        vetted_files=vetted_files,
                        report_function='generate_report'
                    )
                },
                {
                    'spec': generate_seaborn_plot_toolspec,
                    'handler': lambda args_dict: self.run_python_function(
                        python_code=args_dict.get('function_definition'),
                        reason=args_dict.get('reason'),
                        vetted_files=vetted_files,
                        report_function='generate_plot'
                    )
                }
            ]
            _, response, cost = self.chatcompletion_APICall(prompt, model=model, temperature=0.1, tool_config=tool_config)
        else:
            response, _, cost = self.chatcompletion_APICall(prompt, model=model, temperature=0.1, response_format=ResponseFormat)

        st.session_state['prompt_str'] = ""
        st.session_state['cost'] += cost
        for dict_message in prompt:
            content_str = "None"
            tool_calls_str = "None"
            if 'content' in dict_message:
                content_str = dict_message['content'] if dict_message['content'] is not None else "None"
            elif 'tool_calls' in dict_message:
                tool_calls_str = f"Tool calls: {str(dict_message['tool_calls'])}"
            
            st.session_state['prompt_str'] += f"role: {dict_message['role']}\ncontent: {content_str}\ntool call: {tool_calls_str}\n--\n"
        return response


