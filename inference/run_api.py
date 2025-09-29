#!/usr/bin/env python3

"""This python script is designed to run inference on a dataset using either the OpenAI or Anthropic API, depending on the model specified. 
It sorts instances by length and continually writes the outputs to a specified file, so that the script can be stopped and restarted without losing progress.
It can run inference on multiple models in parallel and output all results to the same directory.
"""

import json
import os
import time
import dotenv
import traceback
import threading
from pathlib import Path
from tqdm.auto import tqdm
import numpy as np
import openai
from openai import OpenAI
import tiktoken
from anthropic import HUMAN_PROMPT, AI_PROMPT, Anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
from datasets import load_dataset, load_from_disk
from make_datasets.utils import extract_diff, extract_full_file_patch
from argparse import ArgumentParser
import logging
import concurrent.futures
from transformers import AutoTokenizer
import functools
from collections import defaultdict
from datetime import datetime
from unidiff import PatchSet
import re
from swebench.harness.constants import PatchType
from together import Together

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
dotenv.load_dotenv()

MODEL_TOKENIZER_MAPPING = {
    "deepseek-r1": "deepseek-ai/deepseek-coder-33b-instruct",
    "deepseek-v3": "deepseek-ai/deepseek-coder-33b-instruct",
    "llama-v3p3-70b-instruct": "meta-llama/Llama-2-70b-hf",
    "qwen2p5-coder-32b-instruct": "Qwen/Qwen2-32B",
}

MODEL_LIMITS = {
    "claude-instant-1": 100_000,
    "claude-2": 100_000,
    "claude-3-opus-20240229": 200_000,
    "claude-3-sonnet-20240229": 200_000,
    "claude-3-haiku-20240307": 200_000,
    "claude-3-5-haiku-20241022": 200_000,
    "claude-3-5-sonnet-20240620": 200_000,
    "claude-3-5-sonnet-20241022": 200_000,
    "claude-3-7-sonnet-20250219": 200_000,
    "claude-3-7-sonnet-20250219-thinking": 200_000,
    "claude-sonnet-4-20250514": 200_000,
    "claude-opus-4-20250514": 200_000,
    "claude-opus-4-1-20250805": 200_000,
    "gpt-3.5-turbo-16k-0613": 16_385,
    "gpt-3.5-turbo-0613": 4_097,
    "gpt-3.5-turbo-1106": 16_385,
    "gpt-4-32k-0613": 32_768,
    "gpt-4-0613": 8_192,
    "gpt-4-1106-preview": 128_000,
    "gpt-4-0125-preview": 128_000,
    "gpt-4.1": 1_047_576,
    "o1": 200_000,
    "o1-pro-2025-03-19": 200_000,
    "o3-mini": 200_000,
    "o3": 200_000,
    "o4-mini": 200_000,
    "gpt-5": 400_000,
    "gpt-5-2025-08-07": 400_000,
    "gpt-5-mini": 400_000,
    "gpt-5-mini-2025-08-07": 400_000,
    "gpt-5-nano": 400_000,
    "gpt-5-nano-2025-08-07": 400_000,
    "gpt-5-chat-latest": 400_000,
    "gpt-4.5-preview": 128_000,
    "deepseek-r1": 160_000,
    "deepseek-v3": 128_000,
    "deepseek-v3-0324": 128_000,
    "llama-v3p3-70b-instruct": 128_000,
    "qwen2p5-coder-32b-instruct": 128_000,
    "gemini-2.5-pro-exp-03-25": 1_000_000,
    "gemini-2.5-pro-preview-05-06": 1_000_000,
    "gemini-2.5-pro-preview-06-05": 1_000_000,
    "gpt-4o-2024-11-20": 128_000,
    "llama4-maverick-instruct-basic": 1_000_000,
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8": 524_288,  # Will be increased to 1M
    "grok-3-latest": 128_000,  # xAI Grok-3 context window
}

# The cost per token for each model input.
MODEL_COST_PER_INPUT = {
    "claude-instant-1": 0.00000163,
    "claude-2": 0.00001102,
    "claude-3-opus-20240229": 0.000015,
    "claude-3-sonnet-20240229": 0.000003,
    "claude-3-haiku-20240307": 0.00000025,
    "claude-3-5-haiku-20241022": 0.00000080,
    "claude-3-5-sonnet-20240620": 0.000003,
    "claude-3-5-sonnet-20241022": 0.000003,
    "claude-3-7-sonnet-20250219": 0.000003,
    "claude-3-7-sonnet-20250219-thinking": 0.000003,
    "claude-sonnet-4-20250514": 0.000003,
    "claude-opus-4-20250514": 0.000003,
    "claude-opus-4-1-20250805": 0.000003,
    "gpt-3.5-turbo-16k-0613": 0.0000015,
    "gpt-3.5-turbo-0613": 0.0000015,
    "gpt-3.5-turbo-1106": 0.000001,
    "gpt-35-turbo-0613": 0.0000015,
    "gpt-35-turbo": 0.0000015,
    "gpt-4-0613": 0.00003,
    "gpt-4-32k-0613": 0.00006,
    "gpt-4-32k": 0.00006,
    "gpt-4-1106-preview": 0.00001,
    "gpt-4-0125-preview": 0.00001,
    "gpt-4.1": 0.000002,  # $2.00/1M tokens for input
    "o1": 0.000015,
    "o1-pro-2025-03-19": 0.000015,
    "o3-mini": 0.00000110,
    "o3": 0.000010,  # $10.00/1M tokens for input
    "o4-mini": 0.00000110,  # $1.10/1M tokens for input
    "gpt-5": 0.00000125,  # $1.25/1M tokens for input
    "gpt-5-2025-08-07": 0.00000125,  # $1.25/1M tokens for input
    "gpt-5-mini": 0.00000025,  # $0.25/1M tokens for input
    "gpt-5-mini-2025-08-07": 0.00000025,  # $0.25/1M tokens for input
    "gpt-5-nano": 0.00000005,  # $0.05/1M tokens for input
    "gpt-5-nano-2025-08-07": 0.00000005,  # $0.05/1M tokens for input
    "gpt-5-chat-latest": 0.00000125,  # $1.25/1M tokens for input
    "gpt-4.5-preview": 0.000075,
    "deepseek-r1": 0.000003,
    "deepseek-v3": 0.0000009,
    "deepseek-v3-0324": 0.0000009,
    "llama-v3p3-70b-instruct": 0.0000009,
    "qwen2p5-coder-32b-instruct": 0.0000009,
    "gemini-2.5-pro-exp-03-25": 0.000005,  # $0.005/1K tokens for input
    "gemini-2.5-pro-preview-05-06": 0.000005,  # $0.005/1K tokens for input
    "gemini-2.5-pro-preview-06-05": 0.000005,  # $0.005/1K tokens for input
    "gpt-4o-2024-11-20": 0.0000025,  # $2.50/1M tokens for input
    "llama4-maverick-instruct-basic": 0.0000009,  # Estimated cost similar to other Llama models
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8": 0.0000009,  # Actual pricing from Together AI
    "grok-3-latest": 0.0000020,  # Estimated cost for Grok-3
}

# The cost per token for each model output.
MODEL_COST_PER_OUTPUT = {
    "claude-instant-1": 0.00000551,
    "claude-2": 0.00003268,
    "claude-3-opus-20240229": 0.000075,
    "claude-3-sonnet-20240229": 0.000015,
    "claude-3-haiku-20240307": 0.00000125,
    "claude-3-5-haiku-20241022": 0.000004,
    "claude-3-5-sonnet-20240620": 0.000015,
    "claude-3-5-sonnet-20241022": 0.000015,
    "claude-3-7-sonnet-20250219": 0.000015,
    "claude-3-7-sonnet-20250219-thinking": 0.000015,
    "claude-sonnet-4-20250514": 0.000015,
    "claude-opus-4-20250514": 0.000015,
    "claude-opus-4-1-20250805": 0.000015,
    "gpt-3.5-turbo-16k-0613": 0.000002,
    "gpt-3.5-turbo-16k": 0.000002,
    "gpt-3.5-turbo-1106": 0.000002,
    "gpt-35-turbo-0613": 0.000002,
    "gpt-35-turbo": 0.000002,
    "gpt-4-0613": 0.00006,
    "gpt-4-32k-0613": 0.00012,
    "gpt-4-32k": 0.00012,
    "gpt-4-1106-preview": 0.00003,
    "gpt-4-0125-preview": 0.00003,
    "gpt-4.1": 0.000008,  # $8.00/1M tokens for output
    "o1": 0.000060,
    "o1-pro-2025-03-19": 0.000060,
    "o3-mini": 0.00000440,
    "o3": 0.000040,  # $40.00/1M tokens for output
    "o4-mini": 0.00000440,  # $4.40/1M tokens for output
    "gpt-5": 0.00001,  # $10.00/1M tokens for output
    "gpt-5-2025-08-07": 0.00001,  # $10.00/1M tokens for output
    "gpt-5-mini": 0.000002,  # $2.00/1M tokens for output
    "gpt-5-mini-2025-08-07": 0.000002,  # $2.00/1M tokens for output
    "gpt-5-nano": 0.0000004,  # $0.40/1M tokens for output
    "gpt-5-nano-2025-08-07": 0.0000004,  # $0.40/1M tokens for output
    "gpt-5-chat-latest": 0.00001,  # $10.00/1M tokens for output
    "gpt-4.5-preview": 0.000150,
    "deepseek-r1": 0.000008,
    "deepseek-v3": 0.0000009,
    "deepseek-v3-0324": 0.0000009,
    "llama-v3p3-70b-instruct": 0.0000009,
    "qwen2p5-coder-32b-instruct": 0.0000009,
    "gemini-2.5-pro-exp-03-25": 0.000015,  # $0.015/1K tokens for output
    "gemini-2.5-pro-preview-05-06": 0.000015,  # $0.015/1K tokens for output
    "gemini-2.5-pro-preview-06-05": 0.000015,  # $0.015/1K tokens for output
    "gpt-4o-2024-11-20": 0.00001,  # $10.00/1M tokens for output
    "llama4-maverick-instruct-basic": 0.0000009,  # Estimated cost similar to other Llama models
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8": 0.0000009,  # Actual pricing from Together AI
    "grok-3-latest": 0.0000060,  # Estimated cost for Grok-3
}

# Mapping of simple model names to their Fireworks paths
FIREWORKS_MODEL_PATHS = {
    "deepseek-r1": "accounts/fireworks/models/deepseek-r1",
    "deepseek-v3": "accounts/fireworks/models/deepseek-v3-0324",
    "deepseek-v3-0324": "accounts/fireworks/models/deepseek-v3-0324",
    "llama-v3p3-70b-instruct": "accounts/fireworks/models/llama-v3p3-70b-instruct",
    "qwen2p5-coder-32b-instruct": "accounts/fireworks/models/qwen2p5-coder-32b-instruct",
}

# Mapping of simple model names to their Together AI paths
TOGETHER_MODEL_PATHS = {
    "llama4-maverick-instruct-basic": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
}

# used for azure
ENGINES = {
    "gpt-3.5-turbo-16k-0613": "gpt-35-turbo-16k",
    "gpt-4-0613": "gpt-4",
    "gpt-4-32k-0613": "gpt-4-32k",
}

#####################################
#          Helper Functions         #
#####################################

def is_test(name, test_phrases=None):
    if test_phrases is None:
        test_phrases = ["test", "tests", "testing"]
    words = set(re.split(r" |_|\/|\.", name.lower()))
    return any(word in words for word in test_phrases)

