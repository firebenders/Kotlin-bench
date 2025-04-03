import argparse
import datetime
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
import re

import modal
from modal import Image, Volume, Mount, App

from swebench.harness.utils import load_swebench_dataset
from swebench.harness.grading import get_logs_eval, get_eval_report, get_resolution_status
from swebench.metrics.report import get_model_eval_summary, get_model_report, save_model_report_kt
from swebench.harness.constants import PatchType

# Define base image with required dependencies
base_image = (
    modal.Image.debian_slim()
    .apt_install(["git", "curl", "zip", "unzip", "ca-certificates"])
    .pip_install([
        "datasets",
        "docker",
        "pre-commit",
        "requests",
        "tqdm",
        "ghapi",
        "GitPython",
        "python-dotenv",
        "bs4",
        "unidiff"
    ])
    .run_commands([
        # Add this line to set JVM arguments that fix the ByteBuddy/Mockito issue
        'echo "export JAVA_TOOL_OPTIONS=-Dmockito.mock.maker=org.mockito.internal.creation.bytebuddy.SubclassByteBuddyMockMaker -Djdk.attach.allowAttachSelf=true" >> /etc/profile'
    ])
    .add_local_dir(
        "swebench",
        remote_path="/root/swebench",
        ignore=lambda path: (
            str(path).endswith(".pyc") or 
            "__pycache__" in str(path) or
            ".git" in str(path)
        ),
        copy=True
    )
)

# Create Modal app and volumes
app = modal.App("swebench-evaluation", image=base_image)
logs_volume = modal.Volume.from_name("logs-volume", create_if_missing=True)
jdk_volume = modal.Volume.from_name("jdk-volume", create_if_missing=True)
repos_volume = modal.Volume.from_name("repos-volume", create_if_missing=True)
android_sdk_volume = modal.Volume.from_name("android-sdk-volume", create_if_missing=True)

def get_repo_path(repo: str) -> str:
    """Generate path for repository within shared volume."""
    repo_dir = repo.replace('/', '__')
    return f"/repos/{repo_dir}"

@app.function(
    volumes={"/repos": repos_volume},
    timeout=1800
)
def initialize_repo_volume(repo: str) -> bool:
    """Initialize repository in shared volume."""
    import os
    from swebench.harness.utils import clone_repo
    import subprocess
    
    repo_path = get_repo_path(repo)
    os.makedirs(repo_path, exist_ok=True)
    
    # Check if repo exists and reset if it does
    if os.path.exists(os.path.join(repo_path, ".git")):
        try:
            os.chdir(repo_path)
            subprocess.run(["git", "restore", "."], check=False)
            subprocess.run(["git", "reset", "HEAD", "."], check=False)
            subprocess.run(["git", "clean", "-fdx"], check=False)
            subprocess.run(["git", "fetch", "--all"], check=False)
            return True
        except Exception as e:
            print(f"Failed to reset repository: {e}")
    
    # Clone repository if needed
    return clone_repo(repo, repo_path, use_original_repo=True)

