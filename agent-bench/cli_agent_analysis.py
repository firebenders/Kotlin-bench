#!/usr/bin/env python3
"""
CLI Agent Evaluation Analysis

Generates detailed analysis reports from CLI agent evaluation results.
Reads from outputs/cli_agent_data/ and produces:
- Per-task file accuracy metrics (precision, recall, F1)
- Aggregate statistics by agent/model
- Task difficulty categorization
- Comparison across agents/models

Usage:
    python agent-bench/cli_agent_analysis.py
    python agent-bench/cli_agent_analysis.py --agent claude-code --model claude-sonnet-4
    python agent-bench/cli_agent_analysis.py --format markdown
"""

import json
import os
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


# =============================================================================
# Paths
# =============================================================================

LOCAL_OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
CLI_AGENT_DATA_DIR = LOCAL_OUTPUTS_DIR / "cli_agent_data"
ANALYSIS_DIR = Path(__file__).parent.parent / "analysis"


# =============================================================================
# Data Loading
# =============================================================================

def load_report() -> dict:
    """Load the consolidated CLI agent report."""
    report_path = LOCAL_OUTPUTS_DIR / "cli_agent_report.json"
    if not report_path.exists():
        print(f"Report not found at {report_path}")
        print("Run evaluations first or use --report-only to regenerate")
        return {}
    
    with open(report_path) as f:
        return json.load(f)


def load_task_result(task_id: str, agent: str, model: str, rules: str = "no-rules") -> Optional[dict]:
    """Load result files for a specific task/agent/model/rules."""
    result_dir = CLI_AGENT_DATA_DIR / task_id / agent / model / rules
    
    # Fallback: check for old format (results directly in model dir)
    if not result_dir.exists():
        old_dir = CLI_AGENT_DATA_DIR / task_id / agent / model
        if old_dir.exists() and (old_dir / "file_comparison.json").exists():
            result_dir = old_dir
        else:
            return None
    
    result = {"task_id": task_id, "agent": agent, "model": model, "rules": rules}
    
    # File comparison
    comp_path = result_dir / "file_comparison.json"
    if comp_path.exists():
        with open(comp_path) as f:
            result["file_comparison"] = json.load(f)
    
    # Agent trace
    trace_path = result_dir / "agent_trace.json"
    if trace_path.exists():
        with open(trace_path) as f:
            result["agent_trace"] = json.load(f)
    
    # Test result
    test_path = result_dir / "test_result.json"
    if test_path.exists():
        with open(test_path) as f:
            result["test_result"] = json.load(f)
    
    # Agent patch
    patch_path = result_dir / "agent_patch.diff"
    if patch_path.exists():
        result["patch_size"] = patch_path.stat().st_size
    
    return result


