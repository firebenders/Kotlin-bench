import argparse
import datetime
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import re
from abc import ABC, abstractmethod
import importlib
import sys

import modal
from modal import Image, Volume, Mount, App

from swebench.harness.utils import load_swebench_dataset
from swebench.harness.grading import get_logs_eval, get_eval_report, get_resolution_status
from swebench.metrics.report import get_model_eval_summary, get_model_report, save_model_report_kt
from swebench.harness.constants import PatchType

class BaseAgent:
    """
    Base class for SWEBench agents.
    This interface should be implemented by all agents that want to participate
    in the SWEBench evaluation.
    """
    
    def __init__(
        self,
        model_name: str = "GPT_4O",
        env_prompt_file: Optional[str] = None,
        log_dir: str = "/tmp/agents",
        verbose: bool = False,
        max_iterations: int = 30
    ):
        """
        Initialize the BaseAgent.
        
        Args:
            model_name: The name of the model to use
            env_prompt_file: Path to the environment prompt file
            log_dir: Directory to store logs
            verbose: Whether to print verbose logs
            max_iterations: Maximum number of agent iterations
        """
        self.model_name = model_name
        self.env_prompt_file = env_prompt_file
        self.log_dir = log_dir
        self.verbose = verbose
        self.max_iterations = max_iterations
    
    def solve_task(self, instance: Dict[str, Any], workspace_dir: Optional[str] = None) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Solve a single task instance using the agent.
        
        Args:
            instance: The task instance to solve
            workspace_dir: Directory containing the workspace files
            
        Returns:
            Tuple containing (success, conversation_history)
        """
        raise NotImplementedError("Subclasses must implement solve_task")

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
    timeout=3600
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

@app.function(volumes={"/logs": logs_volume}, timeout=3600)
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

@app.function(
    volumes={
        "/logs": logs_volume, 
        "/root/.sdkman/candidates/java": jdk_volume, 
        "/repos": repos_volume,
        "/root/android-sdk": android_sdk_volume
    },
    timeout=3600,
    cpu=4.0,
    memory=8000
)
def evaluate_agent_prediction(
    task_instance: Dict[str, Any],
    model_name: str,
    volume_log_dir: str,
    agent_module_path: str = "swebench.agents.default_agent",
    agent_class_name: str = "DefaultAgent",
    timeout: int = 3600
) -> Dict[str, Any]:
    """Evaluate a single task instance using the specified agent."""
    import os
    import subprocess
    from swebench.harness.context_manager_modal import ModalTaskEnvManager

    print(f"Evaluating agent prediction for:")
    print(f"- Task instance ID: {task_instance['instance_id']}")
    print(f"- Model: {model_name}")
    print(f"- Agent: {agent_module_path}.{agent_class_name}")
    print(f"- Volume log directory: {volume_log_dir}")
    print(f"- Timeout: {timeout} seconds")
    
    instance_id = task_instance["instance_id"]
    repo = task_instance["repo"]
    version = task_instance["version"]
    
    # Setup working directory
    repo_path = get_repo_path(repo)
    work_dir = f"/tmp/{repo.replace('/', '_')}_{version}_{instance_id}"
    os.makedirs(work_dir, exist_ok=True)
    print(f"Setting up working directory: {work_dir}")
    
    try:
        # Copy repository to working directory once
        print(f"Copying repository {repo} to working directory: {work_dir}")
        subprocess.run(["cp", "-r", f"{repo_path}/.", work_dir], check=True)
        print(f"Copied repository to working directory: {work_dir}")

        # Setup logging for this prediction
        task_volume_log_dir = os.path.join(volume_log_dir, instance_id, model_name)
        print(f"Setting up task volume log directory: {task_volume_log_dir}")
        
        # Create agent log directory
        agent_log_dir = os.path.join(task_volume_log_dir, "agent_logs")
        os.makedirs(agent_log_dir, exist_ok=True)
        print(f"Created agent log directory at {agent_log_dir}")

        with ModalTaskEnvManager(
            task_instance,
            work_dir,
            task_volume_log_dir,
            verbose=True,
            timeout=timeout,
            jdk_volume_path="/root/.sdkman/candidates/java",
            android_sdk_path="/root/android-sdk"
        ) as tcm:
            # Initial setup only needs to be done once
            if not (tcm.reset_task_env(task_instance) and tcm.run_install_task(task_instance)):
                print("Failed to setup environment")
                return {"instance_id": instance_id, "error": "Failed to setup environment"}
            
            # Setup logging for this prediction
            os.makedirs(task_volume_log_dir, exist_ok=True)
            test_output_path = os.path.join(task_volume_log_dir, f"{instance_id}.log")
            report_filename = f"report_{model_name}.json"
            report_path = os.path.join(task_volume_log_dir, report_filename)
            print(f"Report path: {report_path}")
            
            # Skip if already evaluated
            if os.path.exists(report_path):
                print(f"Report already exists at {report_path}, loading existing report")
                with open(report_path, 'r') as f:
                    return {"instance_id": instance_id, "report": json.load(f)}
            
            try:
                print(f"Creating base result structure for instance {instance_id}")
                # Create base result structure
                result = {
                    "instance_id": instance_id,
                    "model_name": model_name,
                    "source_file": "",
                    "patch_is_None": False,
                    "patch_exists": False,
                    "patch_successfully_applied": False,
                    "resolved": False,
                    "tests_status": None
                }
                
                try:
                    print("Loading agent implementation")
                    # Dynamically load agent implementation
                    print(f"Using agent module: {agent_module_path}, class: {agent_class_name}")
                    
                    # Add the current directory to sys.path if needed
                    if "." in agent_module_path:
                        print("Adding current directory to sys.path")
                        sys.path.append(os.getcwd())
                    
                    print("Importing agent module and getting agent class")
                    agent_module = importlib.import_module(agent_module_path)
                    AgentClass = getattr(agent_module, agent_class_name)
                    
                    print(f"Instantiating agent with model: {model_name}")
                    # Instantiate and run agent
                    agent = AgentClass(model_name=model_name, log_dir=agent_log_dir)
                    
                    print("Starting agent execution")
                    # Record start time for agent execution
                    agent_start_time = datetime.datetime.now()
                    
                    print("Running agent solve_task")
                    success, conversation_history = agent.solve_task(task_instance, work_dir)
                    agent_result = success
                    
                    print("Agent execution completed")
                    # Record end time and total duration
                    agent_end_time = datetime.datetime.now()
                    agent_duration = (agent_end_time - agent_start_time).total_seconds()
                    print(f"Agent execution took {agent_duration} seconds")
                    
                    print("Adding agent metadata to result")
                    # Add agent metadata to result
                    result["agent_execution_time"] = agent_duration
                    result["agent_reports_success"] = agent_result
                    result["conversation_history_length"] = len(conversation_history) if isinstance(conversation_history, list) else 0
                except Exception as e:
                    print(f"Error running agent: {str(e)}")
                    result["agent_error"] = str(e)
                    import traceback
                    print(traceback.format_exc())
                
                # Run tests
                if not success:
                    print(f"Agent failed to solve task for {instance_id} {model_name}")
                else:
                    if task_instance["test_patch"]:
                        tcm.apply_patch(task_instance["test_patch"], patch_type=PatchType.PATCH_TEST.value)
                    else:
                        print(f"No test patch provided for {instance_id} {model_name}")
                        success = False
                        return {
                            "instance_id": instance_id,
                            "model_name": model_name,
                            "error": "No test patch provided"
                        }

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

                # Save report with model-specific filename
                with open(report_path, "w") as f:
                    json.dump(result, f, indent=4)
                
                return {
                    "instance_id": instance_id,
                    "model_name": model_name,
                    "source_file": "unknown",
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

def run_agent_evaluation(
    dataset_name: str,
    model_name: str,
    output_log_dir: str,
    agent: str = "default",
    split: str = "test",
    instance_id: str = None,
    rerun_failed_only: bool = False
):
    """Run agentic evaluation for a single model on a dataset"""
    # Load and filter dataset
    dataset = load_swebench_dataset(dataset_name, split)
    
    # Filter to specific instance if provided
    if instance_id:
        dataset = [task for task in dataset if task.get("instance_id") == instance_id]
        if not dataset:
            print(f"No task found with instance_id: {instance_id}")
            return
        print(f"Filtered to single task instance: {instance_id}")
    
    if not dataset:
        print("No instances to evaluate.")
        return
    
    # Filter out tasks that have already been successfully completed
    if rerun_failed_only:
        filtered_dataset = []
        for task in dataset:
            task_id = task.get("instance_id")
            report_path = os.path.join(output_log_dir, task_id, model_name, f"report_{model_name}.json")
            
            # Include task if report doesn't exist or agent_reports_success is False
            should_run = True
            if os.path.exists(report_path):
                try:
                    with open(report_path, 'r') as f:
                        report_data = json.load(f)
                        # Skip if agent_reports_success is True
                        if report_data.get("agent_reports_success", False):
                            should_run = False
                            print(f"Skipping {task_id} for {model_name} - already successful")
                except Exception as e:
                    print(f"Error reading report {report_path}: {e}")
            
            if should_run:
                filtered_dataset.append(task)
        
        print(f"Filtered from {len(dataset)} to {len(filtered_dataset)} instances that need to be run or re-run")
        dataset = filtered_dataset
        
        if not dataset:
            print("No failed instances to re-run.")
            return

    # Setup logging
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    volume_log_dir = f"/logs/eval_{timestamp}"
    os.makedirs(output_log_dir, exist_ok=True)
    
    print(f"Evaluating {model_name} with agent '{agent}' on {len(dataset)} instances...")
    
    # Determine agent module and class name
    agent_module_path = "swebench.agents.default_agent"
    agent_class_name = "DefaultAgent"
    
    # Configure agent module and class name
    if agent == "default":
        agent_module_path = "swebench.agents.default_agent"
        agent_class_name = "DefaultAgent"
    elif agent == "llm":
        agent_module_path = "swebench.agents.llm_agent_template" 
        agent_class_name = "LLMBasedAgent"
    elif agent == "firebender":
        agent_module_path = "swebench.agents.firebender_agent"
        agent_class_name = "FirebenderAgent"
    else:
        # Assume the agent parameter contains the full module.class specification
        if "." in agent:
            agent_module_path, agent_class_name = agent.rsplit(".", 1)
        else:
            print(f"Invalid agent specification: {agent}")
            return
    
    print(f"Using agent module: {agent_module_path}, class: {agent_class_name}")
    
    # Initialize repositories in parallel
    repos = list({i["repo"] for i in dataset})
    print(f"Setting up {len(repos)} repositories in parallel...")
    repo_results = list(initialize_repo_volume.map(repos, return_exceptions=True))
    
    # Prepare inputs for parallel agentic evaluation - flatten to evaluate each prediction individually
    eval_inputs = []
    for task_instance in dataset:
        # No need to look up the task again since we already have it
        eval_inputs.append((task_instance, model_name, volume_log_dir, agent_module_path, agent_class_name))
    print(f"Starting parallel agentic evaluation of {len(eval_inputs)} instances...")
    
    # Run evaluations in parallel
    for agent_eval_result in evaluate_agent_prediction.starmap(eval_inputs, return_exceptions=True):
        if isinstance(agent_eval_result, Exception):
            print(f"Warning: Agentic evaluation failed: {agent_eval_result}")
            continue

    # Copy logs from volume to local
    print(f"Copying logs from volume to local directory: {output_log_dir}")
    files_data = copy_logs_to_local.remote(volume_log_dir)

    if files_data:
        files_copied = 0
        for filename, content in files_data.items():
            try:
                file_path = os.path.join(output_log_dir, filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(content)
                files_copied += 1
            except Exception as e:
                print(f"Error writing file {filename}: {e}")
        print(f"Successfully copied {files_copied} log files to {output_log_dir}")
    else:
        print("Warning: Failed to copy logs from volume")

@app.local_entrypoint()
def main(*arglist):
    """Modal entrypoint that parses command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_name", default="princeton-nlp/SWE-bench_Lite", help="Dataset name or path")
    parser.add_argument("--model_name", required=True, help="Model to evaluate")
    parser.add_argument("--output_log_dir", required=True, help="Directory for logs")
    parser.add_argument("--split", default="test", help="Dataset split")
    parser.add_argument("--agent", default="default", help="Agent to use. Can be 'default', 'llm', 'firebender', or a full module.class specification")
    parser.add_argument("--instance_id", help="Specific instance ID to evaluate (optional)")
    parser.add_argument("--rerun_failed_only", action="store_true", help="Only rerun instances that failed or don't have results")
    
    args = parser.parse_args(arglist)
    
    run_agent_evaluation(
        dataset_name=args.dataset_name,
        model_name=args.model_name,
        output_log_dir=args.output_log_dir,
        agent=args.agent,
        split=args.split,
        instance_id=args.instance_id,
        rerun_failed_only=args.rerun_failed_only
    )

    report = calculate_resolved_percentage()
    print(report)

def calculate_resolved_percentage():
    # Path to the agent_evaluation_logs directory
    base_dir = "agent_evaluation_logs"
    
    # Find all report_*.json files
    report_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.startswith("report_") and file.endswith(".json"):
                report_files.append(os.path.join(root, file))
    
    total_reports = len(report_files)
    resolved_reports = 0
    
    # Process each report file
    for report_file in report_files:
        try:
            with open(report_file, 'r') as f:
                data = json.load(f)
                if data.get("resolved", False):
                    resolved_reports += 1
        except Exception as e:
            print(f"Error processing {report_file}: {e}")
    
    # Calculate percentage
    percentage = (resolved_reports / total_reports * 100) if total_reports > 0 else 0
    
    return {
        "total_reports": total_reports,
        "resolved_reports": resolved_reports,
        "percentage_resolved": percentage
    }

# Example command to run the evaluation:
# modal run swebench/harness/run_evaluation_agent_modal.py \
#   --model_name "claude-3.7-sonnet" \
#   --output_log_dir ./agent_evaluation_logs \
#   --dataset_name ./datasets/Kotlin-bench \
#   --split test \
#   --agent firebender \
#   --instance_id wordpress-mobile__WordPress-Android-18959