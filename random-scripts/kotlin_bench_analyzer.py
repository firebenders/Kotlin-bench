import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import glob
import difflib
from pathlib import Path
from datasets import load_from_disk
import openai
import time

# Path to the dataset and reports directory
dataset_path = "./datasets/Kotlin-bench"
reports_dir = './evaluation_logs/reports'
logs_dir = './evaluation_logs'

# Configure OpenAI API (add your API key here or set as environment variable)
# openai.api_key = "your-api-key"  # Or use: os.environ.get("OPENAI_API_KEY")

# Load the Kotlin-bench dataset
def load_dataset():
    print(f"Loading dataset from {dataset_path}")
    dataset = load_from_disk(dataset_path)
    print(f"Dataset loaded with splits: {list(dataset.keys())}")
    return dataset["test"]

# Extract repo, issue, and PR information from task instances
def extract_task_info(dataset):
    print(f"Extracting information from {len(dataset)} tasks...")
    
    task_info = []
    for task in dataset:
        instance_id = task["instance_id"]
        repo = task["repo"]
        
        # Format GitHub issues/PRs URLs
        issues_urls = [f"https://github.com/{repo}/issues/{issue}" for issue in task.get("issue_numbers", [])]
        pr_url = f"https://github.com/{repo}/pull/{task['pull_number']}" if "pull_number" in task else None
        
        task_info.append({
            "instance_id": instance_id,
            "repo": repo,
            "issue_urls": issues_urls,
            "pr_url": pr_url
        })
    
    return pd.DataFrame(task_info)

# Load all model reports and create a mapping of model_name to results
def load_model_reports():
    print(f"Loading model reports from {reports_dir}")
    
    reports = {}
    report_files = glob.glob(os.path.join(reports_dir, "*.json"))
    
    for report_file in report_files:
        with open(report_file, 'r') as f:
            report_data = json.load(f)
            model_name = report_data.get("model", Path(report_file).stem.replace("model_report_", ""))
            
            # Extract results for each task
            reports[model_name] = {
                "generated": set(report_data.get("generated", [])),
                "applied": set(report_data.get("applied", [])),
                "resolved": set(report_data.get("resolved", []))
            }
    
    print(f"Loaded {len(reports)} model reports")
    return reports

# Create model_name to result mapping for each task with simplified labels
def create_model_result_mapping(task_info_df, model_reports):
    print("Creating model result mappings with simplified labels (no_generation, failed, resolved)...")
    
    for model_name, results in model_reports.items():
        # Create a result column for each model with simplified labels
        task_info_df[f"result_{model_name}"] = task_info_df["instance_id"].apply(
            lambda instance_id: "resolved" if instance_id in results["resolved"] else
                              "failed" if instance_id in results["generated"] else
                              "no_generation"
        )
    
    return task_info_df

# Analyze model performance
def analyze_model_performance(task_df):
    # Count results by model
    model_columns = [col for col in task_df.columns if col.startswith('result_')]
    
    results = {}
    for col in model_columns:
        model = col.replace('result_', '')
        result_counts = task_df[col].value_counts()
        results[model] = {
            'resolved': result_counts.get('resolved', 0),
            'failed': result_counts.get('failed', 0),
            'no_generation': result_counts.get('no_generation', 0)
        }
    
    return pd.DataFrame(results).T

