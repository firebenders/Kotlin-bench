#!/usr/bin/env python3
import json
import sys
from typing import Dict, Any

from swebench.harness.utils import get_test_directives, get_android_test_cmd

def process_instances(jsonl_file: str) -> None:
    """
    Process a JSON file containing a list of task instances and print out 
    the mapping between instances and their corresponding Android test commands.
    
    Args:
        jsonl_file (str): Path to the JSON file containing task instances
    """
    try:
        with open(jsonl_file, 'r') as f:
            # Parse the entire file as a JSON array
            instances = json.load(f)
            
            total = 0
            aggregate_counts = {}

            # Process each instance in the array
            version_set = set()
            for instance in instances:
                if (instance.get("version", "unknown") == "unknown"):
                    continue
                version_set.add(instance.get("version", "unknown"))
                # Get instance identifier
                instance_id = instance.get("instance_id", "unknown")

                # Get test directives and command
                test_directives = get_test_directives(instance)
                total += len(test_directives)
                instance["test_directives"] = test_directives  # Store as list
                test_cmd = get_android_test_cmd(instance)
                
                # Print mapping
                if (len(test_directives) > 0):
                    print(f"Instance {instance_id}:")
                    print(f"  Repo: {instance.get('repo', 'unknown')}")
                    print(f"  Commit: {instance.get('base_commit', 'unknown')}")
                    print(f"  Test directives: {test_directives}")
                    print(f"  Test command: {test_cmd}")
                    print()

                # for directive in instance.get("test_directives", []):
                #     added = False
                #     for prefix in prefix_set:
                #         if directive.startswith(prefix):
                #             aggregate_counts[prefix] = aggregate_counts.get(prefix, 0) + 1
                #             added = True
                #             break
                #     else:
                #         if not added:
                #             print(directive)
                #             aggregate_counts["other"] = aggregate_counts.get("other", 0) + 1

            # print(aggregate_counts)

            print("\nVersions found:")
            for version in sorted(version_set):
                print(f"  {version}")
    except FileNotFoundError:
        print(f"Error: File {jsonl_file} not found", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file {jsonl_file}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Error processing instances: {e}", file=sys.stderr)
        raise  # Add this to see the full traceback for debugging

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_test_commands.py <json_file>", file=sys.stderr)
        sys.exit(1)
        
    process_instances(sys.argv[1]) 
