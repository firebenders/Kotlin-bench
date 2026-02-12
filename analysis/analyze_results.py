#!/usr/bin/env python3
"""
Kotlin-bench Agent Analysis Report Generator

Comprehensive analytics for benchmark evaluation including:
- Core success metrics with rankings
- Timing analysis with correlations
- Task categorization (easy/medium/hard)
- Tool usage analysis with IntelliJ semantic tools breakdown
- Linter tool analysis (productive vs empty calls)
- Conversation metrics (messages, turns, estimated tokens)
- Code change metrics (lines added/removed, files changed)
- Cost analysis with model-specific pricing
"""

import json
import os
import re
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple
import statistics
from itertools import combinations
from datetime import datetime


# Model display names and pricing (per 1M tokens)
# cached_input_price is for prompt caching (cache hits & refreshes)
MODEL_CONFIG = {
    "claude-opus-4-5": {
        "display_name": "Opus 4.5",
        "input_price": 5.00,
        "cached_input_price": 0.50,  # Cache hits & refreshes
        "output_price": 25.00,
    },
    "claude-opus-4-6": {
        "display_name": "Opus 4.6",
        "input_price": 5.00,
        "cached_input_price": 0.50,  # Cache hits & refreshes
        "output_price": 25.00,
    },
    "claude-sonnet-4-20250514": {
        "display_name": "Sonnet 4",
        "input_price": 3.00,
        "cached_input_price": 0.30,  # Cache hits & refreshes
        "output_price": 15.00,
    },
    "claude-sonnet-4-5-20250929": {
        "display_name": "Sonnet 4.5",
        "input_price": 3.00,
        "cached_input_price": 0.30,  # Cache hits & refreshes
        "output_price": 15.00,
    },
    "gemini-3-flash-preview": {
        "display_name": "Gemini Flash 3",
        "input_price": 0.50,
        "cached_input_price": 0.05,  # Context caching price
        "output_price": 3.00,
    },
    "gemini-3-pro-preview": {
        "display_name": "Gemini Pro 3",
        "input_price": 2.00,
        "cached_input_price": 0.20,  # Context caching price
        "output_price": 12.00,
    },
    "gpt-5.2": {
        "display_name": "GPT-5.2",
        "input_price": 1.75,
        "cached_input_price": 0.175,  # Cached input
        "output_price": 14.00,
    },
    "gpt-5.2-codex": {
        "display_name": "GPT-5.2-Codex",
        "input_price": 1.75,
        "cached_input_price": 0.175,  # Cached input
        "output_price": 14.00,
    },
    "gpt-5.1-codex": {
        "display_name": "GPT-5.1-Codex",
        "input_price": 1.25,
        "cached_input_price": 0.125,  # Cached input
        "output_price": 10.00,
    },
    "gpt-4.1": {
        "display_name": "GPT-4.1",
        "input_price": 2.50,
        "cached_input_price": 0.25,  # Cached input
        "output_price": 10.00,
    },
    "zai-glm-4.7": {
        "display_name": "GLM-4.7",
        "input_price": 0.60,
        "cached_input_price": 0.30,  # Cached input
        "output_price": 2.20,
    },
    "zai-glm-4.7-fp8": {
        "display_name": "GLM-4.7-FP8",
        "input_price": 0.60,
        "cached_input_price": 0.30,  # Cached input
        "output_price": 2.20,
    },
}

# IntelliJ-specific semantic tools
INTELLIJ_TOOLS = {
    "go_to_definition": "Navigate to symbol definitions",
    "find_usages": "Find all usages of a symbol",
    "rename_symbol": "Rename symbols across project",
    "delete_symbol": "Delete symbols from codebase",
    "read_lints": "Read IDE diagnostics/linter errors",
}


def short_name(model: str) -> str:
    """Get short display name for model"""
    return MODEL_CONFIG.get(model, {}).get("display_name", model[:15])


def get_pricing(model: str) -> Tuple[float, float, float]:
    """Get input/cached_input/output pricing for model (per 1M tokens)"""
    config = MODEL_CONFIG.get(model, {"input_price": 1.0, "cached_input_price": 0.25, "output_price": 5.0})
    return config["input_price"], config.get("cached_input_price", config["input_price"] * 0.25), config["output_price"]


@dataclass
class AgentMetrics:
    """Metrics extracted from an agent run"""
    model: str
    instance_id: str
    test_passed: bool
    test_error: Optional[str] = None
    test_duration_seconds: float = 0.0
    
    # Agent metrics
    agent_duration_ms: int = 0
    num_messages: int = 0
    num_tool_calls: int = 0
    num_assistant_turns: int = 0
    tools_used: dict = field(default_factory=dict)
    
    # Patch metrics
    patch_lines_added: int = 0
    patch_lines_removed: int = 0
    patch_files_changed: int = 0
    
    # Error patterns
    agent_error: Optional[str] = None
    agent_success: bool = True
    
    # Conversation metrics
    total_input_chars: int = 0
    total_output_chars: int = 0
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    estimated_cached_input_tokens: int = 0  # Tokens served from cache
    estimated_uncached_input_tokens: int = 0  # Tokens NOT from cache
    
    # Linter analysis
    read_lints_calls: int = 0
    read_lints_empty: int = 0  # "No linter errors"
    read_lints_with_errors: int = 0  # Found actual errors
    
    # Cost estimate
    estimated_cost_usd: float = 0.0