def load_all_results(agent: str = None, model: str = None, rules: str = None) -> List[dict]:
    """Load all results, optionally filtered by agent, model, and/or rules version."""
    results = []
    
    if not CLI_AGENT_DATA_DIR.exists():
        return results
    
    for task_dir in sorted(CLI_AGENT_DATA_DIR.iterdir()):
        if not task_dir.is_dir():
            continue
        
        for agent_dir in sorted(task_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            if agent and agent_dir.name != agent:
                continue
            
            for model_dir in sorted(agent_dir.iterdir()):
                if not model_dir.is_dir():
                    continue
                if model and model_dir.name != model:
                    continue
                
                # Check for old format (files directly in model_dir)
                has_result_files = (model_dir / "file_comparison.json").exists()
                has_subdirs = any(d.is_dir() for d in model_dir.iterdir() if not d.name.startswith("."))
                
                if has_result_files and not has_subdirs:
                    # Old format: treat as "no-rules"
                    if rules and rules != "no-rules":
                        continue
                    result = load_task_result(task_dir.name, agent_dir.name, model_dir.name, "no-rules")
                    if result:
                        results.append(result)
                else:
                    # New format: rules subdirectories
                    for rules_dir in sorted(model_dir.iterdir()):
                        if not rules_dir.is_dir():
                            continue
                        if rules and rules_dir.name != rules:
                            continue
                        result = load_task_result(task_dir.name, agent_dir.name, model_dir.name, rules_dir.name)
                        if result:
                            results.append(result)
    
    return results


# =============================================================================
# Analysis Functions
# =============================================================================

def analyze_file_accuracy(results: List[dict]) -> dict:
    """
    Analyze file-level accuracy across all results.
    
    Returns detailed statistics about how well agents identify
    the correct files to modify.
    """
    analysis = {
        "total_tasks": len(results),
        "tasks_with_patch": 0,
        "tasks_with_exact_match": 0,
        "tasks_with_partial_match": 0,
        "tasks_with_no_match": 0,
        "precisions": [],
        "recalls": [],
        "f1_scores": [],
        "files_per_task": {
            "agent": [],
            "gold": [],
        },
    }
    
    for result in results:
        comp = result.get("file_comparison", {})
        if not comp:
            continue
        
        precision = comp.get("precision", 0)
        recall = comp.get("recall", 0)
        f1 = comp.get("f1_score", 0)
        agent_count = comp.get("agent_file_count", 0)
        gold_count = comp.get("gold_file_count", 0)
        
        if agent_count > 0:
            analysis["tasks_with_patch"] += 1
        
        analysis["precisions"].append(precision)
        analysis["recalls"].append(recall)
        analysis["f1_scores"].append(f1)
        analysis["files_per_task"]["agent"].append(agent_count)
        analysis["files_per_task"]["gold"].append(gold_count)
        
        if precision == 1.0 and recall == 1.0:
            analysis["tasks_with_exact_match"] += 1
        elif f1 > 0:
            analysis["tasks_with_partial_match"] += 1
        else:
            analysis["tasks_with_no_match"] += 1
    
    # Compute aggregate stats
    for metric in ["precisions", "recalls", "f1_scores"]:
        values = analysis[metric]
        if values:
            analysis[f"avg_{metric[:-1]}"] = round(statistics.mean(values), 4)
            analysis[f"median_{metric[:-1]}"] = round(statistics.median(values), 4)
            if len(values) > 1:
                analysis[f"stdev_{metric[:-1]}"] = round(statistics.stdev(values), 4)
    
    for key in ["agent", "gold"]:
        values = analysis["files_per_task"][key]
        if values:
            analysis[f"avg_{key}_files"] = round(statistics.mean(values), 2)
            analysis[f"median_{key}_files"] = round(statistics.median(values), 2)
    
    return analysis


def categorize_tasks_by_difficulty(results: List[dict]) -> dict:
    """
    Categorize tasks by difficulty based on gold patch complexity.
    
    - Easy: 1 file in gold patch
    - Medium: 2-3 files in gold patch
    - Hard: 4+ files in gold patch
    """
    categories = {"easy": [], "medium": [], "hard": []}
    
    for result in results:
        comp = result.get("file_comparison", {})
        gold_count = comp.get("gold_file_count", 0)
        
        if gold_count <= 1:
            categories["easy"].append(result)
        elif gold_count <= 3:
            categories["medium"].append(result)
        else:
            categories["hard"].append(result)
    
    # Compute stats per category
    category_stats = {}
    for cat, cat_results in categories.items():
        if not cat_results:
            category_stats[cat] = {"count": 0}
            continue
        
        f1_scores = [
            r.get("file_comparison", {}).get("f1_score", 0)
            for r in cat_results
        ]
        test_passed = sum(
            1 for r in cat_results
            if r.get("test_result", {}).get("passed") is True
        )
        
        category_stats[cat] = {
            "count": len(cat_results),
            "avg_f1": round(statistics.mean(f1_scores), 4) if f1_scores else 0,
            "test_pass_rate": round(test_passed / len(cat_results), 4) if cat_results else 0,
        }
    
    return category_stats


def analyze_by_repo(results: List[dict]) -> dict:
    """Break down results by repository."""
    by_repo = defaultdict(list)
    
    for result in results:
        task_id = result.get("task_id", "")
        # Extract repo from task_id (format: owner__repo-number)
        repo = _task_id_to_repo(task_id)
        by_repo[repo].append(result)
    
    repo_stats = {}
    for repo, repo_results in sorted(by_repo.items()):
        f1_scores = [
            r.get("file_comparison", {}).get("f1_score", 0)
            for r in repo_results
        ]
        precisions = [
            r.get("file_comparison", {}).get("precision", 0)
            for r in repo_results
        ]
        recalls = [
            r.get("file_comparison", {}).get("recall", 0)
            for r in repo_results
        ]
        test_passed = sum(
            1 for r in repo_results
            if r.get("test_result", {}).get("passed") is True
        )
        
        repo_stats[repo] = {
            "count": len(repo_results),
            "avg_f1": round(statistics.mean(f1_scores), 4) if f1_scores else 0,
            "avg_precision": round(statistics.mean(precisions), 4) if precisions else 0,
            "avg_recall": round(statistics.mean(recalls), 4) if recalls else 0,
            "test_passed": test_passed,
            "test_pass_rate": round(test_passed / len(repo_results), 4) if repo_results else 0,
        }
    
    return repo_stats


def compare_agents_models(results: List[dict]) -> dict:
    """
    Compare performance across different agent/model/rules combinations.
    """
    by_combo = defaultdict(list)
    
    for result in results:
        agent = result.get("agent", "")
        model = result.get("model", "")
        rules = result.get("rules", "no-rules")
        key = f"{agent}/{model}/{rules}"
        by_combo[key].append(result)
    
    comparison = {}
    for combo, combo_results in sorted(by_combo.items()):
        f1_scores = [
            r.get("file_comparison", {}).get("f1_score", 0)
            for r in combo_results
        ]
        precisions = [
            r.get("file_comparison", {}).get("precision", 0)
            for r in combo_results
        ]
        recalls = [
            r.get("file_comparison", {}).get("recall", 0)
            for r in combo_results
        ]
        test_passed = sum(
            1 for r in combo_results
            if r.get("test_result", {}).get("passed") is True
        )
        
        comparison[combo] = {
            "total": len(combo_results),
            "avg_f1": round(statistics.mean(f1_scores), 4) if f1_scores else 0,
            "avg_precision": round(statistics.mean(precisions), 4) if precisions else 0,
            "avg_recall": round(statistics.mean(recalls), 4) if recalls else 0,
            "median_f1": round(statistics.median(f1_scores), 4) if f1_scores else 0,
            "test_passed": test_passed,
            "test_pass_rate": round(test_passed / len(combo_results), 4) if combo_results else 0,
        }
    
    return comparison


def analyze_trace(result: dict) -> Optional[dict]:
    """
    Analyze agent trace for a single task.
    
    Extracts metrics like:
    - Number of tool calls
    - Types of tools used
    - Number of files read/written
    - Conversation length
    """
    trace = result.get("agent_trace")
    if not trace:
        return None
    
    analysis = {
        "has_trace": True,
    }
    
    # Claude Code JSON output format may vary - try common structures
    if isinstance(trace, dict):
        # Try to extract common metrics
        if "messages" in trace:
            analysis["message_count"] = len(trace["messages"])
        if "tool_calls" in trace:
            analysis["tool_call_count"] = len(trace["tool_calls"])
        if "cost_usd" in trace:
            analysis["cost_usd"] = trace["cost_usd"]
        if "duration_ms" in trace:
            analysis["duration_ms"] = trace["duration_ms"]
        if "model" in trace:
            analysis["model_used"] = trace["model"]
        if "num_turns" in trace:
            analysis["num_turns"] = trace["num_turns"]
        # Claude Code specific fields
        if "result" in trace:
            analysis["result_text_length"] = len(str(trace["result"]))
    elif isinstance(trace, list):
        # Might be a list of messages/events
        analysis["event_count"] = len(trace)
    
    return analysis


# =============================================================================
# Report Generation
# =============================================================================

def generate_analysis_report(agent: str = None, model: str = None, rules: str = None) -> dict:
    """Generate a comprehensive analysis report."""
    results = load_all_results(agent=agent, model=model, rules=rules)
    
    if not results:
        print("No results found to analyze")
        return {}
    
    print(f"Analyzing {len(results)} results...")
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_results": len(results),
        "filters": {"agent": agent, "model": model, "rules": rules},
        "file_accuracy": analyze_file_accuracy(results),
        "difficulty_breakdown": categorize_tasks_by_difficulty(results),
        "by_repo": analyze_by_repo(results),
        "agent_model_comparison": compare_agents_models(results),
    }
    
    # Trace analysis (if any traces available)
    trace_analyses = []
    for result in results:
        ta = analyze_trace(result)
        if ta:
            trace_analyses.append(ta)
    
    if trace_analyses:
        report["trace_summary"] = {
            "tasks_with_traces": len(trace_analyses),
        }
    
    return report