def validate_patch_format(patch_text: str, output_dir: str = None, instance_id: str = None) -> tuple[bool, str]:
    """
    Validates that a patch is properly formatted and can be parsed.
    
    Args:
        patch_text (str): The patch text to validate
        output_dir (str, optional): Directory to write failed patches to
        instance_id (str, optional): Instance ID for the failed patch filename
        
    Returns:
        tuple[bool, str]: (is_valid, error_message). If is_valid is False, error_message contains the reason
    """
    try:
        patch_set = PatchSet(patch_text.splitlines())
        return True, ""
    except Exception as e:
        error_msg = (
            "VALIDATION ERROR: Failed to parse patch\n"
            f"Error: {str(e)}\n"
            "The generated output may not be in the correct patch format"
        )
        logger.error(f"Error parsing patch: {str(e)}")
        return False, error_msg

def validate_patch_no_test_files(patch_text: str, output_dir: str = None, instance_id: str = None) -> tuple[bool, str]:
    """
    Validates that a patch does not modify any test files.
    
    Args:
        patch_text (str): The patch text to validate
        output_dir (str, optional): Directory to write failed patches to
        instance_id (str, optional): Instance ID for the failed patch filename
        
    Returns:
        tuple[bool, str]: (is_valid, error_message). If is_valid is False, error_message contains the reason
    """
    try:
        patch_set = PatchSet(patch_text.splitlines())
        test_files = []
        
        for patched_file in patch_set:
            if is_test(patched_file.path):
                test_files.append(patched_file.path)
                logger.warning(f"Found test file modification: {patched_file.path}")
        
        if test_files:
            error_msg = (
                "VALIDATION ERROR: Generated patch contains test file modifications\n"
                "The model must only modify source code files, not test files.\n"
                f"Test files found ({len(test_files)}):\n- " + "\n- ".join(test_files)
            )
            return False, error_msg
        return True, ""
    except Exception as e:
        error_msg = (
            "VALIDATION ERROR: Failed to parse patch\n"
            f"Error: {str(e)}\n"
            "The generated output may not be in the correct patch format"
        )
        logger.error(f"Error parsing patch: {str(e)}")
        return False, error_msg

def validate_and_extract_patch(completion_text: str, output_dir: str = None, instance_id: str = None) -> tuple[str|None, str|None]:
    """
    Extracts and validates a patch from completion text, checking both format and content.
    
    Args:
        completion_text (str): The model completion text
        output_dir (str, optional): Directory to write failed patches to
        instance_id (str, optional): Instance ID for the failed patch filename
        
    Returns:
        tuple[str|None, str|None]: (patch_text, error_message)
    """
    # First extract the patch
    patch_text = extract_full_file_patch(completion_text)
    if not patch_text:
        return None, "No valid full file patch found in completion: " + completion_text[:200] + "..."
    
    # patch_text = extract_diff(completion_text)
    # if not patch_text:
    #     return None, "No valid patch found in completion"
    
    # # Optionally validate patch format here
    # if not validate_patch_format(patch_text):
    #     return None, "Patch format validation failed"

    return patch_text, None

def calc_cost(model_name, input_tokens, output_tokens):
    """
    Calculates the cost of a response from the openai API.

    Args:
    response (openai.ChatCompletion): The response from the API.

    Returns:
    float: The cost of the response.
    """
    # Handle model name mismatches by stripping version information if needed
    base_model_name = model_name
    if base_model_name not in MODEL_COST_PER_INPUT:
        # Extract the base model name without version information
        for known_model in MODEL_COST_PER_INPUT.keys():
            if base_model_name.startswith(known_model):
                base_model_name = known_model
                break
    
    if base_model_name not in MODEL_COST_PER_INPUT:
        logger.warning(f"Unknown model: {model_name}, defaulting to gpt-4.5-preview pricing")
        base_model_name = "gpt-4.5-preview"
        
    cost = (
        MODEL_COST_PER_INPUT[base_model_name] * input_tokens
        + MODEL_COST_PER_OUTPUT[base_model_name] * output_tokens
    )
    logger.info(
        f"input_tokens={input_tokens}, output_tokens={output_tokens}, cost={cost:.2f}"
    )
    return cost


#####################################
#          Tokenizer Functions      #
#####################################

@functools.lru_cache(maxsize=None)
def get_hf_tokenizer(model_name):
    """Returns a HuggingFace tokenizer for the given model name.
    Uses caching to avoid loading the same tokenizer multiple times.
    Note: This only downloads the tokenizer files (~1-2MB) not the full model.
    
    Args:
        model_name (str): The name of the model to get the tokenizer for
        
    Returns:
        transformers.PreTrainedTokenizer: The tokenizer for the model
    """
    if model_name not in MODEL_TOKENIZER_MAPPING:
        raise ValueError(f"No HuggingFace tokenizer mapping found for {model_name}")
    
    try:
        # First try to load from local cache
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                MODEL_TOKENIZER_MAPPING[model_name],
                local_files_only=True
            )
            return tokenizer
        except Exception:
            # If not in cache, download it (only happens once)
            logger.info(f"Downloading tokenizer for {model_name} (only happens once)")
            tokenizer = AutoTokenizer.from_pretrained(MODEL_TOKENIZER_MAPPING[model_name])
            return tokenizer
    except Exception as e:
        logger.error(f"Error loading tokenizer for {model_name}: {e}")
        # Fallback to GPT-4 tokenizer
        return tiktoken.encoding_for_model("gpt-4")

def gpt_tokenize(string: str, encoding) -> int:
    """Returns the number of tokens in a text string."""
    # First check if this is a model that needs HuggingFace tokenizer
    if isinstance(encoding, str) and encoding in MODEL_TOKENIZER_MAPPING:
        tokenizer = get_hf_tokenizer(encoding)
        return len(tokenizer.encode(string))
    
    # For cases where the model doesn't have a direct tokenizer mapping
    if isinstance(encoding, str):
        try:
            encoding = tiktoken.encoding_for_model(encoding)
        except KeyError:
            # Fallback for models without direct tokenizer mapping
            model_mapping = {
                "gpt-4.5-preview": "gpt-4",
                "gpt-4.1": "gpt-4",
                "o1": "gpt-4",
                "o1-pro-2025-03-19": "gpt-4",
                "o3-mini": "gpt-4",
                "o3": "gpt-4",
                "o4-mini": "gpt-4",
            }
            fallback_model = model_mapping.get(encoding, "gpt-4")
            encoding = tiktoken.encoding_for_model(fallback_model)
    
    num_tokens = len(encoding.encode(string))
    print(f"Number of tokens: {num_tokens}")
    return num_tokens

def claude_tokenize(string: str, api) -> int:
    """Returns the number of tokens in a text string."""
    try:
        response = api.messages.count_tokens(
            model="claude-opus-4-1-20250805",
            messages=[{
                "role": "user",
                "content": string
            }]
        )
        return response.input_tokens
    except Exception as e:
        logger.error(f"Error counting tokens: {e}")
        return 0


#####################################
#          OpenAI API               #
#####################################

def call_chat(model_name_or_path, inputs, use_azure, temperature, top_p, instance_id=None, **model_args):
    """
    Calls the openai API to generate completions for the given inputs.
    """
    logger.info(f"Making chat API call for instance {instance_id}")
    system_messages = inputs.split("\n", 1)[0]
    user_message = inputs.split("\n", 1)[1]
    try:
        # Initialize the OpenAI client
        openai_key = os.environ.get("OPENAI_API_KEY", None)
        if openai_key is None:
            raise ValueError(
                "Must provide an api key. Expected in OPENAI_API_KEY environment variable."
            )
        
        additional_args = {}
        request_args = model_args.copy()
        
        # Handle max tokens parameter based on model type
        if model_name_or_path.startswith("gpt-5"):
            request_args["max_completion_tokens"] = 128_000
        if model_name_or_path.startswith(("o3")):
            request_args["max_completion_tokens"] = request_args.pop("max_tokens", 20_000)
        elif model_name_or_path.startswith("o4"):
            request_args["max_completion_tokens"] = request_args.pop("max_tokens", 20_000)
        elif model_name_or_path.startswith("gpt-4.1"):
            # GPT-4.1 supports a larger output window of 32,768 tokens
            request_args["max_tokens"] = 32_768
        else:
            request_args["max_tokens"] = 16_384

        # Remove max_tokens from request_args if present, as per instruction
        request_args.pop("max_tokens", None)
        
        # Special handling for O-level models
        if model_name_or_path.startswith("o1") or model_name_or_path.startswith("o3") or model_name_or_path.startswith("o4"):
            # Add reasoning_effort for o-level models
            additional_args["reasoning_effort"] = "high"  # Changed from "low" to "high"
            
            # O-level models don't support temperature parameter
            # Don't pass temperature or top_p
            temperature_param = None
            top_p_param = None
        else:
            # For other models, use the provided temperature and top_p
            temperature_param = temperature
            top_p_param = top_p
            
        if use_azure:
            client = OpenAI(
                api_key=openai_key,
                base_url="https://pnlpopenai3.openai.azure.com/",
                api_version="2023-05-15"
            )
            print(f"additional_args: {additional_args}")
            print(f"request_args: {request_args}")
            # For Azure, we use deployment_id instead of model
            response = client.chat.completions.create(
                deployment_id=ENGINES[model_name_or_path] if use_azure else None,
                messages=[
                    {"role": "system", "content": system_messages},
                    {"role": "user", "content": user_message},
                ],
                top_p=top_p_param,
                **additional_args,
                **request_args,
            )
        else:
            client = OpenAI(api_key=openai_key)
            # Add more verbose error handling in the call_chat function
            try:
                create_args = {
                    "model": model_name_or_path,
                    "messages": [
                        {"role": "system", "content": system_messages},
                        {"role": "user", "content": user_message},
                    ],
                    **additional_args,
                    **request_args,
                }
                
                # Only add temperature and top_p if they're not None
                if top_p_param is not None:
                    create_args["top_p"] = top_p_param
                
                response = client.chat.completions.create(**create_args)
            except Exception as e:
                print(f"Error calling OpenAI API with model {model_name_or_path}: {e}")
                print(f"Full error details: {str(e)}")
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    print(f"Response content: {e.response.text}")
                raise e
        
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = calc_cost(response.model, input_tokens, output_tokens)
        return response, cost
    except Exception as e:
        if hasattr(e, 'code') and e.code == "context_length_exceeded":
            print("Context length exceeded")
            return None
        print(f"Error calling OpenAI API with model {model_name_or_path}: {e}")
        raise e

