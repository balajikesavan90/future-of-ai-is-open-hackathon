import streamlit as st
import base64
from openai import OpenAI, pydantic_function_tool
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
import json
import logging
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel
import os
import uuid
import matplotlib.pyplot as plt
import matplotlib.figure as mfigure
import pandas as pd
import numpy as np
import io
import base64
import tiktoken

# from utils.system_messages import construct_system_message
from utils.streamlit_helpers import safely_escape_dollars, render_tool_call, render_tool_response
from utils.security_helpers import safely_execute_code



class OpenAIResponsesUtility:
    def __init__(self):
        self.client = OpenAI()
        self.enc_gpt4 = tiktoken.encoding_for_model("gpt-4")

    @retry(wait=wait_random_exponential(min=5, max=10), stop=stop_after_attempt(5))
    def _embedding_with_backoff(self, **kwargs):
        logging.info(f'embedding_with_backoff - {st.session_state["session_id"]}')
        return self.client.embeddings.create(**kwargs)

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
        elif model == 'gpt-5-2025-08-07':
            return 1.25*prompt_tokens/1000000 + 10*completion_tokens/1000000
        elif model == 'gpt-5-mini-2025-08-07':
            return 0.25*prompt_tokens/1000000 + 2*completion_tokens/1000000
        elif model == 'gpt-5-nano-2025-08-07':
            return 0.05*prompt_tokens/1000000 + 0.4*completion_tokens/1000000
        else:
            st.error(f"Model {model} not recognized for cost calculation.")

    def _calculate_context_window_usage(self, tokens, model):
        if model in ['gpt-5-2025-08-07', 'gpt-5-mini-2025-08-07', 'gpt-5-nano-2025-08-07']:
            return tokens/400000
        elif model in ['gpt-4.1-2025-04-14', 'gpt-4.1-mini-2025-04-14', 'gpt-4.1-nano-2025-04-14']:
            return tokens/1047576

    def create_embedding_APICall(self, text, page, session_id=''):
        logging.info(f'create_embedding_APICall - {st.session_state["session_id"]}')
        response = self._embedding_with_backoff(
            input=text,
            model='text-embedding-3-small'
            )
        
        embeddings = response.data[0].embedding
        tokens = response.usage.total_tokens
        model = response.model
        cost_USD = self._calculate_cost(tokens, model=model)

        return embeddings   

    # @retry(wait=wait_random_exponential(min=5, max=10), stop=stop_after_attempt(5))
    def _responses_with_backoff(self, **kwargs):
        logging.info(f'responses_with_backoff - {st.session_state["session_id"]}')
        return self.client.responses.parse(**kwargs)

    def _extract_tools_and_handlers(self, tool_config):
        """Extracts tool specifications and handlers from the tool configuration"""
        tools = []
        tool_handlers = {}
        
        if tool_config:
            for item in tool_config:
                if 'spec' in item:
                    tools.append(item['spec'])
                if 'handler' in item:
                    if 'name' in item['spec']:
                        tool_name = item['spec']['name']
                        tool_handlers[tool_name] = item['handler']
                    
        return tools, tool_handlers

    def _prepare_api_args(self, messages, model, temperature, response_format, reasoning_effort, tools, tool_choice, include):
        args = {
            'input': messages,
            'instructions': messages[0]['content'][0]['text'],
            'model': model,
            'temperature': temperature,
            'include': include
        }

        if tools:
            args['tools'] = tools
            args['tool_choice'] = tool_choice
            args['parallel_tool_calls'] = True

        if model.startswith('o4'):
            args['tool_choice'] = 'auto'  # Set tool choice to auto for o4 models

        if model.startswith('o4') or model.startswith('o3') or model.startswith('gpt-5'):
            del args['temperature']  # Remove temperature for o4 and o3 models

            if reasoning_effort:
                args['reasoning'] = {'effort': reasoning_effort, 'summary': 'auto'}

        if response_format:
                args['text_format'] = response_format


        return args
    

    def _process_api_response(self, response, messages, session_id, model, image_params):
        outputs = response.output
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        total_tokens = prompt_tokens + completion_tokens
        logging.info(f'Prompt tokens: {prompt_tokens}')
        logging.info(f'Completion tokens: {completion_tokens}')

        
        # Calculate cost using the new method
        cost_USD = self._calculate_cost(prompt_tokens, completion_tokens, model)
        context_window_usage = self._calculate_context_window_usage(total_tokens, model)
        # st.toast(f"Cost for this API call: ${cost_USD:.6f}")
        
        tool_calls = []
        text = None
        images = []
        for output in outputs:
            if output.type == 'message':
                messages.append(output.to_dict())
            # elif output.type == 'web_search_call':
            #     messages.append(output.to_dict())
            elif output.type == 'reasoning':
                messages.append(output.to_dict())
                summary_list = output.to_dict()['summary']
                if summary_list != []:
                    for summary in summary_list:
                        with st.session_state['messages_container']:
                            with st.expander(f"🧠 Agent Reasoning", expanded=True):
                                st.write(safely_escape_dollars(summary['text']))  # Safely escape dollar signs for LaTeX rendering
            # elif output.type in ['mcp_list_tools', 'mcp_call']:
            #     messages.append(output.to_dict())
            elif output.type == 'function_call':
                id = output.id
                call_id = output.call_id
                function_name = output.name
                arguments = output.arguments
                tool_calls.append({
                    'type': 'function_call',
                    'id': id,
                    'call_id': call_id,
                    'name': function_name,
                    'arguments': arguments
                })
                with st.session_state['messages_container']:
                    render_tool_call({
                        'type': 'function_call',
                        'id': id,
                        'call_id': call_id,
                        'name': function_name,
                        'arguments': arguments
                    })

                output_dict = output.to_dict()
                if 'parsed_arguments' in output_dict:
                    del output_dict['parsed_arguments']  # Remove parsed_arguments if present
                messages.append(output_dict)
            # elif output.type == 'image_generation_call':
            #     processed_result = None
            #     try:
            #         if output.result:
            #             cost_USD += self._calculate_image_cost(image_params)
            #             # Save the image bytes to a file
            #             # decode and save via helper
            #             image_bytes = base64.b64decode(output.result)
            #             fname = str(uuid.uuid4())
            #             file_path = f"images/{session_id}/{fname}.webp"
            #             try:
            #                 # Save the image to the bucket
            #                 save_image_to_bucket(image_bytes, file_path)
            #                 images.append(file_path)
            #                 processed_result = file_path
            #             except Exception as e:
            #                 logging.error(f"Error saving image to bucket: {e}")
            #             messages.append({
            #                 'type': 'image_generation_call',
            #                 'status': output.status,
            #                 'result': processed_result,
            #                 'id': output.id
            #             })
            #         else:
            #             logging.warning("Image generation result is null")
            #     except Exception as e:
            #         logging.error(f"Error processing image generation: {e}")

        return tool_calls, cost_USD, messages, images, context_window_usage

    def _process_tool_call_loop(self, tool_calls, messages, tool_handlers, args, session_id, model):
        """Handles the recursive tool call processing"""
        tool_cost = 0
        
        while tool_calls != []:
            for tool_call in tool_calls:
                    logging.info(f'Calling tool: {tool_call['name']}')
                    logging.info(f'Tool call arguments: {tool_call['arguments']}')

                    try:
                        tool_name = tool_call['name']
                        args_dict = json.loads(tool_call['arguments'])
                        
                        if tool_name in tool_handlers:
                            tool_response = tool_handlers[tool_name](args_dict)
                        else:
                            tool_response = f"Tool '{tool_name}' not implemented or not available."

                        if tool_response.startswith('data:image/png;base64,'): 
                            messages.append({
                                'type': 'function_call_output',
                                'call_id': tool_call['call_id'],
                                'output': [
                                    {
                                        'type': 'input_image',
                                        'image_url': tool_response
                                    }
                                ],
                            })
                        else:                           
                            messages.append({
                                'type': 'function_call_output',
                                'call_id': tool_call['call_id'],
                                'output': str(tool_response),
                            })
                        with st.session_state['messages_container']:
                            render_tool_response(tool_response)
                    except Exception as e:
                        error_message = f"Error executing tool {tool_call['name']}: {str(e)}"
                        logging.error(error_message)
                        messages.append({
                            'type': 'function_call_output',
                            'call_id': tool_call['call_id'],
                            'output': error_message
                        })
                        with st.session_state['messages_container']:
                            render_tool_response(error_message)
        

            # Update messages in args and set tool_choice to auto for follow-up call
            args['input'] = messages
            args['tool_choice'] = 'auto'
            response = self._responses_with_backoff(**args)

            # Process the follow-up response
            tool_calls, cost_USD_inner, messages, images, context_window_usage = self._process_api_response(
                response, messages, session_id, model, image_params=None
            )
            
            tool_cost += cost_USD_inner
            
            if tool_calls is None:
                tool_calls = []

        return messages, images, tool_cost, context_window_usage

    def responses_APIcall(
            self, 
            messages, 
            session_id = '', 
            temperature = 0.8, 
            model='gpt-5-nano-2025-08-07', 
            response_format = None, 
            reasoning_effort = 'low', 
            tool_config = None, 
            tool_choice = 'auto', 
            allow_image_generation = False,
            image_params = None,
            # include = ['web_search_call.action.sources', 'reasoning.encrypted_content']
            include = ['reasoning.encrypted_content']
        ):
        logging.info(f'responses_APIcall - {st.session_state["session_id"]}')

        # if allow_image_generation:
        #     tool_config = tool_config or []
        #     tool_config.append(
        #         {
        #             'spec': {"type": "image_generation", "output_format": "webp", "background": image_params["background"], "input_fidelity": image_params["input_fidelity"], "model": image_params["model"], "moderation": image_params["moderation"], "quality": image_params["quality"], "size": image_params["size"]},
        #             'handler': None
        #         }
        #     )
        #     if 'reference_images' in image_params:
        #         image_content = []
        #         for img in image_params['reference_images']:
        #             image_content.append({
        #                 'type': 'input_image',
        #                 'detail': img['detail'],
        #                 'image_url': img['url']
        #             })
        #         messages.append({
        #             'role': 'user',
        #             'content': image_content
        #         })
        # else:
        #     image_params = None

        # # Extract tool specs and handlers
        tools, tool_handlers = self._extract_tools_and_handlers(tool_config)

        # # Prepare API arguments
        args = self._prepare_api_args(messages, model, temperature, response_format, reasoning_effort, tools, tool_choice, include)

        # st.write(args['input'])
        # st.stop()

        # Initial API call
        response = self._responses_with_backoff(**args)

        output_images = []

        # Process the initial response
        tool_calls, cost_USD_initial, messages, images_1, context_window_usage_1 = self._process_api_response(
            response, messages, session_id, model, image_params
        )

        # Handle tool calls if present
        cost_USD_tool = 0
        context_window_usage_2 = 0
        images_2 = None
        if tool_calls is not None and tool_calls != []:
            messages, images_2, cost_USD_tool, context_window_usage_2 = self._process_tool_call_loop(
                tool_calls, messages, tool_handlers, args, session_id, model
            )
            
        # Calculate total cost at the end
        cost_USD = cost_USD_initial + cost_USD_tool
        context_window_usage = context_window_usage_1 + context_window_usage_2
        if images_1:
            output_images.extend(images_1)
        if images_2:
            output_images.extend(images_2)

        logging.info(f'Final cost: ${cost_USD}')
        return [messages, output_images, cost_USD, context_window_usage]
    

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
            if python_code.strip().startswith('def generate_plot():'):
                logging.error(f'Use of generate_plot function detected in generate_report tool: {python_code}')
                return "Use of generate_plot function detected in the generate_report tool. Please use the generate_plot tool to create plots."
            elif not python_code.strip().startswith('def generate_report():'):
                logging.error(f'Invalid function definition: {python_code}')
                return "The function definition should start with 'def generate_report():'. The python function must be named generate_report and intake 0 arguments. The function must return a single pandas DataFrame or a pandas Series or a python dictionary. You can only use the pandas, numpy, datetime and math libraries."
        elif report_function == 'generate_plot':
            if python_code.strip().startswith('def generate_report():'):
                logging.error(f'Use of generate_report function detected in generate_plot tool: {python_code}')
                return "Use of generate_report function detected in the generate_plot tool. Please use the generate_report tool to create data reports."
            elif not python_code.strip().startswith('def generate_plot():'):
                logging.error(f'Invalid function definition: {python_code}')
                return "The function definition should start with 'def generate_plot():'. The python function must be named generate_plot and intake 0 arguments. The function must return a single matplotlib.figure.Figure. You can only use the pandas, numpy, seaborn, matplotlib, datetime and math libraries."
        
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
                if report_function == 'generate_report':
                    result = "Code execution returned None. The code execution must return a pandas DataFrame or a pandas Series or a Python dictionary. You can only use the pandas, numpy, datetime and math libraries."
                elif report_function is None:
                    result = "Code execution returned None. This could happen if the Python expression is multiple lines long. The Python expression must be a small single line code snippet. Use the run_python_function tool for complex multi-line code."

            else:
                logging.info(f'Result is not a pandas df or a pandas series or a python dictionary: {type(result)}')
                result = f"Code execution returned an object of type {type(result)}. The code execution must return a pandas DataFrame or a pandas Series or a Python dictionary. You can only use the pandas, numpy, datetime and math libraries."

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

    def generate_openai_response(self, vetted_files, model):
        logging.info(f'generate_openai_response - {st.session_state["session_id"]}')

        run_python_expression_toolspec = {
            "type": "function",
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
                "required": ["python_expression", "reason"]
            }
        }

        run_python_function_toolspec = {
            "type": "function",
            "name": "run_python_function",
            "description": "Run a python function called generate_report. The function must intake 0 arguments and return a single pandas DataFrame or a pandas Series or a python dictionary. You can only use the pandas, numpy, datetime and math libraries.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "function_definition": {
                        "type": "string",
                        "description": "The python function definition to run. The function must be named generate_report and intake 0 arguments. The function must return a single pandas DataFrame or a pandas Series or a python dictionary. You can only use the pandas, numpy, datetime and math libraries. ONLY provide the function definition, do not include the function call. The function will be invoked by the tool."
                    },
                    "reason": {
                        "type": "string",
                        "description": "The reason for running the python function. This will be used to provide context for the code execution and help the user understand the purpose of the code snippet."
                    }
                },
                "additionalProperties": False,
                "required": ["function_definition", "reason"]
            }
        }

        generate_seaborn_plot_toolspec = {
            "type": "function",
            "name": "generate_plot",
            "description": "Run a python function to generate a Seaborn plot. The function must intake 0 arguments and return a single matplotlib.figure.Figure. You can only use the pandas, numpy, seaborn, matplotlib, datetime and math libraries.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "function_definition": {
                        "type": "string",
                        "description": "The python function definition to run. The function must be named generate_plot and intake 0 arguments. The function must return a single matplotlib.figure.Figure. You can only use the pandas, numpy, seaborn, matplotlib, datetime and math libraries. ONLY provide the function definition, do not include the function call. The function will be invoked by the tool."
                    },
                    "reason": {
                        "type": "string",
                        "description": "The design decisions made for the plot. This will be used to provide context for the code execution and help the user understand the purpose of the code snippet."
                    }
                },
                "additionalProperties": False,
                "required": ["function_definition", "reason"]
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
        response, _, cost, _ = self.responses_APIcall(st.session_state['messages'], model=model, temperature=0.1, tool_config=tool_config)

        st.session_state['prompt_str'] = ""
        st.session_state['cost'] += cost
        return response