def extract_text_from_content(content) -> str:
    """Extract text from various content formats (string, list of blocks, etc.)"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Content is a list of blocks (thinking, text, tool_use, etc.)
        texts = []
        for block in content:
            if isinstance(block, dict):
                # Handle text blocks
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
                # Handle thinking blocks (also output)
                elif block.get("type") == "thinking":
                    texts.append(block.get("thinking", ""))
            elif isinstance(block, str):
                texts.append(block)
        return " ".join(texts)
    return ""


def parse_agent_log(log_path: Path) -> dict:
    """Parse agent log and extract metrics"""
    metrics = {
        "duration_ms": 0,
        "num_messages": 0,
        "num_tool_calls": 0,
        "num_assistant_turns": 0,
        "tools_used": defaultdict(int),
        "error": None,
        "success": True,
        "total_input_chars": 0,
        "total_output_chars": 0,
        "read_lints_calls": 0,
        "read_lints_empty": 0,
        "read_lints_with_errors": 0,
    }
    
    try:
        with open(log_path, 'r') as f:
            data = json.load(f)
        
        metrics["duration_ms"] = data.get("total_duration_ms", 0)
        metrics["success"] = data.get("success", True)
        metrics["error"] = data.get("error")
        
        conversation = data.get("conversation_history", [])
        metrics["num_messages"] = len(conversation)
        
        for msg in conversation:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                # User content - count as input
                text = extract_text_from_content(content)
                metrics["total_input_chars"] += len(text)
            
            elif role == "assistant":
                metrics["num_assistant_turns"] += 1
                # Assistant content - count as output (includes thinking and text)
                text = extract_text_from_content(content)
                metrics["total_output_chars"] += len(text)
                
                # Also count tool call arguments as output
                tool_calls = msg.get("tool_calls", [])
                metrics["num_tool_calls"] += len(tool_calls)
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "unknown")
                    metrics["tools_used"][tool_name] += 1
                    # Count tool arguments as output
                    args = func.get("arguments", "")
                    if isinstance(args, str):
                        metrics["total_output_chars"] += len(args)
            
            elif role == "tool":
                # Tool result - count as input
                tool_content = msg.get("content", "")
                if isinstance(tool_content, str):
                    metrics["total_input_chars"] += len(tool_content)
                    
                    # Analyze read_lints results
                    tool_name = msg.get("name", "")
                    if tool_name == "read_lints":
                        metrics["read_lints_calls"] += 1
                        if "No linter errors" in tool_content:
                            metrics["read_lints_empty"] += 1
                        elif "<linter_errors>" in tool_content:
                            metrics["read_lints_with_errors"] += 1
                        
    except Exception as e:
        metrics["error"] = str(e)
        metrics["success"] = False
    
    return metrics


def parse_patch(patch_path: Path) -> dict:
    """Parse patch file and extract metrics"""
    metrics = {
        "lines_added": 0,
        "lines_removed": 0,
        "files_changed": 0,
    }
    
    try:
        if patch_path.exists():
            content = patch_path.read_text()
            lines = content.split('\n')
            
            files = set()
            for line in lines:
                if line.startswith('+') and not line.startswith('+++'):
                    metrics["lines_added"] += 1
                elif line.startswith('-') and not line.startswith('---'):
                    metrics["lines_removed"] += 1
                elif line.startswith('diff --git'):
                    parts = line.split(' ')
                    if len(parts) >= 3:
                        files.add(parts[2])
            
            metrics["files_changed"] = len(files)
    except Exception:
        pass
    
    return metrics


def parse_test_result(result_path: Path) -> dict:
    """Parse test result JSON"""
    metrics = {
        "passed": False,
        "error": None,
        "duration_seconds": 0.0,
    }
    
    try:
        if result_path.exists():
            with open(result_path, 'r') as f:
                data = json.load(f)
            metrics["passed"] = data.get("passed", False)
            metrics["error"] = data.get("error")
            metrics["duration_seconds"] = data.get("duration_seconds", 0.0)
    except Exception as e:
        metrics["error"] = str(e)
    
    return metrics


def estimate_cost(model: str, uncached_input_tokens: int, cached_input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD based on model pricing with cache support"""
    input_price, cached_input_price, output_price = get_pricing(model)
    uncached_input_cost = (uncached_input_tokens / 1_000_000) * input_price
    cached_input_cost = (cached_input_tokens / 1_000_000) * cached_input_price
    output_cost = (output_tokens / 1_000_000) * output_price
    return uncached_input_cost + cached_input_cost + output_cost


def estimate_cached_tokens(num_assistant_turns: int, total_input_tokens: int) -> Tuple[int, int]:
    """
    Estimate how many input tokens are cached vs uncached.
    
    In multi-turn conversations with prompt caching:
    - Turn 1: All tokens are uncached (system prompt, initial user message)
    - Turn 2+: Previous context is cached, only new content is uncached
    
    We estimate that on average:
    - The first turn's content (~system prompt + task) is about 15-20% of total input
    - Subsequent turns reuse most of the prior context from cache
    - Roughly 80-85% of total input tokens hit the cache after first turn
    
    Formula: cache_rate = min(0.85, max(0, (turns - 1) / turns * 0.9))
    """
    if num_assistant_turns <= 1:
        # Single turn conversation - no caching benefit
        return 0, total_input_tokens
    
    # More turns = higher cache hit rate, capped at 85%
    # This reflects that each subsequent turn reuses prior context
    cache_rate = min(0.85, (num_assistant_turns - 1) / num_assistant_turns * 0.90)
    
    cached_tokens = int(total_input_tokens * cache_rate)
    uncached_tokens = total_input_tokens - cached_tokens
    
    return cached_tokens, uncached_tokens


def load_all_results(data_dir: Path) -> list[AgentMetrics]:
    """Load all agent results from the data directory"""
    results = []
    
    for instance_dir in data_dir.iterdir():
        if not instance_dir.is_dir():
            continue
        
        instance_id = instance_dir.name
        
        for model_dir in instance_dir.iterdir():
            if not model_dir.is_dir():
                continue
            
            model = model_dir.name
            settings_dir = model_dir / "ij1_oracle1"
            
            if not settings_dir.exists():
                continue
            
            # Parse test result
            test_result = parse_test_result(settings_dir / "test_result.json")
            
            # Parse agent log
            agent_log = parse_agent_log(settings_dir / "agent_log.json")
            
            # Parse patch
            patch = parse_patch(settings_dir / "agent_patch.diff")
            
            # Estimate tokens (chars / 4 is a reasonable approximation)
            estimated_input_tokens = agent_log["total_input_chars"] // 4
            estimated_output_tokens = agent_log["total_output_chars"] // 4
            
            # Estimate cached vs uncached tokens based on conversation turns
            num_turns = agent_log["num_assistant_turns"]
            cached_tokens, uncached_tokens = estimate_cached_tokens(num_turns, estimated_input_tokens)

            # Calculate cost with cache pricing
            cost = estimate_cost(model, uncached_tokens, cached_tokens, estimated_output_tokens)
            
            metrics = AgentMetrics(
                model=model,
                instance_id=instance_id,
                test_passed=test_result["passed"],
                test_error=test_result["error"],
                test_duration_seconds=test_result["duration_seconds"],
                agent_duration_ms=agent_log["duration_ms"],
                num_messages=agent_log["num_messages"],
                num_tool_calls=agent_log["num_tool_calls"],
                num_assistant_turns=agent_log["num_assistant_turns"],
                tools_used=dict(agent_log["tools_used"]),
                patch_lines_added=patch["lines_added"],
                patch_lines_removed=patch["lines_removed"],
                patch_files_changed=patch["files_changed"],
                agent_error=agent_log["error"],
                agent_success=agent_log["success"],
                total_input_chars=agent_log["total_input_chars"],
                total_output_chars=agent_log["total_output_chars"],
                estimated_input_tokens=estimated_input_tokens,
                estimated_output_tokens=estimated_output_tokens,
                estimated_cached_input_tokens=cached_tokens,
                estimated_uncached_input_tokens=uncached_tokens,
                read_lints_calls=agent_log["read_lints_calls"],
                read_lints_empty=agent_log["read_lints_empty"],
                read_lints_with_errors=agent_log["read_lints_with_errors"],
                estimated_cost_usd=cost,
            )
            results.append(metrics)
    
    return results