def call_responses_api(model_name_or_path, inputs, temperature, top_p, instance_id=None, **model_args):
    """
    Calls the OpenAI Responses API for o1 series models.
    """
    logger.info(f"Making responses API call for instance {instance_id}")
    system_messages = inputs.split("\n", 1)[0]
    user_message = inputs.split("\n", 1)[1]
    
    # Log input messages to JSON file
    input_log = {
        "instance_id": instance_id,
        "model": model_name_or_path,
        "system_message": system_messages,
        "user_message": user_message,
        "timestamp": datetime.now().isoformat()
    }
    
    # Create logs directory if it doesn't exist
    os.makedirs("openai_logs", exist_ok=True)
    log_file = "openai_logs/responses_input_messages.json"
    
    # Append input messages to JSONL file
    with open(log_file, "a") as f:
        json.dump(input_log, f)
        f.write("\n")
    
    openai_key = os.environ.get("OPENAI_API_KEY", None)
    if openai_key is None:
        raise ValueError(
            "Must provide an api key. Expected in OPENAI_API_KEY environment variable."
        )
    
    client = OpenAI(api_key=openai_key)
    
    # Prepare additional arguments
    request_args = model_args.copy()
    additional_args = {}
    
    # Handle max tokens parameter based on model type
    if model_name_or_path.startswith("gpt-4.1"):
        # GPT-4.1 supports a larger output window of 32,768 tokens
        request_args["max_tokens"] = 32_768
    elif not "max_tokens" in request_args:
        request_args["max_tokens"] = 16_384

    if model_name_or_path.startswith("gpt-5"):
        request_args["max_output_tokens"] = 128_000
        request_args.pop("max_tokens", None)

    # Special handling for O-level models
    if model_name_or_path.startswith("o1") or model_name_or_path.startswith("o3") or model_name_or_path.startswith("o4") or model_name_or_path.startswith("gpt-5"):
        # O-level models don't support temperature parameter
        # Don't pass temperature or top_p
        temperature_param = None
        top_p_param = None
    else:
        # For other models, use the provided temperature and top_p
        temperature_param = temperature
        top_p_param = top_p
    
    try:
        # Print instructions before making API call
        response = client.responses.create(
            model=model_name_or_path,
            input=user_message,
            instructions=system_messages,
            temperature=temperature_param,
            top_p=top_p_param,
            reasoning={
                "effort": "high"
            },
            **request_args,
        )
        
        # Extract text content from the response
        output_text = response.output_text if hasattr(response, 'output_text') else ""
        if not output_text and response.output:
            # Extract text from the output array if available
            for item in response.output:
                if item.type == "message" and item.content:
                    for content_part in item.content:
                        if content_part.type == "output_text":
                            output_text += content_part.text
        
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = calc_cost(model_name_or_path, input_tokens, output_tokens)
        
        # Convert response to a format similar to ChatCompletion for consistency
        chat_completion_like = {
            "choices": [
                {
                    "message": {"content": output_text},
                }
            ],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            },
            "model": model_name_or_path
        }
        
        return chat_completion_like, cost
    except Exception as e:
        print(f"Error calling OpenAI Responses API with model {model_name_or_path}: {e}")
        print(f"Full error details: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Response content: {e.response.text}")
        raise e

@retry(wait=wait_random_exponential(min=30, max=600), stop=stop_after_attempt(3))
def call_chat_with_validation(model_name_or_path, inputs, use_azure, temperature, top_p, output_dir=None, instance_id=None, **model_args):
    """
    Calls the OpenAI Chat API and validates the response patch. Retries on validation failure.
    Returns (response, cost, patch_text) tuple if successful, or (None, 0, None) if all attempts fail.
    """
    response, cost = call_chat(model_name_or_path, inputs, use_azure, temperature, top_p, instance_id=instance_id, **model_args)
    if response is None:
        return None, 0, None
        
    completion = response.choices[0].message.content
    patch_text, error_msg = validate_and_extract_patch(
        completion,
        output_dir=output_dir,
        instance_id=instance_id
    )
    
    if patch_text is None:
        # Validation failed - raise exception to trigger retry
        raise ValueError(f"Patch validation failed: {error_msg}")
        
    return response, cost, patch_text

@retry(wait=wait_random_exponential(min=30, max=600), stop=stop_after_attempt(3))
def call_responses_with_validation(model_name_or_path, inputs, temperature, top_p, output_dir=None, instance_id=None, **model_args):
    """
    Calls the OpenAI Responses API and validates the response patch. Retries on validation failure.
    Returns (response, cost, patch_text) tuple if successful, or (None, 0, None) if all attempts fail.
    """
    response, cost = call_responses_api(model_name_or_path, inputs, temperature, top_p, instance_id=instance_id, **model_args)
    if response is None:
        print(f"Responses api returned None")
        return None, 0, None

    completion = response["choices"][0]["message"]["content"]
    patch_text, error_msg = validate_and_extract_patch(
        completion,
        output_dir=output_dir,
        instance_id=instance_id
    )
    
    if patch_text is None:
        # Validation failed - raise exception to trigger retry
        raise ValueError(f"Patch validation failed: {error_msg}")
        
    return response, cost, patch_text

