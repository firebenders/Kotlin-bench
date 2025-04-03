#!/usr/bin/env python3

"""
Wrapper script to run create_text_dataset.py with the correct import paths.
This solves the relative import issue.
"""

import os
import sys

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath('.'))

# Import the necessary modules directly with absolute imports
from inference.make_datasets.create_instance import PROMPT_FUNCTIONS, add_text_inputs
from inference.make_datasets.tokenize_dataset import TOKENIZER_FUNCS
from inference.make_datasets.utils import string_to_bool

# Now import and run the main function from create_text_dataset
from inference.make_datasets.create_text_dataset import main

if __name__ == "__main__":
    # Remove the script name from sys.argv
    args = sys.argv[1:]
    
    # Import argparse to parse arguments
    import argparse
    
    # Create the argument parser 
    parser = argparse.ArgumentParser(description="Create a dataset for text-to-text training from raw task instances")
    parser.add_argument(
        "--dataset_name_or_path",
        type=str,
        required=True,
        help="Dataset to use from HuggingFace Datasets or path to a JSON file."
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["train", "test"],
        help="Splits to use from the dataset."
    )
    parser.add_argument(
        "--validation_ratio",
        type=float,
        default=0.01,
        help="Ratio of the training set to use for validation."
    )
    parser.add_argument(
        "--output_dir", 
        type=str, 
        required=True,
        help="Path to the output directory."
    )
    parser.add_argument(
        "--retrieval_file",
        type=str,
        required=True,
        help="Path to the file where the retrieval results are stored."
    )
    parser.add_argument(
        "--prompt_style",
        type=str,
        default="style-3",
        choices=PROMPT_FUNCTIONS.keys(),
        help="Prompt style to use. See create_instance.PROMPT_FUNCTIONS for details."
    )
    parser.add_argument(
        "--file_source",
        type=str,
        default="oracle",
        choices=["oracle", "bm25", "all"],
        help="How to select the files to use in context."
    )
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help="Maximum number of files to use for retrieval."
    )
    parser.add_argument(
        "--max_context_len",
        type=int,
        default=None,
        help="Maximum number of tokens to use for context."
    )
    parser.add_argument(
        "--tokenizer_name",
        type=str,
        default=None,
        choices=TOKENIZER_FUNCS.keys(),
        help="Tokenizer to use for max_context_len. Only needed if max_context_len is specified."
    )
    parser.add_argument(
        "--push_to_hub_user",
        type=str,
        default=None,
        help="Username to use for pushing to the Hub. If not provided, will save to disk."
    )
    parser.add_argument(
        "--include_test_files",
        action="store_true",
        help="Include test files in oracle mode context"
    )
    
    # Parse the arguments and run the main function
    parsed_args = parser.parse_args(args)
    main(**vars(parsed_args)) 
