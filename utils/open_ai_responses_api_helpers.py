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



class OpenAIResponsesUtility:
    def __init__(self):
        self.client = OpenAI()

    @retry(wait=wait_random_exponential(min=5, max=10), stop=stop_after_attempt(5))
    def _embedding_with_backoff(self, **kwargs):
        logging.info(f'embedding_with_backoff - {st.session_state["id"]}')
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
        logging.info(f'create_embedding_APICall - {st.session_state["id"]}')
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
        logging.info(f'responses_with_backoff - {st.session_state["id"]}')
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
            'instructions': messages[0]['content'],
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
                            
                        messages.append({
                            'type': 'function_call_output',
                            'call_id': tool_call['call_id'],
                            'output': str(tool_response),
                        })
                    except Exception as e:
                        error_message = f"Error executing tool {tool_call['name']}: {str(e)}"
                        logging.error(error_message)
                        messages.append({
                            'type': 'function_call_output',
                            'call_id': tool_call['call_id'],
                            'output': error_message
                        })
        

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
            session_id, 
            temperature = 0.8, 
            model='gpt-5-nano-2025-08-07', 
            response_format = None, 
            reasoning_effort = 'low', 
            tool_config = None, 
            tool_choice = 'auto', 
            allow_image_generation = False,
            image_params = None,
            # include = ['web_search_call.action.sources', 'reasoning.encrypted_content']
            include = []
        ):
        logging.info(f'responses_APIcall - {st.session_state["id"]}')

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
                tool_calls, messages, tool_handlers, args, session_id, model, include
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