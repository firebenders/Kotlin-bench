import os
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import time

from swebench.harness.run_evaluation_agent_modal import BaseAgent

class LLMBasedAgent(BaseAgent):
    """
    Template for implementing an LLM-based agent.
    This is just a scaffold - you need to implement the API calls.
    """
    
    def __init__(
        self,
        model_name: str = "GPT_4O",
        env_prompt_file: Optional[str] = None,
        log_dir: str = "/tmp/llm_agents",
        verbose: bool = False,
        max_iterations: int = 30
    ):
        """
        Initialize the agent.
        
        Args:
            model_name: Name of the model being used
            env_prompt_file: Path to environment prompt file
            log_dir: Directory to store logs
            verbose: Whether to print verbose logs
            max_iterations: Maximum number of iterations
        """
        super().__init__(model_name, env_prompt_file, log_dir, verbose, max_iterations)
        self.conversation_history = []
        self.changes_made = {}  # Maps filename to list of changes
        self.logger = self._setup_logger()
        self.agent_log_dir = None
    
    def solve_task(self, instance: Dict[str, Any], workspace_dir: Optional[str] = None) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Solve a single task instance using the agent.
        
        Args:
            instance: The task instance to solve
            workspace_dir: Directory containing the workspace files
            
        Returns:
            Tuple containing (success, conversation_history)
        """
        try:
            # Set up agent log directory
            instance_id = instance.get("instance_id", "unknown")
            self.agent_log_dir = os.path.join(self.log_dir, instance_id)
            os.makedirs(self.agent_log_dir, exist_ok=True)
            
            # Configure logging
            self._configure_file_handler(self.agent_log_dir)
            
            # Log task details
            self._log_task_details(instance, self.agent_log_dir)
            
            # Apply test patch to set up the environment
            self._apply_test_patch(instance, workspace_dir, self.agent_log_dir)
            
            # Gather information about the task
            task_info = self._gather_task_information(instance, workspace_dir)
            
            # Run initial analysis to understand the problem
            problem_understanding = self._analyze_problem(task_info, workspace_dir, self.agent_log_dir)
            
            # Find and analyze failing tests
            failing_tests_info = self._analyze_failing_tests(instance, workspace_dir, self.agent_log_dir)
            
            # Implement the solution
            solution_successful = self._implement_solution(
                instance,
                problem_understanding,
                failing_tests_info,
                workspace_dir,
                self.agent_log_dir
            )
            
            # Save the conversation history
            self._save_conversation_history(self.agent_log_dir)
            
            # Generate patch for reporting
            self._generate_patch_file(workspace_dir, self.agent_log_dir)
            
            # Return success status and conversation history
            return solution_successful, self.conversation_history
            
        except Exception as e:
            self.logger.error(f"Agent execution failed: {str(e)}", exc_info=True)
            if hasattr(self, '_log_conversation'):
                self._log_conversation("ERROR", f"Agent execution failed: {str(e)}", self.agent_log_dir or self.log_dir)
            try:
                if self.agent_log_dir:
                    self._save_conversation_history(self.agent_log_dir)
            except:
                pass
            return False, self.conversation_history or []
    
    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the agent."""
        logger = logging.getLogger(f"llm_agent_{self.model_name}")
        logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        return logger
    
    def _configure_file_handler(self, log_dir: str) -> None:
        """Add file handler to logger."""
        log_file = os.path.join(log_dir, "agent.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def _log_task_details(self, task_instance: Dict[str, Any], log_dir: str) -> None:
        """Log task details to file."""
        task_log_path = os.path.join(log_dir, "task_details.json")
        with open(task_log_path, "w") as f:
            json.dump(task_instance, f, indent=2)
        
        self.logger.info(f"Processing task: {task_instance.get('instance_id')}")
        self.logger.info(f"Title: {task_instance.get('title', 'N/A')}")
    
    def _apply_test_patch(self, task_instance: Dict[str, Any], workspace_dir: str, log_dir: str) -> bool:
        """Apply test patch to set up the environment."""
        test_patch = task_instance.get("test_patch", "")
        if not test_patch:
            self.logger.info("No test patch provided")
            return False
        
        # Save test patch to file
        patch_path = os.path.join(log_dir, "test_patch.diff")
        with open(patch_path, "w") as f:
            f.write(test_patch)
        
        # Apply patch
        try:
            self.logger.info("Applying test patch")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.diff') as tmp:
                tmp.write(test_patch)
                tmp.flush()
                
                # Change to workspace directory
                cwd = os.getcwd()
                os.chdir(workspace_dir)
                
                # Apply patch
                result = subprocess.run(
                    ["git", "apply", "--whitespace=fix", tmp.name],
                    capture_output=True,
                    text=True
                )
                
                # Return to original directory
                os.chdir(cwd)
                
                if result.returncode != 0:
                    self.logger.error(f"Failed to apply test patch: {result.stderr}")
                    return False
                
                self.logger.info("Test patch applied successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Error applying test patch: {str(e)}")
            return False
    
    def _gather_task_information(self, task_instance: Dict[str, Any], workspace_dir: str) -> Dict[str, Any]:
        """Gather information about the task."""
        self.logger.info("Gathering task information")
        
        # Extract key information from task instance
        task_info = {
            "instance_id": task_instance.get("instance_id", "unknown"),
            "repo": task_instance.get("repo", "unknown"),
            "title": task_instance.get("title", ""),
            "problem": task_instance.get("problem", ""),
            "failing_tests": task_instance.get("FAIL_TO_PASS", []),
            "passing_tests": task_instance.get("PASS_TO_PASS", [])
        }
        
        # You might want to add repository structure information here
        # For example, listing key directories, build files, etc.
        
        return task_info
    
    def _analyze_problem(self, task_info: Dict[str, Any], workspace_dir: str, log_dir: str) -> Dict[str, Any]:
        """
        Analyze the problem using an LLM.
        This method should be customized based on your LLM integration.
        """
        self.logger.info("Analyzing problem")
        
        # Create a prompt for the LLM to analyze the problem
        prompt = f"""
        I am working on a Kotlin/Android issue with the following details:
        
        Title: {task_info['title']}
        
        Problem description:
        {task_info['problem']}
        
        Please analyze this problem and help me understand:
        1. What is the root cause of the issue?
        2. Which parts of the codebase should I focus on?
        3. What's a potential approach to solving this issue?
        """
        
        # Generate response from LLM
        analysis = self._generate_llm_response("SYSTEM", prompt, log_dir)
        
        # Log the analysis
        self._log_conversation("ANALYSIS", analysis, log_dir)
        
        return {
            "analysis": analysis,
            "prompt": prompt
        }
    
    def _analyze_failing_tests(self, task_instance: Dict[str, Any], workspace_dir: str, log_dir: str) -> Dict[str, Any]:
        """
        Analyze failing tests to understand what needs to be fixed.
        """
        self.logger.info("Analyzing failing tests")
        
        failing_tests = task_instance.get("FAIL_TO_PASS", [])
        if not failing_tests:
            self.logger.info("No failing tests to analyze")
            return {"tests": []}
            
        test_info = []
        
        # For each failing test, try to find and analyze the test file
        for test_name in failing_tests:
            test_info.append({
                "test_name": test_name,
                # In a real implementation, you would locate and analyze the test file
                # For example, parse the test file, extract assertions, etc.
            })
            
        # In a real implementation, you might run the tests to collect error messages
        
        return {
            "tests": test_info
        }
    
    def _implement_solution(
        self, 
        task_instance: Dict[str, Any],
        problem_understanding: Dict[str, Any], 
        failing_tests_info: Dict[str, Any],
        workspace_dir: str, 
        log_dir: str
    ) -> bool:
        """
        Implement a solution for the problem.
        """
        self.logger.info("Implementing solution")
        
        # This is where you would use your LLM to generate a solution
        # The implementation depends on your specific LLM integration
        
        # Example implementation steps:
        # 1. Identify files to modify
        # 2. Generate changes for each file
        # 3. Apply the changes
        # 4. Verify the changes
        
        # Placeholder implementation - would be replaced with actual LLM-based implementation
        self._log_conversation(
            "SOLUTION", 
            "This is a placeholder solution. Implement your LLM-based solution here.", 
            log_dir
        )
        
        # Return True if you believe the solution is successful
        return False
    
    def _generate_llm_response(self, role: str, prompt: str, log_dir: str) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            role: Role of the message sender
            prompt: Prompt to send to the LLM
            log_dir: Directory to save logs
            
        Returns:
            str: LLM response
        """
        # This is a placeholder implementation
        # You should replace this with your actual LLM implementation
        # For example, you might use OpenAI API, Anthropic API, or a local model
        
        self._log_conversation(role, prompt, log_dir)
        
        # Placeholder response
        mock_response = f"""
        I've analyzed the problem:
        
        1. Root cause: This is a placeholder analysis.
        2. Focus areas: You should look at the relevant Kotlin/Android files.
        3. Approach: Implement a solution that addresses the failing tests.
        
        Note: This is a placeholder response. Implement your LLM integration here.
        """
        
        # Log the response
        self._log_conversation("ASSISTANT", mock_response, log_dir)
        
        return mock_response
    
    def _log_conversation(self, role: str, message: str, log_dir: str) -> None:
        """
        Log a conversation message.
        
        Args:
            role: Role of the message sender (SYSTEM, AGENT, ASSISTANT, etc.)
            message: Content of the message
            log_dir: Directory to save logs
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "role": role,
            "message": message
        }
        self.conversation_history.append(entry)
        
        # Also log to logger
        self.logger.debug(f"[{role}] {message[:100]}..." if len(message) > 100 else f"[{role}] {message}")
    
    def _save_conversation_history(self, log_dir: str) -> None:
        """
        Save the full conversation history to a file.
        
        Args:
            log_dir: Directory to save logs
        """
        history_path = os.path.join(log_dir, "conversation_history.json")
        with open(history_path, "w") as f:
            json.dump(self.conversation_history, f, indent=2)
    
    def _generate_patch_file(self, workspace_dir: str, log_dir: str) -> str:
        """
        Generate a patch file of all changes made.
        
        Args:
            workspace_dir: Directory containing the repository code
            log_dir: Directory to save logs
            
        Returns:
            str: Path to the generated patch file
        """
        patch_path = os.path.join(log_dir, "solution.diff")
        
        try:
            # Change to workspace directory
            cwd = os.getcwd()
            os.chdir(workspace_dir)
            
            # Generate patch using git
            with open(patch_path, "w") as f:
                result = subprocess.run(
                    ["git", "diff"],
                    capture_output=True,
                    text=True
                )
                f.write(result.stdout)
            
            # Return to original directory
            os.chdir(cwd)
            
            self.logger.info(f"Generated patch file: {patch_path}")
            return patch_path
            
        except Exception as e:
            self.logger.error(f"Error generating patch file: {str(e)}")
            return ""
        
    def get_patch(self) -> str:
        """
        Get a unified diff of changes made by the agent.
        
        Returns:
            str: Unified diff of changes
        """
        # In a real implementation, you would return the patch content
        # This could be from a git diff, or by tracking file changes manually
        try:
            with tempfile.NamedTemporaryFile(mode='r') as tmp:
                # Run git diff and capture output
                subprocess.run(
                    ["git", "diff"],
                    stdout=tmp,
                    check=True
                )
                tmp.seek(0)
                return tmp.read()
        except Exception as e:
            self.logger.error(f"Error getting patch: {str(e)}")
            return "" 