# Save results to JSON
def save_to_json(task_df, performance_df):
    # Convert the dataframe to a list of dictionaries for JSON serialization
    new_task_results = task_df.to_dict(orient='records')
    
    # Prepare the model performance summary
    new_performance_dict = performance_df.to_dict(orient='index')
    
    # Create the final JSON structure
    results_json = {
        "task_results": new_task_results,
        "model_performance": new_performance_dict
    }
    
    # Check if the file already exists
    if os.path.exists('kotlin_bench_results.json'):
        print("Existing results file found. Merging new results...")
        try:
            with open('kotlin_bench_results.json', 'r') as f:
                existing_json = json.load(f)
                
                # Create a lookup by instance_id for faster merging
                existing_task_lookup = {task["instance_id"]: task for task in existing_json["task_results"]}
                
                # Merge task results
                merged_task_results = []
                for new_task in new_task_results:
                    instance_id = new_task["instance_id"]
                    if instance_id in existing_task_lookup:
                        # Update existing task with new model results
                        merged_task = existing_task_lookup[instance_id].copy()
                        
                        # Only add the new model results (fields starting with 'result_')
                        for key, value in new_task.items():
                            if key.startswith('result_'):
                                merged_task[key] = value
                                
                        merged_task_results.append(merged_task)
                    else:
                        # This is a new task not in the existing file
                        merged_task_results.append(new_task)
                
                # Add any tasks from existing file that aren't in the new results
                new_instance_ids = {task["instance_id"] for task in new_task_results}
                for instance_id, task in existing_task_lookup.items():
                    if instance_id not in new_instance_ids:
                        merged_task_results.append(task)
                
                # Merge performance dictionaries
                merged_performance = existing_json["model_performance"].copy()
                for model, perf in new_performance_dict.items():
                    merged_performance[model] = perf
                
                # Update the results JSON with merged data
                results_json = {
                    "task_results": merged_task_results,
                    "model_performance": merged_performance
                }
                
                print(f"Successfully merged results. Total tasks: {len(merged_task_results)}")
        except Exception as e:
            print(f"Error merging with existing file: {e}")
            print("Creating new file instead.")
    
    # Save to JSON file
    with open('kotlin_bench_results.json', 'w') as f:
        json.dump(results_json, f, indent=2)
    
    print("Results saved to kotlin_bench_results.json")
    return results_json

def get_all_failed_tasks(results_json):
    """
    Returns a list of task instance IDs where all models failed.
    
    Args:
        results_json (dict): The JSON results containing task results and model performance
        
    Returns:
        list: List of task instance IDs where all models failed
    """
    all_failed_tasks = []
    
    # Iterate through each task result
    for task in results_json["task_results"]:
        # Get all result fields that start with 'result_'
        result_fields = [k for k in task.keys() if k.startswith('result_')]
        
        # Check if all results are 'failed'
        if all(task[field] == 'failed' for field in result_fields):
            all_failed_tasks.append(task["instance_id"])
    
    return all_failed_tasks

def get_patch_from_dataset(dataset, instance_id):
    """
    Get the original patch from the dataset for a specific task instance.
    
    Args:
        dataset: The Kotlin-bench dataset
        instance_id (str): The task instance ID
    
    Returns:
        str: The original patch from the PR
    """
    for task in dataset:
        if task["instance_id"] == instance_id:
            return task.get("patch", "")
    return ""

def get_problem_statement(dataset, instance_id):
    """
    Get the problem statement for a specific task instance.
    
    Args:
        dataset: The Kotlin-bench dataset
        instance_id (str): The task instance ID
    
    Returns:
        str: The problem statement
    """
    for task in dataset:
        if task["instance_id"] == instance_id:
            return task.get("problem_statement", "")
    return ""

def get_model_generated_patches(instance_id, model_names):
    """
    Get the AI-generated patches for a specific task instance from each model.
    
    Args:
        instance_id (str): The task instance ID
        model_names (list): List of model names
    
    Returns:
        dict: Mapping of model name to its generated patch
    """
    model_patches = {}
    
    for model_name in model_names:
        patch_path = os.path.join(logs_dir, instance_id, model_name, "unknown", "patch.diff")
        
        if os.path.exists(patch_path):
            try:
                with open(patch_path, 'r') as f:
                    model_patches[model_name] = f.read()
            except Exception as e:
                print(f"Error reading {patch_path}: {e}")
        
    return model_patches