def format_markdown(report: dict) -> str:
    """Format analysis report as markdown."""
    lines = []
    lines.append("# CLI Agent Evaluation Analysis")
    lines.append("")
    lines.append(f"Generated: {report.get('generated_at', 'N/A')}")
    lines.append(f"Total results: {report.get('total_results', 0)}")
    lines.append("")
    
    # File accuracy
    fa = report.get("file_accuracy", {})
    if fa:
        lines.append("## File-Level Accuracy")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Tasks evaluated | {fa.get('total_tasks', 0)} |")
        lines.append(f"| Tasks with patch | {fa.get('tasks_with_patch', 0)} |")
        lines.append(f"| Exact file match | {fa.get('tasks_with_exact_match', 0)} |")
        lines.append(f"| Partial file match | {fa.get('tasks_with_partial_match', 0)} |")
        lines.append(f"| No file match | {fa.get('tasks_with_no_match', 0)} |")
        lines.append(f"| Avg Precision | {fa.get('avg_precision', 0):.2%} |")
        lines.append(f"| Avg Recall | {fa.get('avg_recall', 0):.2%} |")
        lines.append(f"| Avg F1 | {fa.get('avg_f1', 0):.2%} |")
        lines.append(f"| Median F1 | {fa.get('median_f1_score', 0):.2%} |")
        lines.append("")
    
    # Difficulty breakdown
    diff = report.get("difficulty_breakdown", {})
    if diff:
        lines.append("## Difficulty Breakdown")
        lines.append("")
        lines.append("| Difficulty | Tasks | Avg F1 | Test Pass Rate |")
        lines.append("|-----------|-------|--------|----------------|")
        for cat in ["easy", "medium", "hard"]:
            stats = diff.get(cat, {})
            if stats.get("count", 0) > 0:
                lines.append(
                    f"| {cat.capitalize()} | {stats['count']} | "
                    f"{stats.get('avg_f1', 0):.2%} | "
                    f"{stats.get('test_pass_rate', 0):.2%} |"
                )
        lines.append("")
    
    # By repository
    by_repo = report.get("by_repo", {})
    if by_repo:
        lines.append("## Results by Repository")
        lines.append("")
        lines.append("| Repository | Tasks | Avg F1 | Avg Precision | Avg Recall | Test Pass Rate |")
        lines.append("|-----------|-------|--------|---------------|------------|----------------|")
        for repo, stats in sorted(by_repo.items()):
            lines.append(
                f"| {repo} | {stats['count']} | "
                f"{stats.get('avg_f1', 0):.2%} | "
                f"{stats.get('avg_precision', 0):.2%} | "
                f"{stats.get('avg_recall', 0):.2%} | "
                f"{stats.get('test_pass_rate', 0):.2%} |"
            )
        lines.append("")
    
    # Agent/model/rules comparison
    comparison = report.get("agent_model_comparison", {})
    if comparison:
        lines.append("## Agent/Model/Rules Comparison")
        lines.append("")
        lines.append("| Agent/Model/Rules | Tasks | Avg F1 | Median F1 | Avg Precision | Avg Recall | Test Pass Rate |")
        lines.append("|-------------------|-------|--------|-----------|---------------|------------|----------------|")
        for combo, stats in sorted(comparison.items()):
            lines.append(
                f"| {combo} | {stats['total']} | "
                f"{stats.get('avg_f1', 0):.2%} | "
                f"{stats.get('median_f1', 0):.2%} | "
                f"{stats.get('avg_precision', 0):.2%} | "
                f"{stats.get('avg_recall', 0):.2%} | "
                f"{stats.get('test_pass_rate', 0):.2%} |"
            )
        lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# Utility Functions