@app.function(
    volumes={
        "/logs": logs_volume, 
        "/root/.sdkman/candidates/java": jdk_volume, 
        "/repos": repos_volume,
        "/root/android-sdk": android_sdk_volume
    },
    timeout=1800,
    cpu=4.0,
    memory=8000
)
def evaluate_prediction(
    task_instance: Dict[str, Any],
    prediction: Dict[str, Any],
    volume_log_dir: str,
    timeout: int = 1800
) -> Dict[str, Any]:
    """Evaluate multiple predictions for a single task instance in the same container."""
    import os
    import subprocess
    from swebench.harness.context_manager_modal import ModalTaskEnvManager
    
    instance_id = task_instance["instance_id"]
    repo = task_instance["repo"]
    version = task_instance["version"]
    
    # Setup working directory
    repo_path = get_repo_path(repo)
    work_dir = f"/tmp/{repo.replace('/', '_')}_{version}_{instance_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    try:
        # Copy repository to working directory once
        subprocess.run(["cp", "-r", f"{repo_path}/.", work_dir], check=True)
        
        # Create environment manager once
        model_name = prediction.get("model_name_or_path", "unknown").replace("/", "__")

        # Setup logging for this prediction
        task_prediction_log_dir = os.path.join(volume_log_dir, instance_id, model_name)
            
        with ModalTaskEnvManager(
            task_instance,
            work_dir,
            task_prediction_log_dir,
            verbose=True,
            timeout=timeout,
            jdk_volume_path="/root/.sdkman/candidates/java",
            android_sdk_path="/root/android-sdk"
        ) as tcm:
            # Initial setup only needs to be done once
            if not (tcm.reset_task_env(task_instance) and tcm.run_install_task(task_instance)):
                return [{"instance_id": instance_id, "error": "Failed to setup environment"}]
            
            # Setup logging for this prediction
            os.makedirs(task_prediction_log_dir, exist_ok=True)
            test_output_path = os.path.join(task_prediction_log_dir, f"{instance_id}.log")
            report_filename = f"report_{model_name}.json"
            report_path = os.path.join(task_prediction_log_dir, report_filename)
            patch_path = os.path.join(task_prediction_log_dir, "patch.diff")
            
            # Save the patch
            with open(patch_path, "w") as f:
                f.write(prediction.get("model_patch", ""))
            
            # Skip if already evaluated
            if os.path.exists(report_path):
                with open(report_path, 'r') as f:
                    return {"instance_id": instance_id, "report": json.load(f)}
            
            try:
                # Create base result structure
                result = {
                    "instance_id": instance_id,
                    "model_name": prediction.get("model_name_or_path", "unknown"),
                    "source_file": prediction.get("source_file", "unknown"),
                    "patch_is_None": prediction["model_patch"] is None or len(prediction["model_patch"].strip()) == 0,
                    "patch_exists": False,
                    "patch_successfully_applied": False,
                    "resolved": False,
                    "tests_status": None
                }
                
                # Check if patch exists
                if not result["patch_is_None"]:
                    result["patch_exists"] = True

                    # Apply test patch
                    tcm.apply_patch(task_instance["test_patch"], patch_type=PatchType.PATCH_TEST.value)
                    
                    # Determine if this is a patch or full file format
                    is_full_file = bool(re.search(r'\[start of [\w\.\-\/]+\]', prediction["model_patch"]))
                    print(f"Is full file: {is_full_file}")

                    # Apply AI prediction based on format
                    if is_full_file:
                        print("Applying full file changes")
                        success = tcm.apply_full_file_changes(prediction["model_patch"], patch_type=PatchType.PATCH_PRED.value)
                        print("Application success: ", success)
                    else:
                        success = tcm.apply_patch(prediction["model_patch"], patch_type=PatchType.PATCH_PRED.value)

                    if success:
                        result["patch_successfully_applied"] = True
                        print("Running tests")
                        tcm.run_tests_task(task_instance)
                        
                        if os.path.exists(test_output_path):
                            try:
                                # Parse test results using SWE-bench grading
                                print(f"Parsing test logs: {test_output_path}")
                                eval_sm, found = get_logs_eval(test_output_path, repo)
                                print(f"Eval SM: {eval_sm}")
                                print(f"Found: {found}")
                                
                                if found:
                                    # Create gold results in expected format
                                    gold_results = {
                                        "FAIL_TO_PASS": task_instance["FAIL_TO_PASS"],
                                        "PASS_TO_PASS": task_instance["PASS_TO_PASS"]
                                    }
                                    
                                    # Generate report using SWE-bench utilities
                                    tests_report = get_eval_report(eval_sm, gold_results)
                                    resolution_status = get_resolution_status(tests_report)
                                    
                                    result["tests_status"] = tests_report
                                    result["resolved"] = resolution_status == "RESOLVED_FULL"
                            except Exception as e:
                                print(f"Error parsing test results: {str(e)}")
                        else:
                            print(f"No test output file found for {instance_id} {model_name}")
                    else:
                        print(f"Patch failed to apply for {instance_id} {model_name}")

                # Save report with model-specific filename
                with open(report_path, "w") as f:
                    json.dump(result, f, indent=4)
                
                return {
                    "instance_id": instance_id,
                    "model_name": prediction.get("model_name_or_path", "unknown"),
                    "source_file": prediction.get("source_file", "unknown"),
                    "report": result
                }
                
            except Exception as e:
                print(f"Error evaluating prediction: {str(e)}")
                return {
                    "instance_id": instance_id, 
                    "error": f"Error evaluating prediction: {str(e)}"
                }
    
    except Exception as e:
        return {
            "instance_id": instance_id, 
            "error": f"Container-level error: {str(e)}"
        }