def compare_patches_with_openai(original_patch, model_patch, problem_statement=None):
    """
    Use OpenAI to compare the original PR patch with a model-generated patch and provide 
    a concise description of the differences.
    
    Args:
        original_patch (str): The original patch from the PR
        model_patch (str): The model-generated patch
        problem_statement (str, optional): The problem statement to provide context
        
    Returns:
        str: A concise description of the differences
    """
    if not original_patch or not model_patch:
        return "Could not compare patches - one or both patches are empty"
    
    # Prepare the prompt
    prompt = "Compare these two code patches and describe the differences concisely, focusing on where the AI-generated patch falls short or makes mistakes compared to the actual PR patch:\n\n"
    
    if problem_statement:
        prompt += f"Problem Description: {problem_statement}\n\n"
    
    prompt += "ACTUAL PR PATCH:\n```\n" + original_patch + "\n```\n\n"
    prompt += "AI-GENERATED PATCH:\n```\n" + model_patch + "\n```\n\n"
    prompt += "Provide a concise analysis of the most important differences, focusing on logical errors, missing changes, or misunderstandings in the AI solution compared to the actual PR. Be specific but brief (max 4-5 sentences)."
    
    try:
        # Create an OpenAI client
        client = openai.Client()
        
        # Make the API call to OpenAI using the new interface
        response = client.chat.completions.create(
            model="gpt-4o-2024-11-20",  # Or use a different model
            messages=[
                {"role": "system", "content": "You are an expert code reviewer focusing on differences between patches."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=350,
            temperature=0.0
        )
        
        # Extract and return the model's response
        analysis = response.choices[0].message.content.strip()
        
        # Add a small delay to avoid rate limiting
        time.sleep(0.5)
        
        return analysis
    
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        # Fallback to a simple diff if API call fails
        return f"OpenAI API error: {str(e)}\nFallback to basic comparison: Patches differ in content/structure"

def analyze_failed_tasks(dataset, results_json):
    """
    Analyze tasks where all models failed by comparing original patches with model-generated patches.
    
    Args:
        dataset: The Kotlin-bench dataset
        results_json (dict): The JSON results containing task results and model performance
    
    Returns:
        dict: Analysis of failed tasks with differences between original and model patches
    """
    # Get tasks where all models failed
    failed_tasks = get_all_failed_tasks(results_json)
    print(f"Found {len(failed_tasks)} tasks where all models failed")
    
    # Get model names from the results
    model_names = [k.replace('result_', '') for k in results_json["task_results"][0].keys() 
                  if k.startswith('result_')]
    
    # Analyze each failed task
    analysis_results = {}
    
    for task_id in failed_tasks:
        print(f"Analyzing task: {task_id}")
        
        # Get the original patch
        original_patch = get_patch_from_dataset(dataset, task_id)
        
        # Get the problem statement for context
        problem_statement = get_problem_statement(dataset, task_id)
        
        # Get model-generated patches
        model_patches = get_model_generated_patches(task_id, model_names)
        
        if not model_patches:
            print(f"No model patches found for {task_id}, skipping...")
            continue  # Skip if no model patches found
        
        # Compare patches
        task_analysis = {
            "task_id": task_id,
            "problem_statement": problem_statement,
            "model_comparisons": {}
        }
        
        for model_name, model_patch in model_patches.items():
            print(f"  Comparing {model_name} patch with OpenAI...")
            comparison = compare_patches_with_openai(original_patch, model_patch, problem_statement)
            task_analysis["model_comparisons"][model_name] = comparison
        
        analysis_results[task_id] = task_analysis
    
    return analysis_results

def save_analysis_to_file(analysis_results):
    """
    Save the analysis results to a formatted text file for easy reading.
    
    Args:
        analysis_results (dict): The analysis results
    """
    with open('failed_tasks_analysis.txt', 'w') as f:
        f.write("# Analysis of Tasks Where All Models Failed\n\n")
        
        for task_id, analysis in analysis_results.items():
            f.write(f"## Task: {task_id}\n\n")
            
            if "problem_statement" in analysis and analysis["problem_statement"]:
                f.write("### Problem Statement\n")
                f.write(f"{analysis['problem_statement'][:500]}...\n\n")
            
            for model_name, comparison in analysis["model_comparisons"].items():
                f.write(f"### Model: {model_name}\n")
                f.write(f"{comparison}\n\n")
            
            f.write("-" * 80 + "\n\n")
    
    print("Analysis saved to failed_tasks_analysis.txt")

def extract_all_patches(dataset, output_folder="patches", model_names=None):
    """
    Extract all patch diffs from the dataset and save them to a folder structure:
    output_folder/
        {task_id}/
            {model_name}/
                patch.diff
    
    Args:
        dataset: The Kotlin-bench dataset
        output_folder (str): The main folder where patches will be saved
        model_names (list, optional): List of model names to extract patches for. 
                                     If None, will try to detect from logs directory.
    
    Returns:
        int: Number of patches extracted
    """
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # If model_names is not provided, try to detect from logs directory
    if model_names is None:
        model_names = []
        model_dirs = [d for d in os.listdir(logs_dir) if os.path.isdir(os.path.join(logs_dir, d))]
        for model_dir in model_dirs:
            if os.path.isdir(os.path.join(logs_dir, model_dir)):
                # Check if this is a model directory or a task directory
                potential_model_dir = os.path.join(logs_dir, model_dir)
                subdirs = [d for d in os.listdir(potential_model_dir) if os.path.isdir(os.path.join(potential_model_dir, d))]
                if "unknown" in subdirs:
                    model_names.append(model_dir)
    
    if not model_names:
        print("Warning: No model names provided or detected. Only original PR patches will be extracted.")
    
    count = 0
    
    # Process each task in the dataset
    for task in dataset:
        task_id = task["instance_id"]
        
        # Create task directory
        task_dir = os.path.join(output_folder, task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        # Save original PR patch
        original_patch = task.get("patch", "")
        if original_patch:
            # Create original model directory
            original_dir = os.path.join(task_dir, "original")
            os.makedirs(original_dir, exist_ok=True)
            
            # Save the original patch
            patch_path = os.path.join(original_dir, "patch.diff")
            with open(patch_path, 'w') as f:
                f.write(original_patch)
            count += 1
        
        # Extract model-generated patches
        for model_name in model_names:
            model_patch_path = os.path.join(logs_dir, task_id, model_name, "patch.diff")
            
            if os.path.exists(model_patch_path):
                try:
                    # Create model directory
                    model_dir = os.path.join(task_dir, model_name)
                    os.makedirs(model_dir, exist_ok=True)
                    
                    # Read and save the model patch
                    with open(model_patch_path, 'r') as src_f:
                        model_patch = src_f.read()
                        
                    target_path = os.path.join(model_dir, "patch.diff")
                    with open(target_path, 'w') as dest_f:
                        dest_f.write(model_patch)
                    
                    count += 1
                except Exception as e:
                    print(f"Error extracting patch for task {task_id}, model {model_name}: {e}")
    
    print(f"Extracted {count} patches to {output_folder}/ directory")
    return count

def main():
    # # Main analysis
    print("Starting Kotlin Benchmark Analysis")

    # Check if OpenAI API key is set
    # if not openai.api_key and not os.environ.get("OPENAI_API_KEY"):
    #     print("Warning: OpenAI API key is not set. Please set it in the code or as an environment variable.")
    #     return

    # # Load the dataset
    dataset = load_dataset()

    # Extract task information
    task_info_df = extract_task_info(dataset)
    print("\nFirst task information:")
    print(task_info_df.iloc[0])

    # Load model reports
    model_reports = load_model_reports()

    # Create model to result mapping
    result_df = create_model_result_mapping(task_info_df, model_reports)

    # Display results
    print("\nTask information with model results:")
    print(result_df.head())

    # Analyze model performance
    performance_df = analyze_model_performance(result_df)
    print("\nModel Performance Summary:")
    print(performance_df)

    # Save results to JSON file
    results_json = save_to_json(result_df, performance_df)
    
    # Analyze failed tasks
    analysis_results = analyze_failed_tasks(dataset, results_json)
    
    # Save analysis to file
    save_analysis_to_file(analysis_results)
    
    # Extract all patches to a separate folder
    extract_all_patches(dataset, "patches", [
        "deepseek-r1",
        "deepseek-v3-0324",
        "o1",
        "o3-mini",
        "gpt-4o-2024-11-20",
        "gemini-2.5-pro-exp-03-25",
        "claude-3-7-sonnet-20250219",
        "claude-3-7-sonnet-20250219-thinking",
        "llama4-maverick-instruct-basic",
        "gpt-4.1"
    ])

    print("\nAnalysis complete. Results saved to JSON file and analysis file.")


def get_all_failed_issues(results_json):
    """
    Returns a list of issue URLs for tasks where all models failed.
    
    Args:
        results_json (dict): The JSON results containing task results and model performance
        
    Returns:
        list: List of issue URLs where all models failed
    """
    all_failed_issues = []
    
    # Iterate through each task result
    for task in results_json["task_results"]:
        # Get all result fields that start with 'result_'
        result_fields = [k for k in task.keys() if k.startswith('result_')]
        
        # Check if all results are 'failed'
        if all(task[field] == 'failed' for field in result_fields):
            # Add the issue URLs to our list
            all_failed_issues.extend(task.get('issue_urls', []))
    
    return all_failed_issues


if __name__ == "__main__":
    main() 