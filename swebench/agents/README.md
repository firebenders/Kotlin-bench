# SWE-bench Agent Implementations

This directory contains agent implementations for SWE-bench tasks.

## Implementing a Custom Agent

Agents in SWE-bench must implement the `BaseAgent` abstract base class defined in `swebench/harness/run_evaluation_agent_modal.py`. The main method to implement is:

```python
def solve_task(self, task_instance: Dict[str, Any], workspace_dir: str, agent_log_dir: str) -> bool:
    """
    Solve the given task by modifying files in the workspace directory.
    
    Args:
        task_instance: Dictionary containing task details
        workspace_dir: Directory containing the repository code to modify
        agent_log_dir: Directory where agent can store logs, conversation history, etc.
        
    Returns:
        bool: True if agent believes it successfully solved the task, False otherwise
    """
    pass
```

## Implementing Your Own Agent

To implement your own agent:

1. Create a new Python file in this directory (e.g., `my_agent.py`)
2. Define a class that extends `BaseAgent` and implements the required methods
3. When running the evaluation, specify your agent with:

```python
from swebench.harness.run_evaluation_agent_modal import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, model_name=None):
        super().__init__(model_name=model_name)
        # Your initialization code here
        
    def solve_task(self, task_instance, workspace_dir, agent_log_dir):
        # Your implementation here
        return True  # Return True if you believe the task is solved
```

## Agent Implementations

The available agent implementations include:

- `DefaultAgent`: A basic agent template that shows how to implement the interface but does not actually solve tasks
- `LLMBasedAgent`: A template for implementing an agent based on an LLM API
- `FirebenderAgent`: An advanced agent implementation that uses a more sophistical architecture

## Running an Agent

To run an agent, use the following commands:

```bash
# Direct execution
AGENT_MODULE_PATH=swebench.agents.my_agent AGENT_CLASS_NAME=MyAgent \
  python -m swebench.harness.run_evaluation_agent \
  --model_name "my-model-name" \
  --output_log_dir ./agent_logs \
  --dataset_name ./datasets/some-dataset \
  --instance_id some-instance-id
  
# Using the provided wrapper script
./run_agent.sh \
  --agent="swebench.agents.my_agent.MyAgent" \
  --model="my-model-name" \
  --dataset=./datasets/some-dataset \
  --instance=some-instance-id
```

## Task Instance Format

The `task_instance` parameter contains the following key information:

- `instance_id`: Unique identifier for the task
- `repo`: GitHub repository path (owner/repo)
- `version`: Version/commit of the repository
- `title`: Issue title
- `problem`: Problem description
- `FAIL_TO_PASS`: List of tests that should be fixed (failing tests)
- `PASS_TO_PASS`: List of tests that should remain passing
- `test_patch`: Patch to apply to set up the test environment

## Logging and Reporting

- Use the `agent_log_dir` parameter to store logs, conversation history, etc.
- Implementation of `get_patch()` allows the evaluation framework to record the changes your agent made

## Default Agent

The `default_agent.py` provides a minimal implementation that you can use as a reference. 