def get_repo_from_instance(instance_id: str) -> str:
    """Extract repository name from instance ID"""
    parts = instance_id.split('__')
    if len(parts) >= 2:
        return parts[0] + '/' + parts[1].rsplit('-', 1)[0]
    return instance_id


def generate_report(results: list[AgentMetrics]) -> dict:
    """Generate comprehensive analysis report"""
    report = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_results": len(results),
            "version": "1.0",
        }
    }
    
    # Group data
    by_model = defaultdict(list)
    by_repo = defaultdict(list)
    by_instance = defaultdict(list)
    
    for r in results:
        by_model[r.model].append(r)
        by_repo[get_repo_from_instance(r.instance_id)].append(r)
        by_instance[r.instance_id].append(r)
    
    models = sorted(by_model.keys())
    repos = sorted(by_repo.keys())
    instances = sorted(by_instance.keys())
    
    # ===== 1. Core Success Metrics =====
    report["core_metrics"] = {}
    
    # Pass rate per model (ranked)
    model_pass_rates = {}
    for model in models:
        model_results = by_model[model]
        passed = sum(1 for r in model_results if r.test_passed)
        total = len(model_results)
        model_pass_rates[model] = {
            "passed": passed,
            "total": total,
            "pass_rate": passed / total if total > 0 else 0,
            "display_name": short_name(model),
        }
    
    # Sort by pass rate
    ranked_models = sorted(model_pass_rates.items(), key=lambda x: -x[1]["pass_rate"])
    report["core_metrics"]["model_rankings"] = [
        {"rank": i+1, "model": m, **stats} 
        for i, (m, stats) in enumerate(ranked_models)
    ]
    
    # Pass rate per repository
    repo_pass_rates = {}
    for repo in repos:
        repo_results = by_repo[repo]
        passed = sum(1 for r in repo_results if r.test_passed)
        total = len(repo_results)
        repo_pass_rates[repo] = {
            "passed": passed,
            "total": total,
            "pass_rate": passed / total if total > 0 else 0,
            "num_instances": len(set(r.instance_id for r in repo_results)),
        }
    report["core_metrics"]["repo_pass_rates"] = repo_pass_rates
    
    # Model x Repo matrix
    model_repo_matrix = {}
    for model in models:
        model_repo_matrix[model] = {}
        for repo in repos:
            relevant = [r for r in results if r.model == model and get_repo_from_instance(r.instance_id) == repo]
            passed = sum(1 for r in relevant if r.test_passed)
            total = len(relevant)
            model_repo_matrix[model][repo] = {
                "passed": passed,
                "total": total,
                "pass_rate": passed / total if total > 0 else 0,
            }
    report["core_metrics"]["model_repo_matrix"] = model_repo_matrix
    
    # Task difficulty distribution
    task_difficulty = {}
    for instance_id in instances:
        instance_results = by_instance[instance_id]
        passed_models = [r.model for r in instance_results if r.test_passed]
        total_models = len(instance_results)
        task_difficulty[instance_id] = {
            "num_models_passed": len(passed_models),
            "total_models": total_models,
            "passed_by": passed_models,
        }
    
    easy_tasks = [t for t, d in task_difficulty.items() if d["num_models_passed"] == d["total_models"] and d["total_models"] > 0]
    hard_tasks = [t for t, d in task_difficulty.items() if d["num_models_passed"] == 0]
    medium_tasks = [t for t in instances if t not in easy_tasks and t not in hard_tasks]
    
    report["core_metrics"]["task_difficulty"] = {
        "easy_count": len(easy_tasks),
        "medium_count": len(medium_tasks),
        "hard_count": len(hard_tasks),
        "easy_tasks": easy_tasks,
        "medium_tasks": medium_tasks,
        "hard_tasks": hard_tasks,
        "task_details": task_difficulty,
    }
    
    # ===== 2. Timing Analysis =====
    report["timing_analysis"] = {}
    
    timing_by_model = {}
    for model in models:
        model_results = by_model[model]
        durations = [r.agent_duration_ms for r in model_results if r.agent_duration_ms > 0]
        passed_durations = [r.agent_duration_ms for r in model_results if r.test_passed and r.agent_duration_ms > 0]
        failed_durations = [r.agent_duration_ms for r in model_results if not r.test_passed and r.agent_duration_ms > 0]
        
        timing_by_model[model] = {
            "avg_ms": statistics.mean(durations) if durations else 0,
            "min_ms": min(durations) if durations else 0,
            "max_ms": max(durations) if durations else 0,
            "median_ms": statistics.median(durations) if durations else 0,
            "avg_passed_ms": statistics.mean(passed_durations) if passed_durations else 0,
            "avg_failed_ms": statistics.mean(failed_durations) if failed_durations else 0,
            "faster_when_passing": (statistics.mean(passed_durations) if passed_durations else float('inf')) < (statistics.mean(failed_durations) if failed_durations else float('inf')),
        }
    
    # Speed rankings
    speed_rankings = sorted(timing_by_model.items(), key=lambda x: x[1]["avg_ms"])
    report["timing_analysis"]["by_model"] = timing_by_model
    report["timing_analysis"]["speed_rankings"] = [
        {"rank": i+1, "model": m, "avg_duration_sec": stats["avg_ms"]/1000} 
        for i, (m, stats) in enumerate(speed_rankings)
    ]
    
    # ===== 3. Task Categorization =====
    report["task_categorization"] = {
        "easy_tasks": easy_tasks,
        "hard_tasks": hard_tasks,
        "high_variance_tasks": [],
        "unique_solves": defaultdict(list),
    }
    
    # High variance tasks (some pass, some fail)
    high_variance = []
    for instance_id, details in task_difficulty.items():
        if 0 < details["num_models_passed"] < details["total_models"]:
            variance_score = abs(details["num_models_passed"] - details["total_models"] / 2)
            high_variance.append({
                "instance_id": instance_id,
                "passed_count": details["num_models_passed"],
                "total": details["total_models"],
                "passed_by": details["passed_by"],
            })
    high_variance.sort(key=lambda x: x["passed_count"])
    report["task_categorization"]["high_variance_tasks"] = high_variance
    
    # Unique solves per model
    unique_solves = defaultdict(list)
    for instance_id in instances:
        instance_results = by_instance[instance_id]
        passed_models = [r.model for r in instance_results if r.test_passed]
        if len(passed_models) == 1:
            unique_solves[passed_models[0]].append(instance_id)
    report["task_categorization"]["unique_solves"] = dict(unique_solves)
    
    # ===== 4. Tool Usage Analysis =====
    report["tool_usage"] = {}
    
    # Tool call counts by model
    tool_counts_by_model = {}
    for model in models:
        model_results = by_model[model]
        combined_tools = defaultdict(int)
        for r in model_results:
            for tool, count in r.tools_used.items():
                combined_tools[tool] += count
        
        total_calls = sum(combined_tools.values())
        tool_counts_by_model[model] = {
            "total_tool_calls": total_calls,
            "avg_per_task": total_calls / len(model_results) if model_results else 0,
            "tools": dict(sorted(combined_tools.items(), key=lambda x: -x[1])),
        }
    report["tool_usage"]["by_model"] = tool_counts_by_model
    
    # Tool usage when passing vs failing
    tool_pass_fail = {}
    for model in models:
        passed = [r for r in by_model[model] if r.test_passed]
        failed = [r for r in by_model[model] if not r.test_passed]
        
        tool_pass_fail[model] = {
            "avg_tools_passed": statistics.mean([r.num_tool_calls for r in passed]) if passed else 0,
            "avg_tools_failed": statistics.mean([r.num_tool_calls for r in failed]) if failed else 0,
        }
    report["tool_usage"]["pass_fail_comparison"] = tool_pass_fail
    
    # IntelliJ semantic tools breakdown
    ij_tools_by_model = {}
    for model in models:
        model_results = by_model[model]
        ij_counts = {tool: 0 for tool in INTELLIJ_TOOLS.keys()}
        for r in model_results:
            for tool in INTELLIJ_TOOLS.keys():
                ij_counts[tool] += r.tools_used.get(tool, 0)
        
        ij_tools_by_model[model] = {
            "tools": ij_counts,
            "total": sum(ij_counts.values()),
        }
    report["tool_usage"]["intellij_tools"] = ij_tools_by_model
    
    # ===== 4b. Per-Task Tool Usage Analysis =====
    # Compare how different models use tools on the SAME task
    per_task_tool_analysis = {}
    
    for instance_id in instances:
        task_results = by_instance[instance_id]
        if len(task_results) < 2:
            continue
            
        passed_results = [r for r in task_results if r.test_passed]
        failed_results = [r for r in task_results if not r.test_passed]
        
        # Tool call distribution for this task
        tool_calls_by_model = {}
        tools_used_by_model = {}
        for r in task_results:
            tool_calls_by_model[r.model] = {
                "total_calls": r.num_tool_calls,
                "passed": r.test_passed,
                "tools": dict(r.tools_used),
            }
            tools_used_by_model[r.model] = r.tools_used
        
        # Calculate stats for this task
        all_tool_counts = [r.num_tool_calls for r in task_results]
        passed_tool_counts = [r.num_tool_calls for r in passed_results]
        failed_tool_counts = [r.num_tool_calls for r in failed_results]
        
        # Find tools that correlate with success on THIS task
        tools_in_passing = defaultdict(int)
        tools_in_failing = defaultdict(int)
        for r in passed_results:
            for tool, count in r.tools_used.items():
                tools_in_passing[tool] += count
        for r in failed_results:
            for tool, count in r.tools_used.items():
                tools_in_failing[tool] += count
        
        # Normalize by number of attempts
        if passed_results:
            tools_in_passing = {k: v / len(passed_results) for k, v in tools_in_passing.items()}
        if failed_results:
            tools_in_failing = {k: v / len(failed_results) for k, v in tools_in_failing.items()}
        
        # Find tools more used in passing vs failing
        tool_success_correlation = {}
        all_tools = set(tools_in_passing.keys()) | set(tools_in_failing.keys())
        for tool in all_tools:
            pass_avg = tools_in_passing.get(tool, 0)
            fail_avg = tools_in_failing.get(tool, 0)
            if pass_avg + fail_avg > 0:
                # Positive = more used when passing, negative = more used when failing
                correlation = (pass_avg - fail_avg) / (pass_avg + fail_avg + 0.01)
                tool_success_correlation[tool] = round(correlation, 3)
        
        per_task_tool_analysis[instance_id] = {
            "num_models": len(task_results),
            "num_passed": len(passed_results),
            "num_failed": len(failed_results),
            "tool_calls": {
                "min": min(all_tool_counts) if all_tool_counts else 0,
                "max": max(all_tool_counts) if all_tool_counts else 0,
                "avg": statistics.mean(all_tool_counts) if all_tool_counts else 0,
                "std_dev": statistics.stdev(all_tool_counts) if len(all_tool_counts) > 1 else 0,
                "avg_passed": statistics.mean(passed_tool_counts) if passed_tool_counts else None,
                "avg_failed": statistics.mean(failed_tool_counts) if failed_tool_counts else None,
            },
            "by_model": tool_calls_by_model,
            "tool_success_correlation": dict(sorted(tool_success_correlation.items(), key=lambda x: -x[1])),
        }
    
    report["tool_usage"]["per_task"] = per_task_tool_analysis
    
    # Aggregate insights across all tasks
    # Find tools that consistently correlate with success
    tool_correlation_aggregate = defaultdict(list)
    for task_id, task_data in per_task_tool_analysis.items():
        for tool, corr in task_data["tool_success_correlation"].items():
            tool_correlation_aggregate[tool].append(corr)
    
    tool_success_patterns = {}
    for tool, correlations in tool_correlation_aggregate.items():
        if len(correlations) >= 5:  # Only include tools used in at least 5 tasks
            avg_corr = statistics.mean(correlations)
            tool_success_patterns[tool] = {
                "avg_correlation": round(avg_corr, 3),
                "num_tasks": len(correlations),
                "positive_tasks": sum(1 for c in correlations if c > 0.1),
                "negative_tasks": sum(1 for c in correlations if c < -0.1),
                "interpretation": "helps success" if avg_corr > 0.05 else ("hurts success" if avg_corr < -0.05 else "neutral"),
            }
    
    report["tool_usage"]["tool_success_patterns"] = dict(sorted(tool_success_patterns.items(), key=lambda x: -x[1]["avg_correlation"]))
    
    # High variance tasks (where tool usage differs significantly between models)
    high_variance_tool_tasks = []
    for task_id, task_data in per_task_tool_analysis.items():
        if task_data["tool_calls"]["std_dev"] > 15:  # Significant variance
            high_variance_tool_tasks.append({
                "task": task_id,
                "std_dev": round(task_data["tool_calls"]["std_dev"], 1),
                "min": task_data["tool_calls"]["min"],
                "max": task_data["tool_calls"]["max"],
                "passed": task_data["num_passed"],
                "failed": task_data["num_failed"],
            })
    high_variance_tool_tasks.sort(key=lambda x: -x["std_dev"])
    report["tool_usage"]["high_variance_tasks"] = high_variance_tool_tasks[:20]
    
    # ===== 5. Linter Tool Analysis =====
    report["linter_analysis"] = {}
    
    linter_by_model = {}
    for model in models:
        model_results = by_model[model]
        total_calls = sum(r.read_lints_calls for r in model_results)
        empty_calls = sum(r.read_lints_empty for r in model_results)
        productive_calls = sum(r.read_lints_with_errors for r in model_results)
        
        # Correlation with success
        passed = [r for r in model_results if r.test_passed]
        failed = [r for r in model_results if not r.test_passed]
        
        linter_by_model[model] = {
            "total_calls": total_calls,
            "empty_calls": empty_calls,
            "productive_calls": productive_calls,
            "empty_rate": empty_calls / total_calls if total_calls > 0 else 0,
            "productive_rate": productive_calls / total_calls if total_calls > 0 else 0,
            "avg_calls_passed": statistics.mean([r.read_lints_calls for r in passed]) if passed else 0,
            "avg_calls_failed": statistics.mean([r.read_lints_calls for r in failed]) if failed else 0,
        }
    report["linter_analysis"]["by_model"] = linter_by_model
    
    # ===== 6. Conversation Metrics =====
    report["conversation_metrics"] = {}
    
    conv_by_model = {}
    for model in models:
        model_results = by_model[model]
        passed = [r for r in model_results if r.test_passed]
        failed = [r for r in model_results if not r.test_passed]
        
        conv_by_model[model] = {
            "avg_messages": statistics.mean([r.num_messages for r in model_results]) if model_results else 0,
            "avg_assistant_turns": statistics.mean([r.num_assistant_turns for r in model_results]) if model_results else 0,
            "avg_input_tokens": statistics.mean([r.estimated_input_tokens for r in model_results]) if model_results else 0,
            "avg_output_tokens": statistics.mean([r.estimated_output_tokens for r in model_results]) if model_results else 0,
            "total_input_tokens": sum(r.estimated_input_tokens for r in model_results),
            "total_output_tokens": sum(r.estimated_output_tokens for r in model_results),
            "avg_messages_passed": statistics.mean([r.num_messages for r in passed]) if passed else 0,
            "avg_messages_failed": statistics.mean([r.num_messages for r in failed]) if failed else 0,
        }
    report["conversation_metrics"]["by_model"] = conv_by_model
    
    # ===== 7. Code Change Metrics =====
    report["code_change_metrics"] = {}
    
    code_by_model = {}
    for model in models:
        model_results = by_model[model]
        passed = [r for r in model_results if r.test_passed]
        failed = [r for r in model_results if not r.test_passed]
        
        all_lines = [r.patch_lines_added + r.patch_lines_removed for r in model_results]
        passed_lines = [r.patch_lines_added + r.patch_lines_removed for r in passed]
        failed_lines = [r.patch_lines_added + r.patch_lines_removed for r in failed]
        
        code_by_model[model] = {
            "avg_lines_added": statistics.mean([r.patch_lines_added for r in model_results]) if model_results else 0,
            "avg_lines_removed": statistics.mean([r.patch_lines_removed for r in model_results]) if model_results else 0,
            "avg_lines_changed": statistics.mean(all_lines) if all_lines else 0,
            "avg_files_changed": statistics.mean([r.patch_files_changed for r in model_results]) if model_results else 0,
            "avg_lines_passed": statistics.mean(passed_lines) if passed_lines else 0,
            "avg_lines_failed": statistics.mean(failed_lines) if failed_lines else 0,
        }
    report["code_change_metrics"]["by_model"] = code_by_model
    
    # ===== 8. Cost Analysis =====
    # Cost calculation includes prompt caching - cached tokens are ~10-25% the price of uncached
    report["cost_analysis"] = {}
    
    cost_by_model = {}
    for model in models:
        model_results = by_model[model]
        passed = [r for r in model_results if r.test_passed]
        
        total_cost = sum(r.estimated_cost_usd for r in model_results)
        avg_cost = total_cost / len(model_results) if model_results else 0
        
        # Cost per success
        cost_per_success = total_cost / len(passed) if passed else float('inf')
        
        # Token breakdown
        total_input_tokens = sum(r.estimated_input_tokens for r in model_results)
        total_cached_tokens = sum(r.estimated_cached_input_tokens for r in model_results)
        total_uncached_tokens = sum(r.estimated_uncached_input_tokens for r in model_results)
        total_output_tokens = sum(r.estimated_output_tokens for r in model_results)
        
        # Cache hit rate
        cache_hit_rate = total_cached_tokens / total_input_tokens if total_input_tokens > 0 else 0
        
        input_price, cached_price, output_price = get_pricing(model)
        
        cost_by_model[model] = {
            "total_cost_usd": round(total_cost, 4),
            "avg_cost_per_task_usd": round(avg_cost, 4),
            "cost_per_success_usd": round(cost_per_success, 4) if cost_per_success != float('inf') else None,
            "total_input_tokens": total_input_tokens,
            "total_cached_input_tokens": total_cached_tokens,
            "total_uncached_input_tokens": total_uncached_tokens,
            "total_output_tokens": total_output_tokens,
            "cache_hit_rate": round(cache_hit_rate, 3),
            "pricing": {
                "input_per_1m": input_price,
                "cached_input_per_1m": cached_price,
                "output_per_1m": output_price,
            }
        }
    
    # Cost rankings (lowest cost per success)
    cost_rankings = sorted(
        [(m, c["cost_per_success_usd"]) for m, c in cost_by_model.items() if c["cost_per_success_usd"] is not None],
        key=lambda x: x[1]
    )
    
    report["cost_analysis"]["by_model"] = cost_by_model
    report["cost_analysis"]["cost_rankings"] = [
        {"rank": i+1, "model": m, "cost_per_success_usd": cost}
        for i, (m, cost) in enumerate(cost_rankings)
    ]
    
    # ===== Summary Statistics =====
    total_passed = sum(1 for r in results if r.test_passed)
    total_cost = sum(r.estimated_cost_usd for r in results)
    
    report["summary"] = {
        "total_tasks": len(instances),
        "total_models": len(models),
        "total_runs": len(results),
        "total_passed": total_passed,
        "overall_pass_rate": total_passed / len(results) if results else 0,
        "total_cost_usd": round(total_cost, 2),
        "best_model": ranked_models[0][0] if ranked_models else None,
        "best_pass_rate": ranked_models[0][1]["pass_rate"] if ranked_models else 0,
        "lowest_cost_per_success": cost_rankings[0][0] if cost_rankings else None,
    }
    
    return report


