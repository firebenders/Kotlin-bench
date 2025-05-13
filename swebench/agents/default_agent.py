from typing import Dict, Any, List, Optional, Tuple
import os
import json
import logging
import subprocess

from swebench.harness.run_evaluation_agent_modal import BaseAgent

class DefaultAgent(BaseAgent):
    """
    Default implementation of the BaseAgent interface.
    This implementation does nothing and always returns False.
    """
    
    def __init__(self, model_name=None, env_prompt_file=None, log_dir="/tmp/agents", verbose=False, max_iterations=30):
        """Initialize the default agent."""
        super().__init__(model_name=model_name, env_prompt_file=env_prompt_file, 
                        log_dir=log_dir, verbose=verbose, max_iterations=max_iterations)
        self.logger = logging.getLogger("default_agent")
    
    def solve_task(self, instance: Dict[str, Any], workspace_dir: Optional[str] = None) -> Tuple[bool, List[Dict[str, Any]]]:
        """Stub implementation that does nothing and returns False."""
        self.logger.info("DefaultAgent does nothing and returns False")
        # Return success status (False) and empty conversation history
        return False, []
        