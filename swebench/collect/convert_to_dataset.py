import json
from datasets import Dataset, DatasetDict, load_from_disk
import os
import argparse

def convert_to_hf_dataset(task_instances, output_dir):
    """
    Convert task instances JSON to a Huggingface dataset and save it to the specified directory.
    
    Args:
        task_instances: List of task instance dictionaries
        output_dir: Directory where the Huggingface dataset will be saved
    
    Returns:
        The created dataset
    """
    # Create Dataset from the list of dictionaries
    dataset = Dataset.from_list(task_instances)
    
    # Organize into DatasetDict with a single split (you can add train/test splits if needed)
    dataset_dict = DatasetDict({"test": dataset})
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the dataset to the specified directory
    dataset_dict.save_to_disk(output_dir)
    
    print(f"Dataset saved to {output_dir}")
    return dataset_dict

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert task instances to Huggingface dataset')
    parser.add_argument('--input_file', type=str, help='Path to the JSON file containing task instances')
    parser.add_argument('--output_dir', type=str, help='Directory where the Huggingface dataset will be saved')
    
    args = parser.parse_args()
    
    # Read the JSON file
    with open(args.input_file, 'r') as f:
        task_instances = json.load(f)
    
    # Convert and save the dataset
    dataset = convert_to_hf_dataset(task_instances, args.output_dir)