def openai_inference(
    test_dataset,
    model_name_or_path,
    output_file,
    model_args,
    existing_ids,
    max_cost,
):
    """
    Run inference on test dataset using OpenAI API with parallel processing.
    """
    # Initialize API token
    openai_key = os.environ.get("OPENAI_API_KEY", None)
    if openai_key is None:
        raise ValueError(
            "Must provide an api key. Expected in OPENAI_API_KEY environment variable."
        )
    
    print(f"Using OpenAI key {'*' * max(0, len(openai_key)-5) + openai_key[-5:]}")
    
    # Filter the dataset to include only instances that fit within the context window
    encoding = model_name_or_path  # Pass the model name instead of the encoding object
    print(f"Model name: {model_name_or_path}")
    print(f"Model limits: {MODEL_LIMITS[model_name_or_path]}")
    test_dataset = test_dataset.filter(
        lambda x: gpt_tokenize(x["text"], encoding) <= MODEL_LIMITS[model_name_or_path],
        desc="Filtering",
        load_from_cache_file=False,
    )
    
    temperature = model_args.pop("temperature", 0)
    top_p = model_args.pop("top_p", 1)
    use_azure = False
    print(f"Using temperature={temperature}, top_p={top_p}")
    
    basic_args = {
        "model_name_or_path": model_name_or_path,
    }
    
    # Set up for parallel processing - use more workers for GPT-4.1 which has higher throughput
    max_workers = model_args.pop("max_workers", 10)  # Default to 10 parallel workers
    max_concurrent_requests = model_args.pop("max_concurrent_requests", 10)  # Default to 5 concurrent API calls
    
    # Increase workers for GPT-4.1
    if model_name_or_path.startswith("gpt-4.1"):
        max_workers = model_args.pop("max_workers", 20)  # Use more workers for GPT-4.1
        max_concurrent_requests = model_args.pop("max_concurrent_requests", 10)  # Use more concurrent requests
    
    # Prepare data for parallel processing
    data_to_process = []
    for datum in test_dataset:
        instance_id = datum["instance_id"]
        if instance_id in existing_ids:
            continue
            
        output_dict = {"instance_id": instance_id}
        output_dict.update(basic_args)
        output_dict["text"] = f"{datum['text']}\n\n"
        data_to_process.append((instance_id, output_dict, model_args.copy()))
    
    if not data_to_process:
        logger.info(f"No new instances to process for {model_name_or_path}")
        return 0
    
    total_cost = 0
    processed_count = 0
    
    # Create thread-safe locks for shared resources
    output_lock = threading.Lock()
    cost_lock = threading.Lock()
    
    # Semaphore to limit concurrent API requests
    api_semaphore = threading.Semaphore(max_concurrent_requests)
    
    # Flag to signal early termination
    stop_processing = threading.Event()
    
    # Progress bar
    pbar = tqdm(total=len(data_to_process), desc=f"Inference for {model_name_or_path}")
    
    def process_instance(args):
        """Worker function to process a single instance with retry logic"""
        nonlocal total_cost, processed_count
        
        instance_id, output_dict, instance_args = args
        output_dir = os.path.dirname(output_file)
        
        # Skip if we've reached max cost
        if stop_processing.is_set():
            return None
        
        # Limit concurrent API requests
        with api_semaphore:
            retry_attempts = 0
            max_retries = 3
            
            while retry_attempts < max_retries and not stop_processing.is_set():
                try:
                    # Choose appropriate API based on model name
                    if output_dict["model_name_or_path"].startswith("o1") or output_dict["model_name_or_path"].startswith("gpt-5"):
                        response, cost, patch_text = call_responses_with_validation(
                            output_dict["model_name_or_path"],
                            output_dict["text"],
                            temperature,
                            top_p,
                            output_dir=output_dir,
                            instance_id=instance_id,
                            **instance_args,
                        )
                    else:
                        response, cost, patch_text = call_chat_with_validation(
                            output_dict["model_name_or_path"],
                            output_dict["text"],
                            use_azure,
                            temperature,
                            top_p,
                            output_dir=output_dir,
                            instance_id=instance_id,
                            **instance_args,
                        )
                    
                    # Skip if no valid response
                    if response is None:
                        logger.warning(f"[{instance_id}] Generated invalid response")
                        break
                    
                    # Store the validated response
                    if output_dict["model_name_or_path"].startswith("o1") or output_dict["model_name_or_path"].startswith("gpt-5"):
                        output_dict["full_output"] = response["choices"][0]["message"]["content"]
                    else:
                        output_dict["full_output"] = response.choices[0].message.content
                    
                    output_dict["model_patch"] = patch_text
                    
                    # Update costs and write output in a thread-safe way
                    with cost_lock:
                        total_cost += cost
                        current_cost = total_cost
                        
                        # Check if we've hit max cost
                        if max_cost is not None and current_cost >= max_cost:
                            stop_processing.set()
                    
                    # Write to output file
                    with output_lock:
                        with open(output_file, "a+") as f:
                            print(json.dumps(output_dict), file=f, flush=True)
                        
                        # Log cost occasionally
                        with cost_lock:
                            processed_count += 1
                            if processed_count % 5 == 0:  # Log every 5 completed instances
                                print(f"Processed {processed_count}/{len(data_to_process)}, Total Cost: ${current_cost:.4f}")
                    
                    return True
                    
                except Exception as e:
                    retry_attempts += 1
                    # Check for rate limit errors
                    if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                        wait_time = min(2 ** retry_attempts, 60)  # Exponential backoff capped at 60 seconds
                        logger.warning(f"[{instance_id}] Rate limit hit, retrying in {wait_time}s (attempt {retry_attempts}/{max_retries})")
                        time.sleep(wait_time)
                    elif retry_attempts < max_retries:
                        wait_time = min(2 ** retry_attempts, 30)
                        logger.warning(f"[{instance_id}] Error: {e}, retrying in {wait_time}s (attempt {retry_attempts}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        # For other errors on last attempt, log and break
                        logger.error(f"[{instance_id}] Error: {e}")
                        traceback.print_exc()
                        break
            
            return False
    
    try:
        print(f"Processing {len(data_to_process)} instances with {max_workers} workers")
        
        # Process instances in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks to the executor
            future_to_instance = {
                executor.submit(process_instance, args): args[0]  # Map future to instance_id
                for args in data_to_process
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_instance):
                instance_id = future_to_instance[future]
                try:
                    result = future.result()
                    if stop_processing.is_set():
                        logger.info(f"Skipping remaining instances due to max cost or interrupt")
                        # Cancel any pending futures
                        for pending_future in future_to_instance:
                            if not pending_future.done():
                                pending_future.cancel()
                except Exception as e:
                    logger.error(f"[{instance_id}] Worker thread error: {e}")
                    traceback.print_exc()
                
                # Update progress bar
                pbar.update(1)
                
                # Check for early termination
                if stop_processing.is_set():
                    break
    
    finally:
        pbar.close()
    
    print(f"Completed OpenAI inference for {model_name_or_path}")
    print(f"Processed {processed_count}/{len(data_to_process)} instances")
    print(f"Total Cost: ${total_cost:.4f}")
    
    return total_cost


#####################################
#          Anthropic API            #
#####################################

def call_anthropic(
    inputs, anthropic, model_name_or_path, temperature, top_p, instance_id=None, **model_args
):
    """
    Calls the anthropic API to generate completions for the given inputs.
    """
    logger.info(f"Making API call for instance {instance_id}")
    try:
        completion = anthropic.completions.create(
            model=model_name_or_path,
            max_tokens_to_sample=8192,
            prompt=inputs,
            temperature=temperature,
            top_p=top_p,
            **model_args,
        )
        response = completion.completion
        input_tokens = anthropic.count_tokens(inputs)
        output_tokens = anthropic.count_tokens(response)
        cost = calc_cost(model_name_or_path, input_tokens, output_tokens)
        return completion, cost
    except Exception as e:
        logger.error(e)
        logger.error(f"Inputs: {inputs}")
        traceback.print_exc()
        time.sleep(20)
        return None

def call_anthropic_v2_streaming(
    inputs, anthropic, model_name_or_path, temperature, top_p, instance_id=None, **model_args
):
    """
    Calls the anthropic API with streaming enabled for handling longer responses.
    Returns the complete response accumulated from the stream.
    """
    logger.info(f"Making streaming API call for instance {instance_id}")
    system_messages = inputs.split("\n", 1)[0]
    user_message = inputs.split("\n", 1)[1]
    
    # Check if using the thinking version of Claude 3.7 Sonnet
    using_thinking = "-thinking" in model_name_or_path or "claude-sonnet-4-20250514" in model_name_or_path or "claude-opus-4-20250514" in model_name_or_path or "claude-opus-4-1-20250805" in model_name_or_path
    # Extract the base model name without the "-thinking" suffix
    base_model_name = model_name_or_path.replace("-thinking", "")

    try:
        messages = [
            {"role": "user", "content": user_message},
        ]
        
        request_args = {
            "messages": messages,
            "model": base_model_name,
            "system": system_messages,
            "stream": True,
        }
        
        # Add thinking parameters if using the thinking version
        if using_thinking:
            # When thinking is enabled, temperature must be set to 1
            request_args["temperature"] = 1.0
            # Don't include top_p when thinking is enabled
        else:
            # Only add temperature and top_p for non-thinking models
            request_args["temperature"] = temperature
            request_args["top_p"] = top_p
            
        # Add any remaining model_args
        request_args.update(model_args)
        
        logger.info(f"Max tokens: {request_args['max_tokens']}")
        if using_thinking:
            logger.info(f"Thinking budget: {request_args['thinking']['budget_tokens']}")
        
        # Create streaming request
        stream = anthropic.messages.create(**request_args)
        
        # Accumulate the response content
        accumulated_content = []
        accumulated_text = ""
        thinking_content = []
        
        # Process the stream
        for event in stream:
            if event.type == "content_block_delta":
                # Handle content block deltas
                if event.delta.type == "text_delta":
                    # For normal text content
                    accumulated_text += event.delta.text
                elif event.delta.type == "thinking_delta" and hasattr(event.delta, "thinking"):
                    # For thinking content
                    thinking_content.append(event.delta.thinking)
            elif event.type == "content_block_start":
                # Initialize a new content block
                if hasattr(event, "content_block") and event.content_block.type == "text":
                    accumulated_text = ""
            elif event.type == "content_block_stop":
                # Finalize a content block
                if hasattr(event, "content_block") and event.content_block.type == "text":
                    accumulated_content.append({
                        "type": "text",
                        "text": accumulated_text
                    })
        
        # Write accumulated content to file periodically
        if instance_id and len(accumulated_text) > 0 and len(accumulated_text) % 1000 == 0:
            output_path = os.path.join("anthropic_completions", f"{instance_id}.txt")
            os.makedirs("anthropic_completions", exist_ok=True)
            with open(output_path, "w") as f:
                f.write(accumulated_text)
        
        # Calculate cost
        return accumulated_text, 0
    except Exception as e:
        logger.error(e)
        logger.error(f"Inputs: {inputs}")
        traceback.print_exc()
        time.sleep(20)
        return None

@retry(wait=wait_random_exponential(min=60, max=600), stop=stop_after_attempt(1))
def call_anthropic_v2_streaming_with_validation(
    inputs, anthropic, model_name_or_path, temperature, top_p, output_dir=None, instance_id=None, **model_args
):
    """
    Calls the Anthropic v2 API with streaming enabled and validates the response patch.
    Retries on validation failure.
    Returns (response, cost, patch_text) tuple if successful, or (None, 0, None) if all attempts fail.
    """
    logger.info(f"Making streaming API call for instance {instance_id}")
    response, cost = call_anthropic_v2_streaming(inputs, anthropic, model_name_or_path, temperature, top_p, instance_id=instance_id, **model_args)
    if response is None:
        return None, 0, None
    
    # For models with thinking, get only the text content for validation
    if "-thinking" in model_name_or_path or "claude-sonnet-4-20250514" in model_name_or_path or "claude-opus-4-20250514" in model_name_or_path or "claude-opus-4-1-20250805" in model_name_or_path:
        completion = response
    else:
        completion = response

    # Create directory if it doesn't exist
    os.makedirs("./anthropic_completions", exist_ok=True)
    
    # Save completion to file
    completion_file = f"./anthropic_completions/{instance_id}.txt"
    with open(completion_file, "w") as f:
        f.write(completion)
    logger.info(f"Saved Anthropic completion to {completion_file}")
        
    patch_text, error_msg = validate_and_extract_patch(
        completion,
        output_dir=output_dir,
        instance_id=instance_id
    )
    
    if patch_text is None:
        # Validation failed - raise exception to trigger retry
        raise ValueError(f"Patch validation failed: {error_msg}")
        
    return response, cost, patch_text

def anthropic_inference(
    test_dataset,
    model_name_or_path,
    output_file,
    model_args,
    existing_ids,
    max_cost,
):
    """
    Runs inference on a dataset using the anthropic API with parallel processing.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", None)
    if api_key is None:
        raise ValueError(
            "Must provide an api key. Expected in ANTHROPIC_API_KEY environment variable."
        )
    print(f"Using Anthropic key {'*' * max(0, len(api_key)-5) + api_key[-5:]}")
    anthropic = Anthropic(api_key=api_key)
    
    # Check if using the thinking version
    using_thinking = "-thinking" in model_name_or_path or "claude-sonnet-4-20250514" in model_name_or_path or "claude-opus-4-20250514" in model_name_or_path or "claude-opus-4-1-20250805" in model_name_or_path
    max_tokens = 32_000
    thinking_budget = 16_000
    
    # Calculate available tokens based on model configuration
    model_args["max_tokens"] = max_tokens
    if using_thinking:
        model_args["thinking"] = {
            "type": "enabled",
            "budget_tokens": thinking_budget
        }
    available_tokens = MODEL_LIMITS[model_name_or_path] - max_tokens
    
    def check_tokens(text):
        try:
            tokens = claude_tokenize(text, anthropic)
            return tokens <= available_tokens
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return False
    
    test_dataset = test_dataset.filter(
        lambda x: check_tokens(x["text"]),
        desc="Filtering",
        load_from_cache_file=False,
    )
    temperature = model_args.pop("temperature", 0.2)
    top_p = model_args.pop("top_p", 0.95 if temperature > 0 else 1)
    print(f"Using temperature={temperature}, top_p={top_p}")
    basic_args = {
        "model_name_or_path": model_name_or_path,
    }
    
    # Set up for parallel processing
    max_workers = model_args.pop("max_workers", 10)  # Default to 10 parallel workers
    max_concurrent_requests = model_args.pop("max_concurrent_requests", 5)  # Default to 5 concurrent API calls
    
    # Define the token threshold for when to use streaming
    streaming_token_threshold = 16000  # Use streaming for inputs with more than 16K tokens
    
    # Prepare data for parallel processing
    data_to_process = []
    for datum in test_dataset:
        instance_id = datum["instance_id"]
        if instance_id in existing_ids:
            continue
            
        output_dict = {"instance_id": instance_id}
        output_dict.update(basic_args)
        output_dict["text_inputs"] = f"{datum['text']}\n"
        
        # Count tokens in the input to determine whether to use streaming
        try:
            token_count = claude_tokenize(datum["text"], anthropic)
            output_dict["use_streaming"] = token_count > streaming_token_threshold
            logger.info(f"Instance {instance_id} has {token_count} tokens, {'using' if output_dict['use_streaming'] else 'not using'} streaming")
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            output_dict["use_streaming"] = False
            
        data_to_process.append((instance_id, output_dict, model_args.copy()))
    
    if not data_to_process:
        logger.info(f"No new instances to process for {model_name_or_path}")
        return 0
    
    total_cost = 0
    processed_count = 0
    
    # Create thread-safe locks for shared resources
    output_lock = threading.Lock()
    cost_lock = threading.Lock()
    
    # Semaphore to limit concurrent API requests
    api_semaphore = threading.Semaphore(max_concurrent_requests)
    
    # Flag to signal early termination
    stop_processing = threading.Event()
    
    # Progress bar
    pbar = tqdm(total=len(data_to_process), desc=f"Inference for {model_name_or_path}")
    
    def process_instance(args):
        """Worker function to process a single instance with retry logic"""
        nonlocal total_cost, processed_count
        
        instance_id, output_dict, instance_args = args
        output_dir = os.path.dirname(output_file)
        
        # Skip if we've reached max cost
        if stop_processing.is_set():
            return None
        
        # Limit concurrent API requests
        with api_semaphore:
            max_retries = 1
            retry_attempts = 0
            
            while retry_attempts < max_retries and not stop_processing.is_set():
                try:
                    # Use streaming for longer responses
                    logger.info(f"[{instance_id}] Using streaming API")
                    response, cost, patch_text = call_anthropic_v2_streaming_with_validation(
                        output_dict["text_inputs"],
                        anthropic,
                        model_name_or_path,
                        temperature,
                        top_p,
                        output_dir=output_dir,
                        instance_id=instance_id,
                        **model_args,
                    )
                    
                    # Skip if no valid response
                    if response is None:
                        logger.warning(f"[{instance_id}] Generated invalid response")
                        break
                    
                    # Extract the text content from the response
                    # if using_thinking:
                    #     # For models with thinking, get only the text content for the output
                    #     text_content = ""
                    #     thinking_content = []
                        
                    #     for content_block in response.content:
                    #         if content_block.type == "text":
                    #             text_content += content_block.text
                    #         elif content_block.type == "thinking":
                    #             thinking_content.append(content_block.thinking)
                        
                    #     output_dict["full_output"] = text_content
                    #     output_dict["thinking_output"] = thinking_content
                    # else:
                    #     # For normal models, just get the text content

                    output_dict["full_output"] = response
                    output_dict["model_patch"] = patch_text
                    
                    # Update costs and write output in a thread-safe way
                    with cost_lock:
                        total_cost += cost
                        current_cost = total_cost
                        
                        # Check if we've hit max cost
                        if max_cost is not None and current_cost >= max_cost:
                            stop_processing.set()
                    
                    # Write to output file
                    with output_lock:
                        with open(output_file, "a+") as f:
                            print(json.dumps(output_dict), file=f, flush=True)
                        
                        # Log cost occasionally
                        with cost_lock:
                            processed_count += 1
                            if processed_count % 5 == 0:  # Log every 5 completed instances
                                print(f"Processed {processed_count}/{len(data_to_process)}, Total Cost: ${current_cost:.4f}")
                    
                    return True
                    
                except Exception as e:
                    retry_attempts += 1
                    # Check for rate limit errors
                    if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                        wait_time = min(2 ** retry_attempts, 60)  # Exponential backoff capped at 60 seconds
                        logger.warning(f"[{instance_id}] Rate limit hit, retrying in {wait_time}s (attempt {retry_attempts}/{max_retries})")
                        time.sleep(wait_time)
                    elif retry_attempts < max_retries:
                        wait_time = min(2 ** retry_attempts, 30)
                        logger.warning(f"[{instance_id}] Error: {e}, retrying in {wait_time}s (attempt {retry_attempts}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        # For other errors on last attempt, log and break
                        logger.error(f"[{instance_id}] Error: {e}")
                        traceback.print_exc()
                        break
            
            return False
    
    try:
        print(f"Processing {len(data_to_process)} instances with {max_workers} workers")
        
        # Process instances in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks to the executor
            future_to_instance = {
                executor.submit(process_instance, args): args[0]  # Map future to instance_id
                for args in data_to_process
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_instance):
                instance_id = future_to_instance[future]
                try:
                    result = future.result()
                    if stop_processing.is_set():
                        logger.info(f"Skipping remaining instances due to max cost or interrupt")
                        # Cancel any pending futures
                        for pending_future in future_to_instance:
                            if not pending_future.done():
                                pending_future.cancel()
                except Exception as e:
                    logger.error(f"[{instance_id}] Worker thread error: {e}")
                    traceback.print_exc()
                
                # Update progress bar
                pbar.update(1)
                
                # Check for early termination
                if stop_processing.is_set():
                    break
    
    finally:
        pbar.close()
    
    print(f"Completed Anthropic inference for {model_name_or_path}")
    print(f"Processed {processed_count}/{len(data_to_process)} instances")
    print(f"Total Cost: ${total_cost:.4f}")
    
    return total_cost


#####################################
#          Fireworks API            #
#####################################

def call_fireworks(model_name_or_path, inputs, temperature, top_p, instance_id=None, **model_args):
    """
    Calls the Fireworks AI API to generate completions for the given inputs.
    """
    logger.info(f"Making API call for instance {instance_id}")
    system_messages = inputs.split("\n", 1)[0]
    user_message = inputs.split("\n", 1)[1]
    
    fireworks_key = os.environ.get("FIREWORKS_API_KEY", None)
    if fireworks_key is None:
        raise ValueError(
            "Must provide an api key. Expected in FIREWORKS_API_KEY environment variable."
        )
    
    # Get the full Fireworks model path
    if model_name_or_path not in FIREWORKS_MODEL_PATHS:
        raise ValueError(f"Unknown Fireworks model: {model_name_or_path}")
    full_model_path = FIREWORKS_MODEL_PATHS[model_name_or_path]
    
    # Create an OpenAI client configured for Fireworks
    client = OpenAI(
        api_key=fireworks_key,
        base_url="https://api.fireworks.ai/inference/v1"
    )
    
    # Additional parameters for DeepSeek models
    additional_args = {}
    if "r1" in model_name_or_path.lower():
        additional_args["reasoning_effort"] = "high"
    
    # Add max_tokens to model_args
    model_args = model_args.copy()
    model_args["max_tokens"] = 20_000

    try:
        response = client.chat.completions.create(
            model=full_model_path,
            messages=[
                {"role": "system", "content": system_messages},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            top_p=top_p,
            **additional_args,
            **model_args,
        )
        
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = calc_cost(model_name_or_path, input_tokens, output_tokens)
        return response, cost
    except openai.BadRequestError as e:
        # Check if this is a context length error
        if "too long" in str(e).lower() or "maximum context length" in str(e).lower():
            logger.warning(f"Context length exceeded for Fireworks API: {e}")
            return None, 0  # Return None to indicate this instance should be skipped
        # Re-raise other BadRequestError types
        logger.error(f"Bad request to Fireworks API: {e}")
        raise e
    except Exception as e:
        logger.error(f"Error calling Fireworks API: {e}")
        logger.error(f"Inputs: {inputs}")
        traceback.print_exc()
        raise e

@retry(wait=wait_random_exponential(min=30, max=600), stop=stop_after_attempt(3))
def call_fireworks_with_validation(model_name_or_path, inputs, temperature, top_p, output_dir=None, instance_id=None, **model_args):
    """
    Calls the Fireworks AI API and validates the response patch. Retries on validation failure.
    Returns (response, cost, patch_text) tuple if successful, or (None, 0, None) if all attempts fail.
    """
    logger.info(f"Making API call for instance {instance_id}")
    response, cost = call_fireworks(model_name_or_path, inputs, temperature, top_p, instance_id=instance_id, **model_args)
    if response is None:
        return None, 0, None
        
    completion = response.choices[0].message.content
    patch_text, error_msg = validate_and_extract_patch(
        completion,
        output_dir=output_dir,
        instance_id=instance_id
    )
    
    if patch_text is None:
        # Validation failed - raise exception to trigger retry
        raise ValueError(f"Patch validation failed: {error_msg}")
        
    return response, cost, patch_text

def fireworks_inference(
    test_dataset,
    model_name_or_path,
    output_file,
    model_args,
    existing_ids,
    max_cost,
):
    """
    Runs inference on a dataset using the Fireworks AI API.
    """
    # Initialize the Fireworks API token
    api_key = os.environ.get("FIREWORKS_API_KEY", None)
    if api_key is None:
        raise ValueError(
            "Must provide an api key. Expected in FIREWORKS_API_KEY environment variable."
        )
    
    print(f"Using Fireworks AI key {'*' * max(0, len(api_key)-5) + api_key[-5:]}")
    
    # Filter the dataset to include only instances that fit within the context window
    encoding = model_name_or_path  # Pass the model name instead of the encoding object
    print(f"Model name: {model_name_or_path}")
    print(f"Model limits: {MODEL_LIMITS[model_name_or_path]}")
    test_dataset = test_dataset.filter(
        lambda x: gpt_tokenize(x["text"], encoding) <= MODEL_LIMITS[model_name_or_path],
        desc="Filtering",
        load_from_cache_file=False,
    )
    
    temperature = model_args.pop("temperature", 0.2)
    top_p = model_args.pop("top_p", 0.95 if temperature > 0 else 1)
    print(f"Using temperature={temperature}, top_p={top_p}")
    
    basic_args = {
        "model_name_or_path": model_name_or_path,
    }
    
    total_cost = 0
    print(f"Filtered to {len(test_dataset)} instances")
    
    with open(output_file, "a+") as f:
        for datum in tqdm(test_dataset, desc=f"Inference for {model_name_or_path}"):
            instance_id = datum["instance_id"]
            if instance_id in existing_ids:
                continue
            
            output_dict = {"instance_id": instance_id}
            output_dict.update(basic_args)
            output_dict["text"] = f"{datum['text']}\n\n"
            
            try:
                response, cost, patch_text = call_fireworks_with_validation(
                    model_name_or_path,
                    output_dict["text"],
                    temperature,
                    top_p,
                    output_dir=os.path.dirname(output_file),
                    instance_id=instance_id,
                    **model_args,
                )
                
                # Skip this instance if response is None (context length exceeded)
                if response is None:
                    logger.warning(f"{instance_id} failed")
                    continue
                
                total_cost += cost
                print(f"Total Cost: {total_cost:.2f}")
                
                output_dict["full_output"] = response.choices[0].message.content
                output_dict["model_patch"] = patch_text
                
                print(json.dumps(output_dict), file=f, flush=True)
                
                if max_cost is not None and total_cost >= max_cost:
                    print(f"Reached max cost {max_cost}, exiting")
                    break
                
            except Exception as e:
                logger.error(f"Error processing instance {instance_id}: {e}")
                traceback.print_exc()
                continue


#####################################
#          Gemini API                #
#####################################

def call_gemini(model_name_or_path, inputs, temperature, top_p, instance_id=None, **model_args):
    """
    Calls the Gemini API to generate completions for the given inputs.
    """
    logger.info(f"Making API call for instance {instance_id}")
    system_messages = inputs.split("\n", 1)[0]
    user_message = inputs.split("\n", 1)[1]
    
    gemini_key = os.environ.get("GEMINI_API_KEY", None)
    if gemini_key is None:
        logger.error(f"No Gemini API key found")
        raise ValueError(
            "Must provide an api key. Expected in GEMINI_API_KEY environment variable."
        )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name_or_path}:generateContent"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Combine system and user messages
    combined_message = f"{system_messages}\n{user_message}"
    
    data = {
        "contents": [{
            "parts":[{"text": combined_message}]
        }],
        "generationConfig": {
            "temperature": temperature,
            "topP": top_p,
            "maxOutputTokens": 65_536
        }
    }
    
    # Add any additional model args
    if model_args:
        data["generationConfig"].update(model_args)
    
    try:
        import requests
        response = requests.post(
            f"{url}?key={gemini_key}",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        result = response.json()

        # Create directory if it doesn't exist
        os.makedirs("./gemini_completions", exist_ok=True)
        
        # Save completion to file
        completion_file = f"./gemini_completions/{instance_id}.json"
        with open(completion_file, "w") as f:
            f.write(json.dumps(result, indent=2))
        logger.info(f"Saved Gemini completion to {completion_file}")
        
        # Debug logging
        # logger.info("Gemini API Response Structure:")
        # logger.info(json.dumps(result, indent=2))
        
        # Check for error responses
        if "error" in result:
            logger.error(f"Gemini API returned error: {result['error']}")
            if "Rate limit" in str(result['error']):
                # Retry rate limit errors
                raise requests.exceptions.HTTPError("Rate limit exceeded")
            # For other API errors, return None to skip this instance
            return None, 0
            
        try:
            completion_text = result["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to extract completion text: {e}")
            logger.error("Response structure:")
            logger.error(json.dumps(result, indent=2))
            # Return None to skip this instance rather than crashing
            return None, 0
        
        # Get token counts from usage metadata
        usage = result.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)
        
        # Create a response object that matches our expected format
        response_obj = type('GeminiResponse', (), {
            'choices': [
                type('Choice', (), {
                    'message': type('Message', (), {
                        'content': completion_text
                    })()
                })()
            ],
            'usage': type('Usage', (), {
                'prompt_tokens': input_tokens,
                'completion_tokens': output_tokens,
                'total_tokens': usage.get("totalTokenCount", 0)
            })(),
            'model': result.get("modelVersion", model_name_or_path)
        })
        
        cost = calc_cost(model_name_or_path, input_tokens, output_tokens)
        return response_obj, cost
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error: {e}")
        logger.error(f"Response Status Code: {e.response.status_code}")
        logger.error(f"Response Headers: {e.response.headers}")
        try:
            error_content = e.response.json()
            logger.error(f"Error Response Content: {json.dumps(error_content, indent=2)}")
        except:
            logger.error(f"Raw Error Response: {e.response.text}")
            
        if e.response.status_code == 429:  # Rate limit error
            logger.warning("Rate limit hit, retrying...")
            raise e
        elif "content length" in str(e).lower():
            logger.warning("Content length exceeded")
            return None, 0
        else:
            raise e
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        logger.error(f"Request URL: {url}")
        logger.error(f"Request Headers: {headers}")
        logger.error(f"Request Data: {json.dumps(data, indent=2)}")
        traceback.print_exc()
        raise e

@retry(wait=wait_random_exponential(min=30, max=600), stop=stop_after_attempt(1))
def call_gemini_with_validation(model_name_or_path, inputs, temperature, top_p, output_dir=None, instance_id=None, **model_args):
    """
    Calls the Gemini API and validates the response patch. Retries on validation failure.
    Returns (response, cost, patch_text) tuple if successful, or (None, 0, None) if all attempts fail.
    """
    logger.info(f"Making API call for instance {instance_id}")
    response, cost = call_gemini(model_name_or_path, inputs, temperature, top_p, instance_id=instance_id, **model_args)
    if response is None:
        return None, 0, None
        
    completion = response.choices[0].message.content
    patch_text, error_msg = validate_and_extract_patch(
        completion,
        output_dir=output_dir,
        instance_id=instance_id
    )
    
    if patch_text is None:
        # Validation failed - raise exception to trigger retry
        logger.error(f"Gemini patch validation failed: {error_msg}")
        raise ValueError(f"Patch validation failed: {error_msg}")
        
    return response, cost, patch_text

def gemini_inference(
    test_dataset,
    model_name_or_path,
    output_file,
    model_args,
    existing_ids,
    max_cost,
):
    """
    Runs inference on a dataset using the Gemini API with parallel processing.
    """
    api_key = os.environ.get("GEMINI_API_KEY", None)
    if api_key is None:
        raise ValueError(
            "Must provide an api key. Expected in GEMINI_API_KEY environment variable."
        )
    
    print(f"Using Gemini API key {'*' * max(0, len(api_key)-5) + api_key[-5:]}")
    
    # Filter the dataset to include only instances that fit within the context window
    encoding = model_name_or_path  # Pass the model name instead of the encoding object
    print(f"Model name: {model_name_or_path}")
    print(f"Model limits: {MODEL_LIMITS[model_name_or_path]}")
    test_dataset = test_dataset.filter(
        lambda x: gpt_tokenize(x["text"], encoding) <= MODEL_LIMITS[model_name_or_path],
        desc="Filtering",
        load_from_cache_file=False,
    )
    
    temperature = model_args.pop("temperature", 0.2)
    top_p = model_args.pop("top_p", 0.95 if temperature > 0 else 1)
    print(f"Using temperature={temperature}, top_p={top_p}")
    
    basic_args = {
        "model_name_or_path": model_name_or_path,
    }
    
    # Set up for parallel processing
    max_workers = model_args.pop("max_workers", 10)  # Default to 10 parallel workers
    max_concurrent_requests = model_args.pop("max_concurrent_requests", 5)  # Default to 5 concurrent API calls
    
    # Prepare data for parallel processing
    data_to_process = []
    for datum in test_dataset:
        instance_id = datum["instance_id"]
        if instance_id in existing_ids:
            continue
            
        output_dict = {"instance_id": instance_id}
        output_dict.update(basic_args)
        output_dict["text"] = f"{datum['text']}\n\n"
        data_to_process.append((instance_id, output_dict, model_args.copy()))
    
    if not data_to_process:
        logger.info(f"No new instances to process for {model_name_or_path}")
        return 0
    
    total_cost = 0
    processed_count = 0
    
    # Create thread-safe locks for shared resources
    output_lock = threading.Lock()
    cost_lock = threading.Lock()
    
    # Semaphore to limit concurrent API requests
    api_semaphore = threading.Semaphore(max_concurrent_requests)
    
    # Flag to signal early termination
    stop_processing = threading.Event()
    
    # Progress bar
    pbar = tqdm(total=len(data_to_process), desc=f"Inference for {model_name_or_path}")
    
    def process_instance(args):
        """Worker function to process a single instance with retry logic"""
        nonlocal total_cost, processed_count
        
        instance_id, output_dict, instance_args = args
        output_dir = os.path.dirname(output_file)
        
        # Skip if we've reached max cost
        if stop_processing.is_set():
            return None
        
        # Limit concurrent API requests
        with api_semaphore:
            retry_attempts = 0
            max_retries = 3
            
            while retry_attempts < max_retries and not stop_processing.is_set():
                try:
                    response, cost, patch_text = call_gemini_with_validation(
                        model_name_or_path,
                        output_dict["text"],
                        temperature,
                        top_p,
                        output_dir=output_dir,
                        instance_id=instance_id,
                        **instance_args
                    )
                    
                    # Skip if no valid response
                    if response is None:
                        logger.warning(f"[{instance_id}] Generated invalid response")
                        break
                    
                    # Update the output dictionary with results
                    output_dict["full_output"] = response.choices[0].message.content
                    output_dict["model_patch"] = patch_text
                    
                    # Update costs and write output in a thread-safe way
                    with cost_lock:
                        total_cost += cost
                        current_cost = total_cost
                        
                        # Check if we've hit max cost
                        if max_cost is not None and current_cost >= max_cost:
                            stop_processing.set()
                    
                    # Write to output file
                    with output_lock:
                        with open(output_file, "a+") as f:
                            print(json.dumps(output_dict), file=f, flush=True)
                        
                        # Log cost occasionally
                        with cost_lock:
                            processed_count += 1
                            if processed_count % 5 == 0:  # Log every 5 completed instances
                                print(f"Processed {processed_count}/{len(data_to_process)}, Total Cost: ${current_cost:.4f}")
                    
                    return True
                    
                except Exception as e:
                    retry_attempts += 1
                    # Check for rate limit errors
                    if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                        wait_time = min(2 ** retry_attempts, 60)  # Exponential backoff capped at 60 seconds
                        logger.warning(f"[{instance_id}] Rate limit hit, retrying in {wait_time}s (attempt {retry_attempts}/{max_retries})")
                        time.sleep(wait_time)
                    elif retry_attempts < max_retries:
                        wait_time = min(2 ** retry_attempts, 30)
                        logger.warning(f"[{instance_id}] Error: {e}, retrying in {wait_time}s (attempt {retry_attempts}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        # For other errors on last attempt, log and break
                        logger.error(f"[{instance_id}] Error: {e}")
                        traceback.print_exc()
                        break
            
            return False
    
    try:
        print(f"Processing {len(data_to_process)} instances with {max_workers} workers")
        
        # Process instances in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks to the executor
            future_to_instance = {
                executor.submit(process_instance, args): args[0]  # Map future to instance_id
                for args in data_to_process
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_instance):
                instance_id = future_to_instance[future]
                try:
                    result = future.result()
                    if stop_processing.is_set():
                        logger.info(f"Skipping remaining instances due to max cost or interrupt")
                        # Cancel any pending futures
                        for pending_future in future_to_instance:
                            if not pending_future.done():
                                pending_future.cancel()
                except Exception as e:
                    logger.error(f"[{instance_id}] Worker thread error: {e}")
                    traceback.print_exc()
                
                # Update progress bar
                pbar.update(1)
                
                # Check for early termination
                if stop_processing.is_set():
                    break
    
    finally:
        pbar.close()
    
    print(f"Completed Gemini inference for {model_name_or_path}")
    print(f"Processed {processed_count}/{len(data_to_process)} instances")
    print(f"Total Cost: ${total_cost:.4f}")
    
    return total_cost


#####################################
#          TogetherAI API           #
#####################################

def call_together(model_name_or_path, inputs, temperature, top_p, instance_id=None, **model_args):
    """
    Calls the Together AI API to generate completions for the given inputs.
    Improved to handle rate limits and other errors better in parallel execution.
    """
    logger.info(f"Making API call for instance {instance_id}")
    system_messages = inputs.split("\n", 1)[0]
    user_message = inputs.split("\n", 1)[1]
    
    # Get Together API key
    together_key = os.environ.get("TOGETHER_API_KEY", None)
    if together_key is None:
        raise ValueError(
            "Must provide an api key. Expected in TOGETHER_API_KEY environment variable."
        )
    
    try:
        # Initialize the Together client
        client = Together(api_key=together_key)
        
        # Prepare request arguments
        request_args = model_args.copy()
        if "max_tokens" not in request_args:
            request_args["max_tokens"] = 16384
        
        # Check if model needs to be mapped to TogetherAI path
        actual_model_path = TOGETHER_MODEL_PATHS.get(model_name_or_path, model_name_or_path)
        logger.info(f"[{instance_id}] Using TogetherAI model: {actual_model_path}")
            
        response = client.chat.completions.create(
            model=actual_model_path,
            messages=[
                {"role": "system", "content": system_messages},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            top_p=top_p,
            **request_args,
        )
        
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        # Use the actual model path for cost calculation if it has cost defined,
        # otherwise fallback to the original model name
        cost_model = actual_model_path if actual_model_path in MODEL_COST_PER_INPUT else model_name_or_path
        cost = calc_cost(cost_model, input_tokens, output_tokens)
        
        logger.info(f"[{instance_id}] Successfully received response (input:{input_tokens}, output:{output_tokens})")
        return response, cost
    except Exception as e:
        # Check for specific error types for better handling
        error_msg = str(e).lower()
        
        # Handle rate limit errors - raise with specific message so calling code can retry
        if "rate limit" in error_msg or "too many requests" in error_msg or "429" in error_msg:
            rate_limit_error = ValueError(f"Rate limit exceeded: {str(e)}")
            rate_limit_error.is_rate_limit = True
            logger.warning(f"[{instance_id}] Hit rate limit: {str(e)}")
            raise rate_limit_error
            
        # Handle context length errors
        elif "context length" in error_msg or "too long" in error_msg:
            logger.warning(f"[{instance_id}] Context length exceeded: {str(e)}")
            return None, 0
            
        # Handle authorization errors
        elif "unauthorized" in error_msg or "authentication" in error_msg or "401" in error_msg:
            logger.error(f"[{instance_id}] Authentication error: {str(e)}")
            raise ValueError(f"TogetherAI authentication error: {str(e)}")
            
        # Handle model not found errors
        elif "model not found" in error_msg or "404" in error_msg:
            logger.error(f"[{instance_id}] Model not found: {str(e)}")
            raise ValueError(f"Model not found: {str(e)}. Check if '{actual_model_path}' is valid.")
            
        # Other errors
        else:
            logger.error(f"[{instance_id}] Error calling Together API: {str(e)}")
            traceback.print_exc()
            raise e

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3), retry=lambda e: hasattr(e, 'is_rate_limit') and e.is_rate_limit)
def call_together_with_validation(model_name_or_path, inputs, temperature, top_p, output_dir=None, instance_id=None, **model_args):
    """
    Calls the Together AI API and validates the response patch. 
    Retries automatically on validation failure or rate limits.
    Returns (response, cost, patch_text) tuple if successful, or (None, 0, None) if all attempts fail.
    """
    logger.info(f"Making API call with validation for instance {instance_id}")
    response, cost = call_together(model_name_or_path, inputs, temperature, top_p, instance_id=instance_id, **model_args)
    if response is None:
        return None, 0, None
        
    completion = response.choices[0].message.content
    patch_text, error_msg = validate_and_extract_patch(
        completion,
        output_dir=output_dir,
        instance_id=instance_id
    )
    
    if patch_text is None:
        # Validation failed - raise exception to trigger retry
        logger.warning(f"[{instance_id}] Patch validation failed: {error_msg}")
        raise ValueError(f"Patch validation failed: {error_msg}")
    
    logger.info(f"[{instance_id}] Successfully validated patch")   
    return response, cost, patch_text

def together_inference(
    test_dataset,
    model_name_or_path,
    output_file,
    model_args,
    existing_ids,
    max_cost,
):
    """
    Runs inference on a dataset using the Together AI API with parallel processing.
    """    
    # Initialize the Together API token
    api_key = os.environ.get("TOGETHER_API_KEY", None)
    if api_key is None:
        raise ValueError(
            "Must provide an api key. Expected in TOGETHER_API_KEY environment variable."
        )
    
    print(f"Using Together AI key {'*' * max(0, len(api_key)-5) + api_key[-5:]}")
    
    # Map the model name to the actual Together AI model path if needed
    actual_model_path = TOGETHER_MODEL_PATHS.get(model_name_or_path, model_name_or_path)
    logger.info(f"Using model {model_name_or_path} mapped to TogetherAI model: {actual_model_path}")
    
    # Use the appropriate model for context length limits
    limit_model = actual_model_path if actual_model_path in MODEL_LIMITS else model_name_or_path
    
    # Filter the dataset to include only instances that fit within the context window
    encoding = limit_model  # Pass the model name instead of the encoding object
    print(f"Model name: {model_name_or_path} (Using {limit_model} for context limits)")
    print(f"Model limits: {MODEL_LIMITS[limit_model]}")
    test_dataset = test_dataset.filter(
        lambda x: gpt_tokenize(x["text"], encoding) <= MODEL_LIMITS[limit_model],
        desc="Filtering",
        load_from_cache_file=False,
    )
    
    temperature = model_args.pop("temperature", 0.2)
    top_p = model_args.pop("top_p", 0.95 if temperature > 0 else 1)
    print(f"Using temperature={temperature}, top_p={top_p}")
    
    basic_args = {
        "model_name_or_path": model_name_or_path,
    }
    
    # Set up for parallel processing
    max_workers = model_args.pop("max_workers", 10)  # Default to 10 parallel workers
    max_concurrent_requests = model_args.pop("max_concurrent_requests", 5)  # Default to 5 concurrent API calls
    
    # Prepare data for parallel processing
    data_to_process = []
    for datum in test_dataset:
        instance_id = datum["instance_id"]
        if instance_id in existing_ids:
            continue
            
        output_dict = {"instance_id": instance_id}
        output_dict.update(basic_args)
        output_dict["text"] = f"{datum['text']}\n\n"
        data_to_process.append((instance_id, output_dict, model_args.copy()))
    
    if not data_to_process:
        logger.info(f"No new instances to process for {model_name_or_path}")
        return 0
    
    total_cost = 0
    processed_count = 0
    
    # Create thread-safe locks for shared resources
    output_lock = threading.Lock()
    cost_lock = threading.Lock()
    
    # Semaphore to limit concurrent API requests
    api_semaphore = threading.Semaphore(max_concurrent_requests)
    
    # Flag to signal early termination
    stop_processing = threading.Event()
    
    # Progress bar
    pbar = tqdm(total=len(data_to_process), desc=f"Inference for {model_name_or_path}")
    
    def process_instance(args):
        """Worker function to process a single instance with retry logic"""
        nonlocal total_cost, processed_count
        
        instance_id, output_dict, instance_args = args
        output_dir = os.path.dirname(output_file)
        
        # Skip if we've reached max cost
        if stop_processing.is_set():
            return None
        
        # Limit concurrent API requests
        with api_semaphore:
            retry_attempts = 0
            max_retries = 5
            
            while retry_attempts < max_retries and not stop_processing.is_set():
                try:
                    response, cost, patch_text = call_together_with_validation(
                        model_name_or_path,
                        output_dict["text"],
                        temperature,
                        top_p,
                        output_dir=output_dir,
                        instance_id=instance_id,
                        **instance_args
                    )
                    
                    # Skip if no valid response
                    if response is None:
                        logger.warning(f"[{instance_id}] Generated invalid response")
                        break
                    
                    # Update the output dictionary with results
                    output_dict["full_output"] = response.choices[0].message.content
                    output_dict["model_patch"] = patch_text
                    
                    # Update costs and write output in a thread-safe way
                    with cost_lock:
                        total_cost += cost
                        current_cost = total_cost
                        
                        # Check if we've hit max cost
                        if max_cost is not None and current_cost >= max_cost:
                            stop_processing.set()
                    
                    # Write to output file
                    with output_lock:
                        with open(output_file, "a+") as f:
                            print(json.dumps(output_dict), file=f, flush=True)
                        
                        # Log cost occasionally
                        with cost_lock:
                            processed_count += 1
                            if processed_count % 5 == 0:  # Log every 5 completed instances
                                print(f"Processed {processed_count}/{len(data_to_process)}, Total Cost: ${current_cost:.4f}")
                    
                    return True
                    
                except Exception as e:
                    # Check if it's a rate limit error
                    if hasattr(e, 'is_rate_limit') and e.is_rate_limit:
                        retry_attempts += 1
                        wait_time = min(2 ** retry_attempts, 60)  # Exponential backoff capped at 60 seconds
                        logger.warning(f"[{instance_id}] Rate limit hit, retrying in {wait_time}s (attempt {retry_attempts}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        # For other errors, log and break
                        logger.error(f"[{instance_id}] Error: {e}")
                        traceback.print_exc()
                        break
            
            return False
    
    try:
        print(f"Processing {len(data_to_process)} instances with {max_workers} workers")
        
        # Process instances in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks to the executor
            future_to_instance = {
                executor.submit(process_instance, args): args[0]  # Map future to instance_id
                for args in data_to_process
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_instance):
                instance_id = future_to_instance[future]
                try:
                    result = future.result()
                    if stop_processing.is_set():
                        logger.info(f"Skipping remaining instances due to max cost or interrupt")
                        # Cancel any pending futures
                        for pending_future in future_to_instance:
                            if not pending_future.done():
                                pending_future.cancel()
                except Exception as e:
                    logger.error(f"[{instance_id}] Worker thread error: {e}")
                    traceback.print_exc()
                
                # Update progress bar
                pbar.update(1)
                
                # Check for early termination
                if stop_processing.is_set():
                    break
    
    finally:
        pbar.close()
    
    print(f"Completed inference for {model_name_or_path}")
    print(f"Processed {processed_count}/{len(data_to_process)} instances")
    print(f"Total Cost: ${total_cost:.4f}")
    
    return total_cost


#####################################
#          Grok API                 #
#####################################

def call_grok(model_name_or_path, inputs, temperature, top_p, instance_id=None, **model_args):
    """
    Calls the xAI Grok API to generate completions for the given inputs.
    Uses OpenAI's client library with a custom base URL.
    """
    logger.info(f"Making API call for instance {instance_id}")
    system_messages = inputs.split("\n", 1)[0]
    user_message = inputs.split("\n", 1)[1]
    
    # Get Grok API keys
    grok_key = os.environ.get("GROK_API_KEY", None)
    if grok_key is None:
        raise ValueError(
            "Must provide an api key. Expected in GROK_API_KEY environment variable."
        )
    
    try:
        # Initialize the OpenAI client with xAI's base URL
        client = OpenAI(
            api_key=grok_key,
            base_url="https://api.x.ai/v1"
        )
        
        # Prepare request arguments
        request_args = model_args.copy()
        if "max_tokens" not in request_args:
            request_args["max_tokens"] = 16384
            
        # Call the chat completions API
        response = client.chat.completions.create(
            model=model_name_or_path,
            messages=[
                {"role": "system", "content": system_messages},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            top_p=top_p,
            **request_args,
        )
        
        # Extract tokens used
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        # Calculate cost
        cost = calc_cost(model_name_or_path, input_tokens, output_tokens)
        
        logger.info(f"[{instance_id}] Successfully received Grok response (input:{input_tokens}, output:{output_tokens})")
        return response, cost
        
    except Exception as e:
        # Handling different error types
        error_msg = str(e).lower()
        
        # Handle rate limit errors
        if "rate limit" in error_msg or "too many requests" in error_msg or "429" in error_msg:
            rate_limit_error = ValueError(f"Rate limit exceeded: {str(e)}")
            rate_limit_error.is_rate_limit = True
            logger.warning(f"[{instance_id}] Hit Grok rate limit: {str(e)}")
            raise rate_limit_error
            
        # Handle context length errors
        elif "context length" in error_msg or "too long" in error_msg:
            logger.warning(f"[{instance_id}] Context length exceeded: {str(e)}")
            return None, 0
            
        # Handle authorization errors
        elif "unauthorized" in error_msg or "authentication" in error_msg or "401" in error_msg:
            logger.error(f"[{instance_id}] Grok authentication error: {str(e)}")
            raise ValueError(f"Grok authentication error: {str(e)}")
            
        # Handle model not found errors
        elif "model not found" in error_msg or "404" in error_msg:
            logger.error(f"[{instance_id}] Model not found: {str(e)}")
            raise ValueError(f"Model not found: {str(e)}. Check if '{model_name_or_path}' is valid.")
            
        # Other errors
        else:
            logger.error(f"[{instance_id}] Error calling Grok API: {str(e)}")
            traceback.print_exc()
            raise e

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3), retry=lambda e: hasattr(e, 'is_rate_limit') and e.is_rate_limit)
def call_grok_with_validation(model_name_or_path, inputs, temperature, top_p, output_dir=None, instance_id=None, **model_args):
    """
    Calls the Grok API and validates the response patch. 
    Retries automatically on validation failure or rate limits.
    Returns (response, cost, patch_text) tuple if successful, or (None, 0, None) if all attempts fail.
    """
    logger.info(f"Making Grok API call with validation for instance {instance_id}")
    response, cost = call_grok(model_name_or_path, inputs, temperature, top_p, instance_id=instance_id, **model_args)
    if response is None:
        return None, 0, None
        
    completion = response.choices[0].message.content
    patch_text, error_msg = validate_and_extract_patch(
        completion,
        output_dir=output_dir,
        instance_id=instance_id
    )
    
    if patch_text is None:
        # Validation failed - raise exception to trigger retry
        logger.warning(f"[{instance_id}] Grok patch validation failed: {error_msg}")
        raise ValueError(f"Patch validation failed: {error_msg}")
    
    logger.info(f"[{instance_id}] Successfully validated Grok patch")   
    return response, cost, patch_text

def grok_inference(
    test_dataset,
    model_name_or_path,
    output_file,
    model_args,
    existing_ids,
    max_cost,
):
    """
    Runs inference on a dataset using the Grok API with parallel processing.
    """    
    # Initialize the Grok API token
    api_key = os.environ.get("GROK_API_KEY", None)
    if api_key is None:
        raise ValueError(
            "Must provide an api key. Expected in GROK_API_KEY environment variable."
        )
    
    print(f"Using xAI Grok key {'*' * max(0, len(api_key)-5) + api_key[-5:]}")
    
    # Filter the dataset to include only instances that fit within the context window
    encoding = model_name_or_path  # Pass the model name instead of the encoding object
    print(f"Model name: {model_name_or_path}")
    print(f"Model limits: {MODEL_LIMITS[model_name_or_path]}")
    test_dataset = test_dataset.filter(
        lambda x: gpt_tokenize(x["text"], encoding) <= MODEL_LIMITS[model_name_or_path],
        desc="Filtering",
        load_from_cache_file=False,
    )
    
    temperature = model_args.pop("temperature", 0.2)
    top_p = model_args.pop("top_p", 0.95 if temperature > 0 else 1)
    print(f"Using temperature={temperature}, top_p={top_p}")
    
    basic_args = {
        "model_name_or_path": model_name_or_path,
    }
    
    # Set up for parallel processing
    max_workers = model_args.pop("max_workers", 10)  # Default to 10 parallel workers
    max_concurrent_requests = model_args.pop("max_concurrent_requests", 5)  # Default to 5 concurrent API calls
    
    # Prepare data for parallel processing
    data_to_process = []
    for datum in test_dataset:
        instance_id = datum["instance_id"]
        if instance_id in existing_ids:
            continue
            
        output_dict = {"instance_id": instance_id}
        output_dict.update(basic_args)
        output_dict["text"] = f"{datum['text']}\n\n"
        data_to_process.append((instance_id, output_dict, model_args.copy()))
    
    if not data_to_process:
        logger.info(f"No new instances to process for {model_name_or_path}")
        return 0
    
    total_cost = 0
    processed_count = 0
    
    # Create thread-safe locks for shared resources
    output_lock = threading.Lock()
    cost_lock = threading.Lock()
    
    # Semaphore to limit concurrent API requests
    api_semaphore = threading.Semaphore(max_concurrent_requests)
    
    # Flag to signal early termination
    stop_processing = threading.Event()
    
    # Progress bar
    pbar = tqdm(total=len(data_to_process), desc=f"Inference for {model_name_or_path}")
    
    def process_instance(args):
        """Worker function to process a single instance with retry logic"""
        nonlocal total_cost, processed_count
        
        instance_id, output_dict, instance_args = args
        output_dir = os.path.dirname(output_file)
        
        # Skip if we've reached max cost
        if stop_processing.is_set():
            return None
        
        # Limit concurrent API requests
        with api_semaphore:
            retry_attempts = 0
            max_retries = 5
            
            while retry_attempts < max_retries and not stop_processing.is_set():
                try:
                    response, cost, patch_text = call_grok_with_validation(
                        model_name_or_path,
                        output_dict["text"],
                        temperature,
                        top_p,
                        output_dir=output_dir,
                        instance_id=instance_id,
                        **instance_args
                    )
                    
                    # Skip if no valid response
                    if response is None:
                        logger.warning(f"[{instance_id}] Generated invalid Grok response")
                        break
                    
                    # Update the output dictionary with results
                    output_dict["full_output"] = response.choices[0].message.content
                    output_dict["model_patch"] = patch_text
                    
                    # Update costs and write output in a thread-safe way
                    with cost_lock:
                        total_cost += cost
                        current_cost = total_cost
                        
                        # Check if we've hit max cost
                        if max_cost is not None and current_cost >= max_cost:
                            stop_processing.set()
                    
                    # Write to output file
                    with output_lock:
                        with open(output_file, "a+") as f:
                            print(json.dumps(output_dict), file=f, flush=True)
                        
                        # Log cost occasionally
                        with cost_lock:
                            processed_count += 1
                            if processed_count % 5 == 0:  # Log every 5 completed instances
                                print(f"Processed {processed_count}/{len(data_to_process)}, Total Cost: ${current_cost:.4f}")
                    
                    return True
                    
                except Exception as e:
                    # Check if it's a rate limit error
                    if hasattr(e, 'is_rate_limit') and e.is_rate_limit:
                        retry_attempts += 1
                        wait_time = min(2 ** retry_attempts, 60)  # Exponential backoff capped at 60 seconds
                        logger.warning(f"[{instance_id}] Grok rate limit hit, retrying in {wait_time}s (attempt {retry_attempts}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        # For other errors, log and break
                        logger.error(f"[{instance_id}] Grok error: {e}")
                        traceback.print_exc()
                        break
            
            return False
    
    try:
        print(f"Processing {len(data_to_process)} instances with {max_workers} workers")
        
        # Process instances in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks to the executor
            future_to_instance = {
                executor.submit(process_instance, args): args[0]  # Map future to instance_id
                for args in data_to_process
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_instance):
                instance_id = future_to_instance[future]
                try:
                    result = future.result()
                    if stop_processing.is_set():
                        logger.info(f"Skipping remaining instances due to max cost or interrupt")
                        # Cancel any pending futures
                        for pending_future in future_to_instance:
                            if not pending_future.done():
                                pending_future.cancel()
                except Exception as e:
                    logger.error(f"[{instance_id}] Grok worker thread error: {e}")
                    traceback.print_exc()
                
                # Update progress bar
                pbar.update(1)
                
                # Check for early termination
                if stop_processing.is_set():
                    break
    
    finally:
        pbar.close()
    
    print(f"Completed Grok inference for {model_name_or_path}")
    print(f"Processed {processed_count}/{len(data_to_process)} instances")
    print(f"Total Cost: ${total_cost:.4f}")
    
    return total_cost


#####################################
#          Main Inference Loop       #
#####################################

def run_inference_for_model(
    dataset,
    model_name_or_path,
    output_file,
    model_args,
    existing_ids,
    max_cost,
):
    """Runs inference for a single model."""
    inference_args = {
        "test_dataset": dataset,
        "model_name_or_path": model_name_or_path,
        "output_file": output_file,
        "model_args": model_args,
        "existing_ids": existing_ids,
        "max_cost": max_cost,
    }
    if model_name_or_path.startswith("claude"):
        anthropic_inference(**inference_args)
    elif model_name_or_path.startswith("gpt") or model_name_or_path.startswith("o1") or model_name_or_path.startswith("o3") or model_name_or_path.startswith("o4"):
        openai_inference(**inference_args)
    elif model_name_or_path in FIREWORKS_MODEL_PATHS:
        fireworks_inference(**inference_args)
    elif model_name_or_path in TOGETHER_MODEL_PATHS or model_name_or_path.startswith("meta-llama/Llama-4"):
        together_inference(**inference_args)
    elif model_name_or_path.startswith("gemini"):
        gemini_inference(**inference_args)
    elif model_name_or_path.startswith("grok"):
        grok_inference(**inference_args)
    else:
        raise ValueError(f"Invalid model name or path {model_name_or_path}")
    logger.info(f"Done with model {model_name_or_path}!")

def parse_model_args(model_args):
    """
    Parses a string of model arguments and returns a dictionary of keyword arguments.

    Args:
        model_args (str): A string of comma-separated key-value pairs representing model arguments.

    Returns:
        dict: A dictionary of keyword arguments parsed from the input string.
    """
    kwargs = dict()
    if model_args is not None:
        for arg in model_args.split(","):
            key, value = arg.split("=")
            # infer value type
            if value in {"True", "False"}:
                kwargs[key] = value == "True"
            elif value.isnumeric():
                kwargs[key] = int(value)
            elif value.replace(".", "", 1).isnumeric():
                kwargs[key] = float(value)
            elif value in {"None"}:
                kwargs[key] = None
            elif value in {"[]"}:
                kwargs[key] = []
            elif value in {"{}"}:
                kwargs[key] = {}
            elif value.startswith("'") and value.endswith("'"):
                kwargs[key] = value[1:-1]
            elif value.startswith('"') and value.endswith('"'):
                kwargs[key] = value[1:-1]
            else:
                kwargs[key] = value
    return kwargs


def main(
    dataset_name_or_path,
    split,
    models,
    shard_id,
    num_shards,
    output_dir,
    model_args,
    max_cost,
):
    if shard_id is None and num_shards is not None:
        logger.warning(
            f"Received num_shards={num_shards} but shard_id is None, ignoring"
        )
    if shard_id is not None and num_shards is None:
        logger.warning(f"Received shard_id={shard_id} but num_shards is None, ignoring")
    
    parsed_model_args = parse_model_args(model_args)
    
    # Load and prepare dataset once for all models
    if Path(dataset_name_or_path).exists():
        dataset = load_from_disk(dataset_name_or_path)
    else:
        dataset = load_dataset(dataset_name_or_path)
    
    if not split in dataset:
        raise ValueError(f"Invalid split {split} for dataset {dataset_name_or_path}")
    
    dataset = dataset[split]
    lens = np.array(list(map(len, dataset["text"])))
    dataset = dataset.select(np.argsort(lens))
    
    if shard_id is not None and num_shards is not None:
        dataset = dataset.shard(num_shards, shard_id, contiguous=True)
    print(f"Dataset: {len(dataset)}")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Run inference on models sequentially
    for model_name_or_path in models:
        model_nickname = model_name_or_path
        if "checkpoint" in Path(model_name_or_path).name:
            model_nickname = Path(model_name_or_path).parent.name
        else:
            model_nickname = Path(model_name_or_path).name
        
        output_file = f"{model_nickname}__{dataset_name_or_path.split('/')[-1]}__{split}"
        if shard_id is not None and num_shards is not None:
            output_file += f"__shard-{shard_id}__num_shards-{num_shards}"
        output_file = Path(output_dir, output_file + ".jsonl")
        logger.info(f"Will write to {output_file}")
        
        existing_ids = set()
        if os.path.exists(output_file):
            with open(output_file) as f:
                for line in f:
                    data = json.loads(line)
                    instance_id = data["instance_id"]
                    existing_ids.add(instance_id)
        logger.info(f"Read {len(existing_ids)} already completed ids from {output_file}")
        
        model_dataset = dataset
        if len(existing_ids) > 0:
            model_dataset = dataset.filter(
                lambda x: x["instance_id"] not in existing_ids,
                desc=f"Filtering out existing ids for {model_name_or_path}",
                load_from_cache_file=False,
            )
        
        try:
            run_inference_for_model(
                model_dataset,
                model_name_or_path,
                output_file,
                parsed_model_args.copy(),
                existing_ids,
                max_cost,
            )
        except Exception as e:
            logger.error(f"Error running inference for model {model_name_or_path}: {e}")
            traceback.print_exc()
    
    logger.info(f"Finished inference for all models!")

def update_full_file_patches():
    """
    Updates the model_patch field in prediction files using extract_full_file_patch on full_output.
    
    Args:
        path (str): Path to a prediction file (.jsonl) or directory of prediction files
    """
    prediction_path = "./predictions/o3/o3__Kotlin-bench__full_file_gen__fs-oracle__test.jsonl"
    if not prediction_path:
        raise ValueError("prediction_path must be specified")
        
    prediction_path = Path(prediction_path)
    if not prediction_path.exists():
        raise ValueError(f"Prediction path {prediction_path} does not exist")
        
    # Create temporary file for writing updates
    temp_file = prediction_path.with_suffix('.jsonl.tmp')
    updated_count = 0
    
    try:
        with open(prediction_path, 'r') as f_in, open(temp_file, 'w') as f_out:
            for line in f_in:
                entry = json.loads(line)
                if 'full_output' in entry:
                    # Extract and update the model_patch field
                    new_patch = extract_full_file_patch(entry['full_output'])
                    if new_patch is not None:
                        entry['model_patch'] = new_patch
                        updated_count += 1
                
                # Write the entry back (updated or not)
                print(json.dumps(entry), file=f_out)
        
        # Replace original file with updated version
        temp_file.replace(prediction_path)
        logger.info(f"Updated {updated_count} entries in {prediction_path}")
        
    except Exception as e:
        logger.error(f"Error processing {prediction_path}: {str(e)}")
        if temp_file.exists():
            temp_file.unlink()  # Delete temp file if it exists
        raise e


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset_name_or_path",
        type=str,
        required=True,
        help="HuggingFace dataset name or local path",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        help="Dataset split to use",
    )
    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        required=True,
        help="Names of API models to use. Can specify multiple models separated by spaces.",
        choices=sorted(list(MODEL_LIMITS.keys())),
    )
    parser.add_argument(
        "--shard_id",
        type=int,
        default=None,
        help="Shard id to process. If None, process all shards.",
    )
    parser.add_argument(
        "--num_shards",
        type=int,
        default=None,
        help="Number of shards. If None, process all shards.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        required=True,
        help="Path to the output directory where all model outputs will be saved.",
    )
    parser.add_argument(
        "--model_args",
        type=str,
        default=None,
        help="List of model arguments separated by commas. (e.g. 'top_p=0.95,temperature=0.70')",
    )
    parser.add_argument(
        "--max_cost",
        type=float,
        default=None,
        help="Maximum cost to spend on inference per model.",
    )
    args = parser.parse_args()
    main(**vars(args))
