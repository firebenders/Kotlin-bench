#!/usr/bin/env python3
"""
Script to upload datasets to Hugging Face.
Usage:
    python hf_upload.py path/to/dataset [path/to/another/dataset ...] --repo-id your-username/dataset-name
"""

import argparse
import os
from pathlib import Path
from datasets import load_from_disk, DatasetDict
from huggingface_hub import HfApi, login
import logging
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Upload datasets to Hugging Face")
    parser.add_argument(
        "dataset_paths",
        nargs="+",
        type=str,
        help="Path(s) to the dataset(s) to upload. Can be file paths or directories.",
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        required=True,
        help="The Hugging Face repository ID to upload to (e.g., 'username/dataset-name').",
    )
    parser.add_argument(
        "--token",
        type=str,
        help="Hugging Face API token. If not provided, will look for HF_TOKEN environment variable.",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Whether to make the repository private.",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="train",
        help="The dataset split to upload to (default: 'train').",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["csv", "json", "jsonl", "parquet", "auto"],
        default="auto",
        help="Dataset format. If 'auto', try to infer from file extension.",
    )
    return parser.parse_args()

def load_and_upload_dataset(dataset_paths, repo_id, private=False, split="train", format="auto", token=None):
    """Load and upload datasets to Hugging Face."""
    # Login to Hugging Face
    if token:
        login(token=token)
    
    # Create dataset dictionary
    dataset_dict = DatasetDict()
    
    # Process each dataset path
    for path in tqdm(dataset_paths, desc="Processing datasets"):
        path_obj = Path(path)
        
        if not path_obj.exists():
            logger.warning(f"Path does not exist: {path}")
            continue
        
        logger.info(f"Loading dataset from {path}")
        try:
            # If it's a directory, load all files with matching extension
            ds = load_from_disk(path)
            
            # Add to our dataset dictionary
            if split not in dataset_dict:
                dataset_dict[split] = ds["train"] if "train" in ds else next(iter(ds.values()))
            else:
                # Combine with existing split
                dataset_dict[split] = dataset_dict[split].concatenate(ds["train"] if "train" in ds else next(iter(ds.values())))
            
            logger.info(f"Successfully loaded dataset from {path}")
        except Exception as e:
            logger.error(f"Error loading dataset from {path}: {e}")
    
    if not dataset_dict:
        logger.error("No datasets were successfully loaded.")
        return
    
    # Print total number of entries in the dataset
    total_entries = sum(len(split) for split in dataset_dict.values())
    logger.info(f"Total number of entries in dataset: {total_entries}")
    
    # Print entries per split
    for split_name, split_data in dataset_dict.items():
        logger.info(f"Split '{split_name}': {len(split_data)} entries")
    
    # Push to the hub
    logger.info(f"Uploading dataset to {repo_id}")
    try:
        dataset_dict.push_to_hub(
            repo_id,
            private=private,
        )
        logger.info(f"Successfully uploaded dataset to {repo_id}")
    except Exception as e:
        logger.error(f"Error uploading dataset to {repo_id}: {e}")

def main():
    args = parse_args()
    
    # Get token from args or environment
    token = args.token or os.environ.get("HF_TOKEN")
    if not token:
        logger.warning("No Hugging Face token provided. You may need to log in with `huggingface-cli login`.")
    
    load_and_upload_dataset(
        dataset_paths=args.dataset_paths,
        repo_id=args.repo_id,
        private=args.private,
        split=args.split,
        format=args.format,
        token=token,
    )

if __name__ == "__main__":
    main()
