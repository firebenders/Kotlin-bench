import os
import json
import re
import argparse
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Regex to find file blocks
# It captures the file path (group 1) and the code content (group 2)
# It handles optional language identifiers after the first ```
# re.DOTALL allows '.' to match newlines within the code block
FILE_BLOCK_REGEX = re.compile(
    r'\[start of (.*?)]'  # Match "[start of " and capture the path (non-greedy)
    r'\n?'               # Optionally match a newline after the start marker
    r'(.*?)'             # Capture the content between markers (non-greedy)
    r'\n?'               # Optionally match a newline before the end marker
    r'\[end of \1]',      # Match "[end of " and the same path captured earlier (\1)
    re.DOTALL
)

def extract_files_from_entry(json_entry, jsonl_filename, output_base_dir):
    """
    Parses a single JSON entry, extracts file blocks from 'full_output',
    and saves them to the output directory, organized by instance ID.

    Args:
        json_entry (dict): The parsed JSON object from a line.
        jsonl_filename (Path): The Path object of the source JSONL file.
        output_base_dir (Path): The base directory for all extracted output.

    Returns:
        int: The number of file blocks successfully extracted from this entry.
    """
    instance_id = json_entry.get("instance_id", None)
    full_output = json_entry.get("full_output", "")

    if not instance_id:
        # Use a unique identifier if instance_id is missing, e.g., based on line number (though less ideal)
        # For simplicity here, we'll just log and skip. You might adapt this.
        logging.warning(f"Entry in {jsonl_filename.name} missing 'instance_id'. Skipping.")
        return 0 # Indicate 0 files extracted

    if not full_output:
        logging.debug(f"Entry {instance_id} in {jsonl_filename.name} has empty 'full_output'. Skipping.")
        return 0 # Indicate 0 files extracted

    matches = FILE_BLOCK_REGEX.finditer(full_output)
    extracted_count = 0

    # Base directory for this specific instance's extracted files
    # Structure: output_base_dir / jsonl_file_name_without_extension / instance_id / extracted_file_path
    instance_output_dir = output_base_dir / jsonl_filename.stem / str(instance_id)

    found_match = False
    for match in matches:
        found_match = True
        extracted_count += 1
        try:
            # Extract file path and code content from the regex match groups
            file_path_str = match.group(1).strip()
            code_content = match.group(2).strip()

            # Basic security check: Prevent writing outside the intended output directory
            if os.path.isabs(file_path_str) or ".." in file_path_str.split(os.sep):
                logging.warning(f"Skipping potentially unsafe path '{file_path_str}' in {instance_id} from {jsonl_filename.name}")
                continue

            # Construct the full path for the output file
            output_file_path = instance_output_dir / file_path_str

            # Ensure the parent directory exists
            output_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the extracted code content to the new file
            with open(output_file_path, "w", encoding="utf-8") as f_out:
                f_out.write(code_content)
            logging.debug(f"Saved extracted file to: {output_file_path}")

        except Exception as e:
            logging.error(f"Error processing match for {instance_id} in {jsonl_filename.name}: {e}")
            # Continue to the next match within the same entry if possible

    if not found_match and full_output:
        logging.info(f"No file blocks found matching pattern in 'full_output' for {instance_id} from {jsonl_filename.name}")
        # Create the "errored" directory within the instance directory
        errored_dir = instance_output_dir / "errored"
        errored_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a numbered file for this error case
        error_count = len(list(errored_dir.glob("error_*.txt")))
        error_file_path = errored_dir / f"error_{error_count + 1}.txt"
        
        # Write the full_output content to the error file
        with open(error_file_path, "w", encoding="utf-8") as f_out:
            f_out.write(full_output)
        logging.info(f"Saved full_output to error file: {error_file_path}")

    return extracted_count


def process_jsonl_file(jsonl_path, output_base_dir):
    """Reads a single JSONL file and processes each line/entry."""
    logging.info(f"Processing file: {jsonl_path.name}")
    total_extracted_for_file = 0
    line_num = 0
    with open(jsonl_path, "r", encoding="utf-8") as f_in:
        for line in f_in:
            line_num += 1
            # Skip empty lines
            if not line.strip():
                continue
            try:
                # Parse the JSON string from the current line
                json_entry = json.loads(line)
                # Extract files from this specific entry
                total_extracted_for_file += extract_files_from_entry(json_entry, jsonl_path, output_base_dir)
            except json.JSONDecodeError:
                logging.error(f"Error decoding JSON on line {line_num} in {jsonl_path.name}")
            except Exception as e:
                # Catch any other unexpected errors during processing of a line
                logging.error(f"Unexpected error processing line {line_num} in {jsonl_path.name}: {e}")
    logging.info(f"Finished processing {jsonl_path.name}. Extracted {total_extracted_for_file} file blocks in total.")


def main():
    parser = argparse.ArgumentParser(
        description="Extract code files embedded within [start/end] blocks in JSONL prediction files for manual review."
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing the .jsonl prediction files."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory where extracted files will be saved, organized by prediction file and instance ID."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging for more detailed output."
    )

    args = parser.parse_args()

    # Set logging level based on debug flag
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    # Validate input directory existence
    if not input_dir.is_dir():
        logging.error(f"Input directory not found: {input_dir}")
        return

    # Create the base output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    logging.info(f"Output will be saved in: {output_dir}")

    # Find all .jsonl files in the input directory
    jsonl_files = list(input_dir.glob("*.jsonl"))

    if not jsonl_files:
        logging.warning(f"No .jsonl files found in {input_dir}")
        return

    # Process each found JSONL file
    for jsonl_file_path in jsonl_files:
        process_jsonl_file(jsonl_file_path, output_dir)

    logging.info("Extraction process completed.")

if __name__ == "__main__":
    main()