def generate_markdown_report(report: dict) -> str:
    """Generate human-readable markdown report"""
    lines = []
    
    lines.append("# Kotlin-bench Analysis Report\n")
    lines.append(f"*Generated: {report['metadata']['generated_at']}*\n")
    lines.append(f"*Total runs: {report['metadata']['total_results']}*\n")
    
    # Executive Summary
    lines.append("## Executive Summary\n")
    summary = report["summary"]
    lines.append(f"- **Total Tasks**: {summary['total_tasks']}")
    lines.append(f"- **Total Models**: {summary['total_models']}")
    lines.append(f"- **Total Runs**: {summary['total_runs']}")
    lines.append(f"- **Overall Pass Rate**: {summary['overall_pass_rate']:.1%} ({summary['total_passed']}/{summary['total_runs']})")
    lines.append(f"- **Total Estimated Cost**: ${summary['total_cost_usd']:.2f}")
    lines.append(f"- **Best Model**: {short_name(summary['best_model'])} ({summary['best_pass_rate']:.1%})")
    lines.append(f"- **Lowest Cost/Success**: {short_name(summary['lowest_cost_per_success'])}")
    lines.append("")
    
    # 1. Core Success Metrics
    lines.append("## 1. Core Success Metrics\n")
    
    lines.append("### Model Rankings by Pass Rate\n")
    lines.append("| Rank | Model | Passed | Total | Pass Rate |")
    lines.append("|------|-------|--------|-------|-----------|")
    for item in report["core_metrics"]["model_rankings"]:
        lines.append(f"| {item['rank']} | {item['display_name']} | {item['passed']} | {item['total']} | {item['pass_rate']:.1%} |")
    lines.append("")
    
    lines.append("### Pass Rate by Repository\n")
    lines.append("| Repository | Tasks | Passed | Total | Pass Rate |")
    lines.append("|------------|-------|--------|-------|-----------|")
    for repo, stats in sorted(report["core_metrics"]["repo_pass_rates"].items(), key=lambda x: -x[1]["pass_rate"]):
        lines.append(f"| {repo} | {stats['num_instances']} | {stats['passed']} | {stats['total']} | {stats['pass_rate']:.1%} |")
    lines.append("")
    
    lines.append("### Task Difficulty Distribution\n")
    diff = report["core_metrics"]["task_difficulty"]
    total_tasks = diff["easy_count"] + diff["medium_count"] + diff["hard_count"]
    lines.append(f"- **Easy** (all models passed): {diff['easy_count']} ({diff['easy_count']/total_tasks:.0%})")
    lines.append(f"- **Medium** (some models passed): {diff['medium_count']} ({diff['medium_count']/total_tasks:.0%})")
    lines.append(f"- **Hard** (no model passed): {diff['hard_count']} ({diff['hard_count']/total_tasks:.0%})")
    lines.append("")
    
    # 2. Timing Analysis
    lines.append("## 2. Timing Analysis\n")
    
    lines.append("### Speed Rankings\n")
    lines.append("| Rank | Model | Avg Duration |")
    lines.append("|------|-------|--------------|")
    for item in report["timing_analysis"]["speed_rankings"]:
        lines.append(f"| {item['rank']} | {short_name(item['model'])} | {item['avg_duration_sec']:.1f}s |")
    lines.append("")
    
    lines.append("### Duration by Outcome\n")
    lines.append("| Model | Avg (Pass) | Avg (Fail) | Faster When |")
    lines.append("|-------|------------|------------|-------------|")
    for model, stats in report["timing_analysis"]["by_model"].items():
        pass_sec = stats["avg_passed_ms"] / 1000
        fail_sec = stats["avg_failed_ms"] / 1000
        faster = "Passing" if stats["faster_when_passing"] else "Failing"
        lines.append(f"| {short_name(model)} | {pass_sec:.1f}s | {fail_sec:.1f}s | {faster} |")
    lines.append("")
    
    # 3. Task Categorization
    lines.append("## 3. Task Categorization\n")
    
    lines.append("### Unique Solves (Tasks only one model solved)\n")
    unique_solves = report["task_categorization"]["unique_solves"]
    if unique_solves:
        for model, tasks in sorted(unique_solves.items(), key=lambda x: -len(x[1])):
            lines.append(f"- **{short_name(model)}**: {len(tasks)} unique solves")
            for task in tasks[:3]:
                lines.append(f"  - `{task}`")
            if len(tasks) > 3:
                lines.append(f"  - ... and {len(tasks)-3} more")
    else:
        lines.append("No unique solves found.")
    lines.append("")
    
    lines.append("### High Variance Tasks (Some pass, some fail)\n")
    high_var = report["task_categorization"]["high_variance_tasks"][:10]
    if high_var:
        lines.append("| Task | Passed By | Pass Count |")
        lines.append("|------|-----------|------------|")
        for item in high_var:
            passed_by = ", ".join([short_name(m) for m in item["passed_by"][:3]])
            if len(item["passed_by"]) > 3:
                passed_by += "..."
            lines.append(f"| `{item['instance_id'][:50]}` | {passed_by} | {item['passed_count']}/{item['total']} |")
    lines.append("")
    
    # 4. Tool Usage Analysis
    lines.append("## 4. Tool Usage Analysis\n")
    
    lines.append("### Tool Calls by Model\n")
    lines.append("| Model | Total Calls | Avg/Task | Top Tools |")
    lines.append("|-------|-------------|----------|-----------|")
    for model, stats in report["tool_usage"]["by_model"].items():
        top_tools = list(stats["tools"].items())[:3]
        top_str = ", ".join([f"{t}:{c}" for t, c in top_tools])
        lines.append(f"| {short_name(model)} | {stats['total_tool_calls']} | {stats['avg_per_task']:.1f} | {top_str} |")
    lines.append("")
    
    lines.append("### IntelliJ Semantic Tools Usage\n")
    lines.append("| Model | read_lints | go_to_def | find_usages | rename | delete | Total |")
    lines.append("|-------|------------|-----------|-------------|--------|--------|-------|")
    for model, stats in report["tool_usage"]["intellij_tools"].items():
        t = stats["tools"]
        lines.append(f"| {short_name(model)} | {t.get('read_lints', 0)} | {t.get('go_to_definition', 0)} | {t.get('find_usages', 0)} | {t.get('rename_symbol', 0)} | {t.get('delete_symbol', 0)} | {stats['total']} |")
    lines.append("")
    
    # 4b. Per-Task Tool Analysis
    lines.append("### Tool-Success Correlation Patterns\n")
    lines.append("*Comparing avg tool usage between passing and failing attempts on the same task.*\n")
    lines.append("*Negative correlation = tool used MORE when failing (struggling models explore more)*\n")
    
    tool_patterns = report["tool_usage"].get("tool_success_patterns", {})
    if tool_patterns:
        lines.append("| Tool | Correlation | Tasks | Insight |")
        lines.append("|------|-------------|-------|---------|")
        for tool, stats in list(tool_patterns.items())[:12]:
            if stats['avg_correlation'] < -0.2:
                insight = "Overused when struggling"
            elif stats['avg_correlation'] < -0.05:
                insight = "Slightly more when failing"
            elif stats['avg_correlation'] > 0.05:
                insight = "More when succeeding"
            else:
                insight = "Similar usage"
            lines.append(f"| {tool} | {stats['avg_correlation']:+.3f} | {stats['num_tasks']} | {insight} |")
    lines.append("")
    
    lines.append("### High Tool-Variance Tasks\n")
    lines.append("*Tasks where models used very different numbers of tools*\n")
    
    high_var_tasks = report["tool_usage"].get("high_variance_tasks", [])
    if high_var_tasks:
        lines.append("| Task | Min Tools | Max Tools | Std Dev | Pass/Fail |")
        lines.append("|------|-----------|-----------|---------|-----------|")
        for item in high_var_tasks[:10]:
            task_short = item["task"][:40] + "..." if len(item["task"]) > 40 else item["task"]
            lines.append(f"| `{task_short}` | {item['min']} | {item['max']} | {item['std_dev']:.1f} | {item['passed']}/{item['passed']+item['failed']} |")
    lines.append("")
    
    # Show example per-task comparisons
    lines.append("### Example: Per-Task Tool Comparison\n")
    lines.append("*Detailed tool usage for select high-variance tasks*\n")
    
    per_task = report["tool_usage"].get("per_task", {})
    # Find interesting tasks (mixed success)
    interesting_tasks = []
    for task_id, data in per_task.items():
        if 1 <= data["num_passed"] <= data["num_models"] - 1:  # Mixed results
            if data["tool_calls"]["std_dev"] > 10:  # Significant variance
                interesting_tasks.append((task_id, data))
    
    interesting_tasks.sort(key=lambda x: -x[1]["tool_calls"]["std_dev"])
    
    for task_id, data in interesting_tasks[:3]:
        task_short = task_id[:50]
        lines.append(f"**{task_short}** ({data['num_passed']}/{data['num_models']} passed)\n")
        lines.append("| Model | Tools Used | Passed | Top Tools |")
        lines.append("|-------|------------|--------|-----------|")
        
        # Sort by passed (True first), then by tool count
        sorted_models = sorted(data["by_model"].items(), 
                              key=lambda x: (not x[1]["passed"], x[1]["total_calls"]))
        for model, model_data in sorted_models:
            passed_str = "Yes" if model_data["passed"] else "No"
            top_tools = sorted(model_data["tools"].items(), key=lambda x: -x[1])[:3]
            tools_str = ", ".join([f"{t}:{c}" for t, c in top_tools])
            lines.append(f"| {short_name(model)} | {model_data['total_calls']} | {passed_str} | {tools_str} |")
        lines.append("")
    
    # 5. Linter Tool Analysis
    lines.append("## 5. Linter Tool Analysis\n")
    
    lines.append("### read_lints Effectiveness\n")
    lines.append("| Model | Total Calls | Empty (no errors) | Productive (found errors) | Empty Rate |")
    lines.append("|-------|-------------|-------------------|---------------------------|------------|")
    for model, stats in report["linter_analysis"]["by_model"].items():
        lines.append(f"| {short_name(model)} | {stats['total_calls']} | {stats['empty_calls']} | {stats['productive_calls']} | {stats['empty_rate']:.0%} |")
    lines.append("")
    
    # 6. Conversation Metrics
    lines.append("## 6. Conversation Metrics\n")
    
    lines.append("### Average Metrics by Model\n")
    lines.append("| Model | Avg Messages | Avg Turns | Avg Input Tokens | Avg Output Tokens |")
    lines.append("|-------|--------------|-----------|------------------|-------------------|")
    for model, stats in report["conversation_metrics"]["by_model"].items():
        lines.append(f"| {short_name(model)} | {stats['avg_messages']:.0f} | {stats['avg_assistant_turns']:.0f} | {stats['avg_input_tokens']:.0f} | {stats['avg_output_tokens']:.0f} |")
    lines.append("")
    
    # 7. Code Change Metrics
    lines.append("## 7. Code Change Metrics\n")
    
    lines.append("### Patch Size by Model\n")
    lines.append("| Model | Avg Lines Added | Avg Lines Removed | Avg Files Changed |")
    lines.append("|-------|-----------------|-------------------|-------------------|")
    for model, stats in report["code_change_metrics"]["by_model"].items():
        lines.append(f"| {short_name(model)} | {stats['avg_lines_added']:.1f} | {stats['avg_lines_removed']:.1f} | {stats['avg_files_changed']:.1f} |")
    lines.append("")
    
    lines.append("### Patch Size: Pass vs Fail\n")
    lines.append("| Model | Avg Lines (Pass) | Avg Lines (Fail) |")
    lines.append("|-------|------------------|------------------|")
    for model, stats in report["code_change_metrics"]["by_model"].items():
        lines.append(f"| {short_name(model)} | {stats['avg_lines_passed']:.1f} | {stats['avg_lines_failed']:.1f} |")
    lines.append("")
    
    # 8. Cost Analysis
    lines.append("## 8. Cost Analysis\n")
    lines.append("*Cost estimates include prompt caching: cached input tokens priced at 10-25% of normal input rate*\n")

    lines.append("### Cost by Model\n")
    lines.append("| Model | Total Cost | Avg/Task | Cost/Success | Cache Hit Rate |")
    lines.append("|-------|------------|----------|--------------|----------------|")
    for model, stats in report["cost_analysis"]["by_model"].items():
        cost_per_success = f"${stats['cost_per_success_usd']:.2f}" if stats['cost_per_success_usd'] else "N/A"
        cache_rate = f"{stats['cache_hit_rate']*100:.0f}%"
        lines.append(f"| {short_name(model)} | ${stats['total_cost_usd']:.2f} | ${stats['avg_cost_per_task_usd']:.2f} | {cost_per_success} | {cache_rate} |")
    lines.append("")

    lines.append("### Token Breakdown by Model\n")
    lines.append("| Model | Total Input | Cached | Uncached | Output |")
    lines.append("|-------|-------------|--------|----------|--------|")
    for model, stats in report["cost_analysis"]["by_model"].items():
        lines.append(f"| {short_name(model)} | {stats['total_input_tokens']:,} | {stats['total_cached_input_tokens']:,} | {stats['total_uncached_input_tokens']:,} | {stats['total_output_tokens']:,} |")
    lines.append("")
    
    lines.append("### Cost per Success Rankings\n")
    lines.append("*Lower is better - cost to achieve one successful task*\n")
    lines.append("| Rank | Model | Cost/Success |")
    lines.append("|------|-------|--------------|")
    for item in report["cost_analysis"]["cost_rankings"]:
        lines.append(f"| {item['rank']} | {short_name(item['model'])} | ${item['cost_per_success_usd']:.2f} |")
    lines.append("")
    
    # Hard Tasks (Unsolved)
    lines.append("## Appendix: Unsolved Tasks\n")
    hard_tasks = report["core_metrics"]["task_difficulty"]["hard_tasks"]
    if hard_tasks:
        lines.append(f"The following {len(hard_tasks)} tasks were not solved by any model:\n")
        for task in hard_tasks[:20]:
            lines.append(f"- `{task}`")
        if len(hard_tasks) > 20:
            lines.append(f"- ... and {len(hard_tasks)-20} more")
    else:
        lines.append("All tasks were solved by at least one model!")
    lines.append("")
    
    return "\n".join(lines)


