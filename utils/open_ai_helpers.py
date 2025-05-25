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
import logging
from pydantic import BaseModel, Field
import pandas as pd
import plotly.graph_objects as go

from utils.system_messages import construct_system_message
from utils.streamlit_helpers import reset_data_analyst
from utils.security_helpers import create_safe_execution_environment, execute_with_timeout


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
        else:
            st.error(f"Model {model} not recognized for cost calculation.")

    # @retry(wait=wait_random_exponential(min=5, max=10), stop=stop_after_attempt(5))
    def _completion_with_backoff(self, **kwargs):
        logging.info(f'completion_with_backoff - {st.session_state["session_id"]}')
        return self.client.beta.chat.completions.parse(**kwargs)

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
            args['parallel_tool_calls'] = True
            
        return args
        
    def _handle_tool_calls(self, tool_calls, tool_handlers, messages):
        """Processes tool calls and updates messages with tool responses"""
        for tool_call in tool_calls:
            logging.info(f'Calling tool: {tool_call.function.name}')
            logging.info(f'Tool call arguments: {tool_call.function.arguments}')
            
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
            except Exception as e:
                error_message = f"Error executing tool {tool_call.function.name}: {str(e)}"
                logging.error(error_message)
                messages.append({
                    'role': 'tool', 
                    'content': error_message, 
                    'tool_call_id': tool_call.id
                })
        
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
            else:
                messages.append({'role': 'assistant', 'tool_calls': serialized_tool_calls})
            
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
        
    def chatcompletion_APICall(self, messages, session_id='', temperature = 0.8, model='gpt-4.1-mini-2025-04-14', response_format = None, reasoning_effort = None, tool_config = None, tool_choice = 'required'):
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
    

    def run_code_snippet(self, code_snippet, vetted_files):
        """
        Run a code snippet in a sandboxed environment
        Args:
            code_snippet: The code snippet to run
            df: The dataframe to use
        Returns:
            The result of the code execution
        """
        # Create a restricted global environment for code execution
        safe_globals = create_safe_execution_environment(vetted_files)
        
        logging.info(f'run_code_snippet - {st.session_state["session_id"]}')
        logging.info(f'code_snippet - {code_snippet} - {st.session_state["session_id"]}')

        # Execute the code with a timeout - pass None for report_function 
        # to let execute_with_timeout decide how to handle the result
        result, stdout_output = execute_with_timeout(code_snippet, safe_globals, None)

        logging.info(f'Execution result - {result} - {st.session_state["session_id"]}')
        logging.info(f'Stdout output - {stdout_output} - {st.session_state["session_id"]}')

        # parse result to check if it is a DataFrame or Plotly figure
        if isinstance(result, pd.DataFrame):
            logging.info('Result is a DataFrame')
            # Only do one conversion to JSON, not two
            result = result.to_json(orient='index')

        elif isinstance(result, pd.Series):
            logging.info('Result is a pandas Series')
            result = result.to_json(orient='index')

        else:
            logging.info(f'Result is not a pandas df ot a pandas series: {type(result)}')
            result = "Code execution did not return a DataFrame or Series. The code snippet must be a single expression that returns a pandas DataFrame or a pandas Series. You can only use the pandas, numpy, datetime and math libraries."

        logging.info(f'Final execution result - {result[:100]}... - {st.session_state["session_id"]}' 
                    if len(str(result)) > 100 else f'Final execution result - {result} - {st.session_state["session_id"]}')

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

        if token_count >= 10000:
            st.error('Conversation length too long. Please keep it under 10000 tokens.')
            st.button(':red[Reset Data Analyst]', on_click=reset_data_analyst, key='reset')
            if st.secrets['ENV'] == 'dev':
                st.write(st.session_state['messages'])
            st.stop()

        if agent_model:
            run_code_snippet_toolspec = {
                "type": "function",
                "function": {
                    "name": "run_code_snippet",
                    "description": "Run a code snippet and return the result. The code snippet must be a single expression that returns a pandas DataFrame or a pandas Series. You can only use the pandas, numpy, datetime and math libraries.",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code_snippet": {
                                "type": "string",
                                "description": "The code snippet to run. The code snippet must be a single expression that returns a pandas DataFrame or a pandas Series. You can only use the pandas, numpy, datetime and math libraries."
                            },
                        },
                        "additionalProperties": False,
                        "required": ["code_snippet"],
                    },
                }
            }            # Define tool config with both specs and handlers
            tool_config = [
                {
                    'spec': run_code_snippet_toolspec,
                    'handler': lambda args_dict: self.run_code_snippet(
                        code_snippet=args_dict.get('code_snippet'),
                        vetted_files=vetted_files
                    )
                },
            ]
            _, response, cost = self.chatcompletion_APICall(prompt, model=model, temperature=0.1, tool_config=tool_config)
        else:
            response, _, cost = self.chatcompletion_APICall(prompt, model=model, temperature=0.1, response_format=ResponseFormat)

        st.session_state['prompt_str'] = ""
        for dict_message in prompt:
            content_str = "None"
            tool_calls_str = "None"
            if 'content' in dict_message:
                content_str = dict_message['content'] if dict_message['content'] is not None else "None"
            elif 'tool_calls' in dict_message:
                tool_calls_str = f"Tool calls: {str(dict_message['tool_calls'])}"
            
            st.session_state['prompt_str'] += f"role: {dict_message['role']}\ncontent: {content_str}\ntool call: {tool_calls_str}\n--\n"
        return response