# =============================================================================

def _task_id_to_repo(task_id: str) -> str:
    """Extract repository name from task ID."""
    # Format: owner__repo-number (e.g., ankidroid__Anki-Android-14182)
    TASK_ID_TO_REPO = {
        "ankidroid__Anki-Android": "ankidroid/Anki-Android",
        "pinterest__ktlint": "pinterest/ktlint",
        "wordpress-mobile__WordPress-Android": "wordpress-mobile/WordPress-Android",
        "Kotlin__kotlinx.coroutines": "Kotlin/kotlinx.coroutines",
        "Kotlin__kotlinx-datetime": "Kotlin/kotlinx-datetime",
        "thunderbird__thunderbird-android": "thunderbird/thunderbird-android",
    }
    
    for prefix, repo in TASK_ID_TO_REPO.items():
        if task_id.startswith(prefix):
            return repo
    
    return "unknown"


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze CLI agent evaluation results")
    parser.add_argument("--agent", help="Filter by agent name")
    parser.add_argument("--model", help="Filter by model name")
    parser.add_argument("--rules", help="Filter by rules version (e.g., baseline, v1)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json",
                        help="Output format (default: json)")
    parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    report = generate_analysis_report(agent=args.agent, model=args.model, rules=args.rules)
    
    if not report:
        return
    
    if args.format == "markdown":
        output = format_markdown(report)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Markdown report saved to: {args.output}")
        else:
            print(output)
    else:
        if args.output:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2)
            print(f"JSON report saved to: {args.output}")
        else:
            # Print summary to console
            fa = report.get("file_accuracy", {})
            print("\n" + "=" * 60)
            print("FILE ACCURACY ANALYSIS")
            print("=" * 60)
            print(f"Tasks evaluated:     {fa.get('total_tasks', 0)}")
            print(f"Exact file match:    {fa.get('tasks_with_exact_match', 0)}")
            print(f"Partial file match:  {fa.get('tasks_with_partial_match', 0)}")
            print(f"No file match:       {fa.get('tasks_with_no_match', 0)}")
            print(f"Avg Precision:       {fa.get('avg_precision', 0):.2%}")
            print(f"Avg Recall:          {fa.get('avg_recall', 0):.2%}")
            print(f"Avg F1:              {fa.get('avg_f1', 0):.2%}")
            
            comparison = report.get("agent_model_comparison", {})
            if comparison:
                print(f"\nAGENT/MODEL/RULES COMPARISON")
                print("-" * 60)
                for combo, stats in sorted(comparison.items()):
                    print(f"  {combo}: F1={stats.get('avg_f1', 0):.2%}  "
                          f"P={stats.get('avg_precision', 0):.2%}  "
                          f"R={stats.get('avg_recall', 0):.2%}  "
                          f"Test={stats.get('test_pass_rate', 0):.1%}")
            
            by_repo = report.get("by_repo", {})
            if by_repo:
                print(f"\nBY REPOSITORY")
                print("-" * 60)
                for repo, stats in sorted(by_repo.items()):
                    print(f"  {repo:40} F1={stats.get('avg_f1', 0):.2%}  "
                          f"Test={stats.get('test_pass_rate', 0):.1%}  "
                          f"({stats['count']} tasks)")


if __name__ == "__main__":
    main()