@app.function(volumes={"/logs": logs_volume})
def process_results(results: List[Dict[str, Any]], volume_log_dir: str) -> Dict[str, Any]:
    """Process and summarize evaluation results."""
    # Track results by model
    model_results = defaultdict(lambda: {
        "completed_ids": set(),
        "resolved_ids": set(),
        "error_ids": set()
    })
    
    for result in results:
        instance_id = result.get("instance_id")
        model_name = result.get("model_name", "unknown")
        if not instance_id:
            continue
            
        if "error" in result:
            model_results[model_name]["error_ids"].add(instance_id)
        elif "report" in result:
            model_results[model_name]["completed_ids"].add(instance_id)
            if result["report"].get(instance_id, {}).get("resolved", False):
                model_results[model_name]["resolved_ids"].add(instance_id)
    
    # Create summary per model
    summary = {
        "total_results": len(results),
        "models": {}
    }
    
    for model_name, stats in model_results.items():
        summary["models"][model_name] = {
            "total_instances": len(stats["completed_ids"] | stats["error_ids"]),
            "completed_instances": len(stats["completed_ids"]),
            "resolved_instances": len(stats["resolved_ids"]),
            "error_instances": len(stats["error_ids"]),
            "completed_ids": list(sorted(stats["completed_ids"])),
            "resolved_ids": list(sorted(stats["resolved_ids"])),
            "error_ids": list(sorted(stats["error_ids"]))
        }
    
    # Save summary
    summary_path = os.path.join(volume_log_dir, "evaluation_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    return summary

@app.function(volumes={"/logs": logs_volume}, timeout=1800)
def copy_logs_to_local(volume_log_dir: str) -> Dict[str, bytes]:
    """Copy logs from volume to local storage."""
    import os
    import glob
    
    files_data = {}
    try:
        for filepath in glob.glob(f"{volume_log_dir}/**/*", recursive=True):
            if os.path.isfile(filepath):
                rel_path = os.path.relpath(filepath, volume_log_dir)
                with open(filepath, 'rb') as f:
                    files_data[rel_path] = f.read()
        return files_data
    except Exception as e:
        print(f"Error copying logs: {e}")
        return {}

def load_predictions_from_directory(predictions_dir: str) -> List[Dict[str, Any]]:
    """Load and group predictions from all JSONL files in the directory by instance_id."""
    predictions = []
    
    # Iterate through all JSONL files in the directory
    for file_path in Path(predictions_dir).glob('*.jsonl'):
        try:
            with open(file_path) as f:
                for line in f:
                    prediction = json.loads(line)
                    predictions.append(prediction)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    return predictions

def run_evaluation(
    predictions_dir: str,
    output_log_dir: str,
    dataset_name: str,
    split: str = "test"
):
    """Run the evaluation process for multiple prediction files."""
    # Load all predictions and group by instance
    predictions = load_predictions_from_directory(predictions_dir)
    
    if not predictions:
        print("No predictions found in directory.")
        return
    
    # Load and filter dataset
    dataset = load_swebench_dataset(dataset_name, split)
    task_ids_from_predictions = {pred["instance_id"] for pred in predictions}
    dataset = [i for i in dataset if i["instance_id"] in task_ids_from_predictions]
    
    # if not dataset:
    #     print("No instances to evaluate.")
    #     return
    
    # # Setup logging
    # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # volume_log_dir = f"/logs/eval_{timestamp}"
    # os.makedirs(output_log_dir, exist_ok=True)
    
    # print(f"Evaluating {len(dataset)} instances with {len(predictions)} total predictions...")
    
    # # Initialize repositories in parallel
    # repos = list({i["repo"] for i in dataset})
    # print(f"Setting up {len(repos)} repositories in parallel...")
    # repo_results = list(initialize_repo_volume.map(repos, return_exceptions=True))
    
    # Prepare inputs for parallel evaluation - flatten to evaluate each prediction individually
    # eval_inputs = []
    # for prediction in predictions:
    #     instance_id = prediction["instance_id"]
    #     task_instance = next((i for i in dataset if i["instance_id"] == instance_id), None)
    #     if task_instance:
    #         eval_inputs.append((task_instance, prediction, volume_log_dir))
    # print(f"Starting parallel evaluation of {len(eval_inputs)} predictions...")
    
    # Run evaluations in parallel
    # for prediction_result in evaluate_prediction.starmap(eval_inputs, return_exceptions=True):
    #     if isinstance(prediction_result, Exception):
    #         print(f"Warning: Prediction evaluation failed: {prediction_result}")
    #         continue
    
    # Process results and copy logs
    # summary = process_results.remote(all_results, volume_log_dir)
    
    # Copy logs from volume to local
    # print(f"Copying logs from volume to local directory: {output_log_dir}")
    # files_data = copy_logs_to_local.remote(volume_log_dir)
     
    # if files_data:
    #     files_copied = 0
    #     for filename, content in files_data.items():
    #         try:
    #             file_path = os.path.join(output_log_dir, filename)
    #             os.makedirs(os.path.dirname(file_path), exist_ok=True)
    #             with open(file_path, 'wb') as f:
    #                 f.write(content)
    #             files_copied += 1
    #         except Exception as e:
    #             print(f"Error writing file {filename}: {e}")
    #     print(f"Successfully copied {files_copied} log files to {output_log_dir}")
    # else:
    #     print("Warning: Failed to copy logs from volume")
    
    # Generate reports using SWE-bench utilities
    print("\nGenerating evaluation reports...")
    os.makedirs(os.path.join(output_log_dir, "reports"), exist_ok=True)  # Create reports directory
    
    for prediction_file in Path(predictions_dir).glob("*.jsonl"):
        print(f"\nProcessing predictions from: {prediction_file}")
        try:
            detailed_report = save_model_report_kt(
                str(prediction_file),
                dataset,
                output_log_dir,
                verbose=True
            )
            
            print(f"Report statistics:")
            print(f"- Generated patches: {len(detailed_report['generated'])}")
            print(f"- Successfully applied: {len(detailed_report['applied'])}")
            print(f"- Resolved cases: {len(detailed_report['resolved'])}")
            
        except Exception as e:
            print(f"Error generating report for {prediction_file}: {e}")

@app.local_entrypoint()
def main(*arglist):
    """Modal entrypoint that parses command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions_dir", required=True, help="Directory containing prediction JSONL files")
    parser.add_argument("--output_log_dir", required=True, help="Directory for logs")
    parser.add_argument("--dataset_name", default="princeton-nlp/SWE-bench_Lite", help="Dataset name or path")
    parser.add_argument("--split", default="test", help="Dataset split")
    
    args = parser.parse_args(arglist)
    
    run_evaluation(
        predictions_dir=args.predictions_dir,
        output_log_dir=args.output_log_dir,
        dataset_name=args.dataset_name,
        split=args.split
    )

#   modal run swebench/harness/run_evaluation_modal.py \
#   --predictions_dir ./predictions/Kotlin-bench-full-file \
#   --output_log_dir ./evaluation_logs \
#   --dataset_name ./datasets/SWE-bench__full_file_gen__fs-oracle \
#   --split test