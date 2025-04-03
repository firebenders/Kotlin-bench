import json
import re
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Regex to find file blocks with their markers
FILE_BLOCK_REGEX = re.compile(
    r'(\[start of .*?]'  # Match and capture the "[start of path]" marker
    r'.*?'               # Capture everything between markers (non-greedy)
    r'\[end of .*?])',    # Match and capture the "[end of path]" marker
    re.DOTALL
)

def update_model_patch(input_path, output_path, dry_run=False):
    """
    Reads a JSONL file, extracts all file blocks with markers from each entry's 'full_output',
    concatenates them, and updates the 'model_patch' key.
    
    Args:
        input_path (Path): Path to the input JSONL file.
        output_path (Path): Path to save the updated JSONL file.
        dry_run (bool): If True, prints changes but doesn't save the file.
    """
    updated_lines = []
    line_count = 0
    modified_count = 0
    
    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            line_count += 1
            try:
                entry = json.loads(line)
                full_output = entry.get('full_output', '')
                
                # Extract all file blocks with their markers
                matches = FILE_BLOCK_REGEX.findall(full_output)
                
                if matches:
                    # Concatenate all file blocks with their markers
                    model_patch = '\n\n'.join(matches)
                    
                    # Update the model_patch field
                    old_patch = entry.get('model_patch', '')
                    entry['model_patch'] = model_patch
                    
                    if old_patch != model_patch:
                        modified_count += 1
                        logging.debug(f"Updated model_patch for entry {line_num}")
                
                updated_lines.append(json.dumps(entry))
                
            except json.JSONDecodeError:
                logging.error(f"Error parsing JSON at line {line_num}")
                updated_lines.append(line)  # Keep original line
            except Exception as e:
                logging.error(f"Error processing line {line_num}: {e}")
                updated_lines.append(line)  # Keep original line
    
    logging.info(f"Processed {line_count} entries. Modified {modified_count} model_patch fields.")
    
    if not dry_run:
        with open(output_path, 'w', encoding='utf-8') as f:
            for line in updated_lines:
                f.write(f"{line}\n")
        logging.info(f"Updated JSONL saved to: {output_path}")
    else:
        logging.info("Dry run completed. No file was written.")

def main():
    parser = argparse.ArgumentParser(
        description="Extract file blocks from 'full_output' and update 'model_patch' in JSONL prediction files."
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to the input JSONL prediction file."
    )
    parser.add_argument(
        "--output",
        type=str,
        required=False,
        help="Path to save the updated JSONL file. If not provided, will use input file with '.updated' suffix."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print changes without modifying any files."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging for more detailed output."
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    input_path = Path(args.input)
    
    if not input_path.exists():
        logging.error(f"Input file not found: {input_path}")
        return

    if args.output:
        output_path = Path(args.output)
    else:
        # Create a default output path with '.updated' suffix
        output_path = input_path.with_suffix(f"{input_path.suffix}.updated")

    update_model_patch(input_path, output_path, args.dry_run)

if __name__ == "__main__":
    main()