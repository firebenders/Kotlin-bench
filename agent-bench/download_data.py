#!/usr/bin/env python3
"""
Simple script to download Kotlin-Bench dataset from HuggingFace.
"""

import json
import os
import requests
from pathlib import Path


DATA_URL = "https://datasets-server.huggingface.co/rows?dataset=firebenders%2FKotlin-Bench&config=default&split=train&offset=0&length=100"
DATA_DIR = Path(__file__).parent / "data"


def download_dataset():
    """Download the Kotlin-Bench dataset from HuggingFace."""
    print(f"Downloading dataset from HuggingFace...")
    
    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download the data
    response = requests.get(DATA_URL)
    response.raise_for_status()
    
    data = response.json()
    
    # Save the raw response
    output_path = DATA_DIR / "kotlin_bench_raw.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved raw data to {output_path}")
    
    # Extract and save just the rows
    if "rows" in data:
        rows = [row["row"] for row in data["rows"]]
        rows_path = DATA_DIR / "kotlin_bench.json"
        with open(rows_path, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"Saved {len(rows)} tasks to {rows_path}")
    
    print("Done!")
    return data


if __name__ == "__main__":
    download_dataset()