def main():
    # Get the data directory (from analysis/ folder at project root)
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "outputs" / "data"
    
    if not data_dir.exists():
        print(f"Error: Data directory not found at {data_dir}")
        return
    
    print(f"Loading results from {data_dir}...")
    results = load_all_results(data_dir)
    print(f"Loaded {len(results)} results")
    
    if not results:
        print("No results found!")
        return
    
    # Generate report
    print("Generating comprehensive analysis...")
    report = generate_report(results)
    
    # Save outputs to analysis/ directory (same as script location)
    output_dir = Path(__file__).parent
    json_path = output_dir / "analysis_report.json"
    with open(json_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"JSON report saved to: {json_path}")
    
    # Generate and save markdown report
    markdown = generate_markdown_report(report)
    md_path = output_dir / "analysis_findings.md"
    with open(md_path, 'w') as f:
        f.write(markdown)
    print(f"Markdown report saved to: {md_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("ANALYSIS SUMMARY")
    print("="*60)
    print(f"Total tasks: {report['summary']['total_tasks']}")
    print(f"Total models: {report['summary']['total_models']}")
    print(f"Overall pass rate: {report['summary']['overall_pass_rate']:.1%}")
    print(f"Total estimated cost: ${report['summary']['total_cost_usd']:.2f}")
    print(f"Best model: {short_name(report['summary']['best_model'])} ({report['summary']['best_pass_rate']:.1%})")
    print(f"Lowest cost/success: {short_name(report['summary']['lowest_cost_per_success'])}")
    print("="*60)


if __name__ == "__main__":
    main()
