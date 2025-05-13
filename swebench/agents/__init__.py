"""
Agent implementations for SWE-bench tasks.

This module contains implementations for various agents that can solve SWE-bench tasks.
"""

from swebench.harness.run_evaluation_agent_modal import BaseAgent
try:
    from swebench.agents.default_agent import DefaultAgent
    from swebench.agents.llm_agent_template import LLMBasedAgent
    try:
        from swebench.agents.firebender_agent import FirebenderAgent
        __all__ = ['BaseAgent', 'DefaultAgent', 'LLMBasedAgent', 'FirebenderAgent']
    except ImportError:
        # FirebenderAgent may not be available
        __all__ = ['BaseAgent', 'DefaultAgent', 'LLMBasedAgent']
except ImportError:
    __all__ = ['BaseAgent'] 