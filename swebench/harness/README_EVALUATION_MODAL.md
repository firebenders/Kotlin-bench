# SWE-Bench Modal Evaluation System

This document explains how to use the Modal-based evaluation system for SWE-Bench task predictions.

## Overview

The original `run_evaluation.py` used Docker to evaluate model predictions on SWE-Bench tasks. This new system (`run_evaluation_modal.py`) leverages [Modal](https://modal.com/) for distributed cloud execution, which offers several advantages:

- Faster evaluations through distributed cloud computing
- Persistent shared volumes for efficient repository and JDK management
- Better resource utilization and scalability
- Support for Android SDK and JVM-based repositories

## Prerequisites

1. Install Modal:
```bash
pip install modal
```

2. Set up your Modal account:
```bash
modal setup
```

3. Ensure you have the necessary dependencies:
```bash
pip install datasets tqdm
```

## Usage

Run evaluations with:

```bash
modal run swebench/harness/run_evaluation_modal.py \
  --predictions_path path/to/predictions.json \
  --output_log_dir ./evaluation_logs
```

### Command Line Arguments

- `--dataset_name`: Dataset name (default: "princeton-nlp/SWE-bench_Lite")
- `--split`: Dataset split to use (default: "test")
- `--predictions_path`: Path to the predictions JSON file (**required**)
- `--output_log_dir`: Directory for storing log files (default: "evaluation_logs")
- `--session_id`: Custom session ID (default: auto-generated)

## Prediction Format

The prediction file should be a JSON array containing objects with:

```json
[
  {
    "instance_id": "repo-issue_number",
    "model_name_or_path": "org/model-name",
    "model_patch": "git diff patch content"
  },
  ...
]
```

## Volumes and Caching

The system uses Modal volumes for caching:

- `logs-volume`: Stores evaluation logs
- `jdk-volume`: Caches installed JDK versions
- `repos-volume`: Caches cloned repositories 
- `android-sdk-volume`: Stores Android SDK installation

These volumes persist between runs, improving efficiency for repeated evaluations.

## Output

The evaluation system generates:

1. A summary report in the log directory
2. Detailed logs for each task instance
3. A model-specific report with resolution status for each instance

## Example

```bash
modal run swebench/harness/run_evaluation_modal.py \
  --predictions_path predictions/kotlin_bench_predictions.json \
  --output_log_dir ./kotlin_eval_logs
```

This runs evaluations for all provided predictions in the Kotlin-bench dataset.

## Differences from Original Evaluation

The Modal-based system differs from the original evaluation system in several ways:

1. Uses distributed cloud execution instead of local Docker containers
2. Repository setup is handled through shared volumes
3. The evaluation environment is prepared using `ModalTaskEnvManager` instead of Docker containers
4. JDK and Android SDK installations are shared across runs
5. Evaluation results are handled differently due to the distributed nature

Despite these differences, the evaluation criteria and outcome determination remain the same. 