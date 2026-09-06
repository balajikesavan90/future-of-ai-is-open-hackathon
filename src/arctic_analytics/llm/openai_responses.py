import streamlit as st
import base64
import binascii
import math
from openai import OpenAI
import json
import logging
import matplotlib.pyplot as plt
import matplotlib.figure as mfigure
import pandas as pd
import io
import warnings
from PIL import Image

from arctic_analytics.config import (
    DEFAULT_OPENAI_MODEL,
    MAX_MODEL_CONTEXT_TOKENS,
    SUPPORTED_OPENAI_MODELS,
    get_openai_api_key,
    validate_openai_model,
)
from arctic_analytics.streamlit.helpers import safely_escape_dollars, render_tool_call, render_tool_response
from arctic_analytics.core.security import safely_execute_code
from arctic_analytics.llm.tokenization import safe_encoding_for_model



class OpenAIResponsesUtility:
    _IMAGE_PATCH_SIZE = 32
    _GPT_56_IMAGE_TOKEN_MULTIPLIER = 1.2
    _MAX_IMAGE_PATCHES = 30_000
    # Reading dimensions should not require allocating an unbounded image payload
    # while estimating request context. Larger inputs use the conservative maximum.
    _MAX_IMAGE_BASE64_CHARACTERS = 20 * 1024 * 1024

    def __init__(self):
        self.enc_gpt4 = safe_encoding_for_model("gpt-4")
        self._openai_api_key = None
        self._openai_client = None

    def _client(self):
        api_key = get_openai_api_key(secrets=st.secrets, session_state=st.session_state)
        if not api_key:
            raise RuntimeError("OpenAI API key is not configured for this session.")
        if self._openai_client is None or self._openai_api_key != api_key:
            self._openai_api_key = api_key
            self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client

    def _calculate_cost(self, prompt_tokens, completion_tokens=0, model=''):
        """
        Calculate API cost based on token usage and model
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model: Model name used for the API call
        Returns:
            cost_USD: Cost in USD
        """
        if model == 'gpt-5.6-luna':
            input_price_per_million = 0.2
            output_price_per_million = 1.2  
        elif model == 'gpt-5.6-terra':
            input_price_per_million = 2
            output_price_per_million = 12
        elif model == 'gpt-5.6-sol':
            input_price_per_million = 4
            output_price_per_million = 20
        elif model == 'gpt-6-astra':
            input_price_per_million = 10 
            output_price_per_million = 50
        else:
            raise ValueError(f"Pricing has not been configured for {model!r}.")

        return (
            input_price_per_million * prompt_tokens / 1_000_000
            + output_price_per_million * completion_tokens / 1_000_000
        )

    def _calculate_context_window_usage(self, input_tokens, model):
        """Return request-context usage against Arctic Analytics' 128K limit."""
        validate_openai_model(model)
        return min(input_tokens / MAX_MODEL_CONTEXT_TOKENS, 1.0)

    def _request_context_token_count(self, request_args):
        """Estimate all request content that contributes to model context."""
        context_payload = {
            key: request_args[key]
            for key in ('input', 'instructions', 'tools')
            if key in request_args
        }
        text_payload, image_tokens = self._separate_image_inputs_for_token_count(
            context_payload, request_args.get('model')
        )
        serialized_payload = json.dumps(
            text_payload,
            default=str,
            ensure_ascii=False,
            separators=(',', ':'),
        )
        return len(self.enc_gpt4.encode(serialized_payload)) + image_tokens

    def _separate_image_inputs_for_token_count(self, value, model):
        """Exclude image transport data from text tokens and estimate vision tokens."""
        image_tokens = 0

        def transform(item):
            nonlocal image_tokens
            if isinstance(item, dict):
                transformed = {key: transform(child) for key, child in item.items()}
                if item.get('type') == 'input_image' and isinstance(item.get('image_url'), str):
                    image_tokens += self._estimate_image_input_tokens(item, model)
                    transformed['image_url'] = '[image input]'
                return transformed
            if isinstance(item, list):
                return [transform(child) for child in item]
            if isinstance(item, tuple):
                return [transform(child) for child in item]
            return item

        return transform(value), image_tokens

    def _estimate_image_input_tokens(self, image_input, model):
        """Estimate image tokens using the documented GPT-5.6 patch rules.

        Unknown models or unreadable images use the API's 30,000-patch maximum
        as a conservative upper bound instead of treating base64 bytes as text.
        """
        maximum_tokens = math.ceil(
            self._MAX_IMAGE_PATCHES * self._GPT_56_IMAGE_TOKEN_MULTIPLIER
        )
        if model not in {'gpt-5.6-luna', 'gpt-5.6-terra', 'gpt-5.6-sol'}:
            return maximum_tokens

        dimensions = self._image_dimensions(image_input['image_url'])
        if dimensions is None:
            return maximum_tokens
        width, height = dimensions
        detail = image_input.get('detail', 'auto')

        if detail == 'low':
            width, height = self._scale_to_max_dimension(width, height, 512)
        elif detail == 'high':
            width, height = self._scale_to_max_dimension(width, height, 2_048)
            patch_count = self._image_patch_count(width, height)
            if patch_count > 2_500:
                return math.ceil(2_500 * self._GPT_56_IMAGE_TOKEN_MULTIPLIER)
        elif detail in {'auto', 'original'}:
            width, height = self._scale_to_max_dimension(width, height, 65_535)
        else:
            return maximum_tokens

        patch_count = self._image_patch_count(width, height)
        if patch_count > self._MAX_IMAGE_PATCHES:
            return maximum_tokens
        return math.ceil(patch_count * self._GPT_56_IMAGE_TOKEN_MULTIPLIER)

    def _image_dimensions(self, image_url):
        """Read data-URL image dimensions without adding image bytes to text context."""
        if not image_url.startswith('data:image/') or ';base64,' not in image_url:
            return None
        try:
            encoded_image = image_url.split(',', 1)[1]
            if len(encoded_image) > self._MAX_IMAGE_BASE64_CHARACTERS:
                return None
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(base64.b64decode(encoded_image, validate=True))) as image:
                    return image.size
        except (binascii.Error, ValueError, OSError):
            return None

    def _scale_to_max_dimension(self, width, height, maximum_dimension):
        scale = min(1, maximum_dimension / max(width, height))
        # Round up so the context-limit estimate never drops a partial image
        # patch after scaling.
        return max(1, math.ceil(width * scale)), max(1, math.ceil(height * scale))

    def _image_patch_count(self, width, height):
        return math.ceil(width / self._IMAGE_PATCH_SIZE) * math.ceil(height / self._IMAGE_PATCH_SIZE)

    def _enforce_request_context_limit(self, request_args):
        estimated_token_count = self._request_context_token_count(request_args)
        if estimated_token_count > MAX_MODEL_CONTEXT_TOKENS:
            raise ValueError(
                f"Estimated request context is {estimated_token_count:,} tokens, exceeding Arctic "
                f"Analytics' {MAX_MODEL_CONTEXT_TOKENS:,}-token limit. Start a "
                "new analysis session or reduce the conversation history."
            )

    def _responses_with_backoff(self, **kwargs):
        logging.info(f'responses_with_backoff - {st.session_state["session_id"]}')
        self._enforce_request_context_limit(kwargs)
        return self._client().responses.parse(**kwargs)

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

    def _prepare_api_args(self, messages, model, response_format, reasoning_effort, tools, tool_choice, include):
        args = {
            # The initial system message is represented by the Responses API's
            # dedicated ``instructions`` field.  Keeping it in ``input`` as
            # well duplicates it in both the request and local context check.
            'input': messages[1:],
            'instructions': messages[0]['content'][0]['text'],
            'model': model,
            'include': include
        }

        if tools:
            args['tools'] = tools
            args['tool_choice'] = tool_choice
            # Keep tool calls sequential so each call can render and execute as
            # soon as the model emits it, instead of batching multiple calls.
            args['parallel_tool_calls'] = False

        if model in SUPPORTED_OPENAI_MODELS:
            if reasoning_effort:
                args['reasoning'] = {'effort': reasoning_effort, 'summary': 'auto'}

        if response_format:
                args['text_format'] = response_format


        return args
    

    def _process_api_response(self, response, messages, model):
        outputs = response.output
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        logging.info(f'Prompt tokens: {prompt_tokens}')
        logging.info(f'Completion tokens: {completion_tokens}')

        
        # Calculate cost using the new method
        cost_USD = self._calculate_cost(prompt_tokens, completion_tokens, model)
        # Provider usage is authoritative for the UI and trace accounting.
        # The local estimator is used only to stop an oversized request before
        # it is sent, when no API usage value exists yet.
        context_window_usage = self._calculate_context_window_usage(prompt_tokens, model)
        # st.toast(f"Cost for this API call: ${cost_USD:.6f}")
        
        tool_calls = []
        for output in outputs:
            if output.type == 'message':
                messages.append(output.to_dict())
            elif output.type == 'reasoning':
                messages.append(output.to_dict())
                summary_list = output.to_dict()['summary']
                if summary_list != []:
                    with st.session_state['messages_container']:
                        with st.chat_message('assistant'):
                            for summary in summary_list:
                                with st.expander("🧠 Agent reasoning", expanded=True):
                                    st.write(safely_escape_dollars(summary['text']))  # Safely escape dollar signs for LaTeX rendering
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
                    with st.chat_message('assistant'):
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

        return tool_calls, cost_USD, messages, context_window_usage, prompt_tokens

    def _process_tool_call_loop(self, tool_calls, messages, tool_handlers, args, model):
        """Handles the recursive tool call processing"""
        tool_cost = 0
        
        while tool_calls != []:
            for tool_call in tool_calls:
                logging.info(f"Calling tool: {tool_call['name']}")
                logging.info(f"Tool call arguments: {tool_call['arguments']}")

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
                        with st.chat_message('assistant'):
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
                        with st.chat_message('assistant'):
                            render_tool_response(error_message)
        

            # Keep the system message solely in ``instructions``, as on the
            # initial request. It must not be duplicated in follow-up input.
            args['input'] = messages[1:]
            args['tool_choice'] = 'auto'
            response = self._responses_with_backoff(**args)

            # Process the follow-up response
            tool_calls, cost_USD_inner, messages, context_window_usage, input_tokens = self._process_api_response(
                response, messages, model
            )
            
            tool_cost += cost_USD_inner
            
            if tool_calls is None:
                tool_calls = []

        return messages, tool_cost, context_window_usage, input_tokens

    def responses_APIcall(
            self, 
            messages, 
            model=DEFAULT_OPENAI_MODEL,
            response_format = None, 
            reasoning_effort = 'low', 
            tool_config = None, 
            tool_choice = 'auto', 
            include = ['reasoning.encrypted_content']
        ):
        logging.info(f'responses_APIcall - {st.session_state["session_id"]}')

        validate_openai_model(model)

        tools, tool_handlers = self._extract_tools_and_handlers(tool_config)

        args = self._prepare_api_args(messages, model, response_format, reasoning_effort, tools, tool_choice, include)

        response = self._responses_with_backoff(**args)

        # Process the initial response
        tool_calls, cost_USD_initial, messages, context_window_usage_1, input_tokens_1 = self._process_api_response(
            response, messages, model
        )

        # Handle tool calls if present
        cost_USD_tool = 0
        context_window_usage_2 = 0
        input_tokens_2 = 0
        if tool_calls is not None and tool_calls != []:
            messages, cost_USD_tool, context_window_usage_2, input_tokens_2 = self._process_tool_call_loop(
                tool_calls, messages, tool_handlers, args, model
            )
            
        # Calculate total cost at the end
        cost_USD = cost_USD_initial + cost_USD_tool
        # Context window usage is cumulative - use the latest value from tool loop if present, otherwise initial
        context_window_usage = context_window_usage_2 if context_window_usage_2 != 0 else context_window_usage_1
        input_tokens = input_tokens_2 if input_tokens_2 != 0 else input_tokens_1

        logging.info(f'Final cost: ${cost_USD}')
        return [messages, cost_USD, context_window_usage, input_tokens]
    

    def run_python_function(self, python_code, reason, vetted_files, report_function):
        """
        Run a python function with application-level execution restrictions.
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
                return "The function definition should start with 'def generate_report():'. The python function must be named generate_report and take 0 arguments. The function must return a single pandas DataFrame. You can only use the pandas, numpy, datetime and math libraries."
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
        Run a code snippet with application-level execution restrictions.
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
            # Successful analysis results have one table-shaped contract so the UI
            # can always render them with st.dataframe.
            if isinstance(result, pd.DataFrame):
                logging.info('Result is a DataFrame')
                result = result.to_json(orient='index')

            elif isinstance(result, mfigure.Figure):
                logging.info('Result is a Matplotlib Figure, but it was created using the wrong tool')
                result = f"Code execution returned a Matplotlib Figure, but it was created using the wrong tool. Please use the generate_plot tool to create plots."

            elif result is None:
                logging.info('Result is None')
                if report_function == 'generate_report':
                    result = "Code execution returned None. The code execution must return a pandas DataFrame so it can be rendered as a table. You can only use the pandas, numpy, datetime and math libraries."
                elif report_function is None:
                    result = "Code execution returned None. The Python expression must be a small single-line expression that returns a pandas DataFrame. Use the run_python_function tool for complex multi-line code."

            else:
                logging.info(f'Result is not a pandas DataFrame: {type(result)}')
                result = f"Code execution returned an object of type {type(result)}. The code execution must return a pandas DataFrame so it can be rendered as a table. You can only use the pandas, numpy, datetime and math libraries."

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
            "description": "Run a Python expression and return a table. The expression must be a single expression that returns a pandas DataFrame, which will be rendered with st.dataframe. You can only use the pandas, numpy, datetime and math libraries.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "python_expression": {
                        "type": "string",
                        "description": "The Python expression to run. It must be a single expression that returns a pandas DataFrame. Convert Series results with .to_frame() or .reset_index(), and scalar results with pd.DataFrame({'result': [value]}). You can only use the pandas, numpy, datetime and math libraries."
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
            "description": "Run a Python function called generate_report. The function must take 0 arguments and return a single pandas DataFrame, which will be rendered with st.dataframe. You can only use the pandas, numpy, datetime and math libraries.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "function_definition": {
                        "type": "string",
                        "description": "The Python function definition to run. The function must be named generate_report, take 0 arguments, and return a single pandas DataFrame. Convert Series results with .to_frame() or .reset_index(), and scalar results with pd.DataFrame({'result': [value]}). You can only use the pandas, numpy, datetime and math libraries. ONLY provide the function definition, do not include the function call. The function will be invoked by the tool."
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
        response, cost, context_window_usage, context_window_tokens = self.responses_APIcall(
            st.session_state['messages'], model=model, tool_config=tool_config
        )

        st.session_state['prompt_str'] = ""
        st.session_state['cost'] += cost
        st.session_state['context_window_usage'] = context_window_usage
        st.session_state['context_window_tokens'] = context_window_tokens
        return response
