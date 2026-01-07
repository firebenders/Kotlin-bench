#!/usr/bin/env python3
"""
Conversation length analysis comparing ij0 (no IntelliJ guidance) vs ij1 (with IntelliJ guidance).

Analyzes:
1. Number of turns/iterations
2. Number of tool calls
3. Statistical significance of differences
"""

import json
from pathlib import Path
from collections import defaultdict
import statistics
import math


def t_cdf_approx(t: float, df: int) -> float:
    """Approximate the CDF of Student's t-distribution."""
    if df <= 0:
        return 0.5
    if df > 100:
        return 0.5 * (1 + math.erf(t / math.sqrt(2)))
    adjusted_t = t * math.sqrt((df - 0.5) / (df + 1)) if df > 1 else t
    return 0.5 * (1 + math.erf(adjusted_t / math.sqrt(2)))


def paired_t_test(differences: list) -> dict:
    """Perform a paired t-test on the differences."""
    n = len(differences)
    if n < 2:
        return {"t_stat": 0, "p_value": 1.0, "significant_05": False, "significant_01": False, "n": n}
    
    mean_diff = statistics.mean(differences)
    std_diff = statistics.stdev(differences)
    
    if std_diff == 0:
        if mean_diff == 0:
            return {"t_stat": 0, "p_value": 1.0, "significant_05": False, "significant_01": False, "n": n}
        else:
            return {"t_stat": float('inf'), "p_value": 0.0, "significant_05": True, "significant_01": True, "n": n}
    
    se = std_diff / math.sqrt(n)
    t_stat = mean_diff / se
    df = n - 1
    
    p_value = 2 * (1 - t_cdf_approx(abs(t_stat), df))
    p_value = min(1.0, max(0.0, p_value))
    
    return {
        "t_stat": round(t_stat, 3),
        "p_value": round(p_value, 4),
        "significant_05": p_value < 0.05,
        "significant_01": p_value < 0.01,
        "n": n,
        "mean_diff": round(mean_diff, 2),
        "std_diff": round(std_diff, 2),
        "se": round(se, 2),
        "ci_95_low": round(mean_diff - 2.0 * se, 2),
        "ci_95_high": round(mean_diff + 2.0 * se, 2),
    }


def load_report(report_path: Path) -> dict:
    with open(report_path) as f:
        return json.load(f)


def load_agent_log(log_path: Path) -> dict:
    """Load agent_log.json and extract conversation metrics."""
    try:
        with open(log_path) as f:
            data = json.load(f)
        
        iterations = data.get("iterations", [])
        num_turns = len(iterations)
        
        # Count total tool calls across all iterations
        total_tool_calls = 0
        for iteration in iterations:
            tool_calls = iteration.get("tool_calls", [])
            total_tool_calls += len(tool_calls)
        
        return {
            "num_turns": num_turns,
            "total_tool_calls": total_tool_calls,
            "success": data.get("success", False),
        }
    except Exception as e:
        return {"num_turns": 0, "total_tool_calls": 0, "success": False, "error": str(e)}


def extract_conversation_data(data_dir: Path, report: dict) -> dict:
    """
    Extract conversation metrics for all task/model/settings combinations.
    
    Returns: {model: {task_id: {settings_id: {num_turns, total_tool_calls, passed}}}}
    """
    conversation_data = defaultdict(lambda: defaultdict(dict))
    
    for task_id, task_data in report.get("results", {}).items():
        for model, results_list in task_data.items():
            for result in results_list:
                settings = result.get("settings", {})
                settings_id = f"ij{int(settings.get('intellij_guidance', True))}_oracle{int(settings.get('oracle_files', False))}"
                
                paths = result.get("paths", {})
                agent_log_path = paths.get("agent_log")
                
                if agent_log_path:
                    full_path = data_dir.parent / agent_log_path
                    if full_path.exists():
                        log_data = load_agent_log(full_path)
                        
                        if log_data.get("num_turns", 0) > 0:
                            conversation_data[model][task_id][settings_id] = {
                                "num_turns": log_data["num_turns"],
                                "total_tool_calls": log_data["total_tool_calls"],
                                "passed": result.get("test_passed", False),
                            }
    
    return dict(conversation_data)


def compare_settings_conversation(conversation_data: dict, model: str,
                                   setting_a: str = "ij0_oracle1",
                                   setting_b: str = "ij1_oracle1",
                                   filter_mode: str = "both_passed") -> dict:
    """
    Compare conversation metrics between two settings for a model.
    """
    model_data = conversation_data.get(model, {})
    
    comparisons = []
    
    for task_id, task_settings in model_data.items():
        if setting_a not in task_settings or setting_b not in task_settings:
            continue
        
        data_a = task_settings[setting_a]
        data_b = task_settings[setting_b]
        
        # Apply filter
        if filter_mode == "both_passed":
            if not (data_a["passed"] and data_b["passed"]):
                continue
        elif filter_mode == "all":
            pass  # include all
        
        turns_a = data_a["num_turns"]
        turns_b = data_b["num_turns"]
        tools_a = data_a["total_tool_calls"]
        tools_b = data_b["total_tool_calls"]
        
        turns_diff = turns_b - turns_a  # positive = b has more turns
        tools_diff = tools_b - tools_a  # positive = b has more tool calls
        
        comparisons.append({
            "task_id": task_id,
            "turns_a": turns_a,
            "turns_b": turns_b,
            "turns_diff": turns_diff,
            "tools_a": tools_a,
            "tools_b": tools_b,
            "tools_diff": tools_diff,
            "a_passed": data_a["passed"],
            "b_passed": data_b["passed"],
        })
    
    if not comparisons:
        return {"n": 0}
    
    turns_diffs = [c["turns_diff"] for c in comparisons]
    tools_diffs = [c["tools_diff"] for c in comparisons]
    turns_a = [c["turns_a"] for c in comparisons]
    turns_b = [c["turns_b"] for c in comparisons]
    tools_a = [c["tools_a"] for c in comparisons]
    tools_b = [c["tools_b"] for c in comparisons]
    
    # Perform paired t-tests
    turns_t_test = paired_t_test(turns_diffs)
    tools_t_test = paired_t_test(tools_diffs)
    
    return {
        "n": len(comparisons),
        "mean_turns_a": statistics.mean(turns_a),
        "mean_turns_b": statistics.mean(turns_b),
        "mean_turns_diff": statistics.mean(turns_diffs),
        "mean_tools_a": statistics.mean(tools_a),
        "mean_tools_b": statistics.mean(tools_b),
        "mean_tools_diff": statistics.mean(tools_diffs),
        "turns_t_test": turns_t_test,
        "tools_t_test": tools_t_test,
        "comparisons": comparisons,
    }


def main():
    data_dir = Path(__file__).parent.parent / "outputs" / "data"
    report_path = Path(__file__).parent.parent / "outputs" / "report.json"
    
    if not report_path.exists():
        print(f"Report not found: {report_path}")
        return
    
    report = load_report(report_path)
    conversation_data = extract_conversation_data(data_dir, report)
    
    models = sorted(conversation_data.keys())
    
    print("=" * 120)
    print("CONVERSATION LENGTH ANALYSIS: ij0 (no IntelliJ guidance) vs ij1 (with IntelliJ guidance)")
    print("=" * 120)
    print()
    print("Positive diff = ij1 uses MORE turns/tools")
    print("Negative diff = ij1 uses FEWER turns/tools")
    print()
    
    # =========================================================================
    # Analysis for tasks where BOTH passed
    # =========================================================================
    print("=" * 120)
    print("ANALYSIS: Only tasks where BOTH ij0 and ij1 PASSED")
    print("=" * 120)
    print()
    
    # Turns analysis
    print("-" * 120)
    print(f"{'Model':<35} {'N':>5} {'ij0 turns':>12} {'ij1 turns':>12} {'Diff':>10} {'95% CI':>20} {'p-value':>10} {'Sig?':>6}")
    print("-" * 120)
    
    both_passed_results = {}
    
    for model in models:
        result = compare_settings_conversation(conversation_data, model, "ij0_oracle1", "ij1_oracle1", "both_passed")
        if result["n"] == 0:
            continue
        
        both_passed_results[model] = result
        t_test = result.get("turns_t_test", {})
        
        if t_test:
            ci_str = f"[{t_test.get('ci_95_low', 0):+.1f}, {t_test.get('ci_95_high', 0):+.1f}]"
            p_value = t_test.get("p_value", 1.0)
            sig_marker = "**" if t_test.get("significant_01") else ("*" if t_test.get("significant_05") else "")
        else:
            ci_str = "N/A"
            p_value = 1.0
            sig_marker = ""
        
        print(f"{model:<35} {result['n']:>5} {result['mean_turns_a']:>11.1f} {result['mean_turns_b']:>11.1f} "
              f"{result['mean_turns_diff']:>+9.1f} {ci_str:>20} {p_value:>10.4f} {sig_marker:>6}")
    
    print("-" * 120)
    
    # Tool calls analysis
    print()
    print("-" * 120)
    print(f"{'Model':<35} {'N':>5} {'ij0 tools':>12} {'ij1 tools':>12} {'Diff':>10} {'95% CI':>20} {'p-value':>10} {'Sig?':>6}")
    print("-" * 120)
    
    for model in models:
        result = both_passed_results.get(model)
        if not result or result["n"] == 0:
            continue
        
        t_test = result.get("tools_t_test", {})
        
        if t_test:
            ci_str = f"[{t_test.get('ci_95_low', 0):+.1f}, {t_test.get('ci_95_high', 0):+.1f}]"
            p_value = t_test.get("p_value", 1.0)
            sig_marker = "**" if t_test.get("significant_01") else ("*" if t_test.get("significant_05") else "")
        else:
            ci_str = "N/A"
            p_value = 1.0
            sig_marker = ""
        
        print(f"{model:<35} {result['n']:>5} {result['mean_tools_a']:>11.1f} {result['mean_tools_b']:>11.1f} "
              f"{result['mean_tools_diff']:>+9.1f} {ci_str:>20} {p_value:>10.4f} {sig_marker:>6}")
    
    print("-" * 120)
    print()
    print("* = p < 0.05, ** = p < 0.01")
    
    # Summary of significant differences
    print()
    print("=" * 120)
    print("STATISTICALLY SIGNIFICANT DIFFERENCES (p < 0.05)")
    print("=" * 120)
    
    sig_turns = []
    sig_tools = []
    
    for model, result in both_passed_results.items():
        turns_t = result.get("turns_t_test", {})
        tools_t = result.get("tools_t_test", {})
        
        if turns_t.get("significant_05"):
            direction = "MORE" if result["mean_turns_diff"] > 0 else "FEWER"
            sig_turns.append((model, result["mean_turns_diff"], turns_t["p_value"], direction))
        
        if tools_t.get("significant_05"):
            direction = "MORE" if result["mean_tools_diff"] > 0 else "FEWER"
            sig_tools.append((model, result["mean_tools_diff"], tools_t["p_value"], direction))
    
    print("\nTurns/Iterations:")
    if sig_turns:
        for model, diff, p, direction in sig_turns:
            sig_level = "p < 0.01" if p < 0.01 else "p < 0.05"
            print(f"  {model}: ij1 uses {direction} turns ({diff:+.1f}, {sig_level})")
    else:
        print("  No statistically significant differences in number of turns.")
    
    print("\nTool Calls:")
    if sig_tools:
        for model, diff, p, direction in sig_tools:
            sig_level = "p < 0.01" if p < 0.01 else "p < 0.05"
            print(f"  {model}: ij1 uses {direction} tool calls ({diff:+.1f}, {sig_level})")
    else:
        print("  No statistically significant differences in number of tool calls.")
    
    # Overall summary across all models
    print()
    print("=" * 120)
    print("OVERALL SUMMARY (Tasks where both passed)")
    print("=" * 120)
    
    all_turns_diffs = []
    all_tools_diffs = []
    total_tasks = 0
    
    for model, result in both_passed_results.items():
        if result["n"] > 0:
            all_turns_diffs.extend([c["turns_diff"] for c in result["comparisons"]])
            all_tools_diffs.extend([c["tools_diff"] for c in result["comparisons"]])
            total_tasks += result["n"]
    
    if all_turns_diffs:
        turns_overall = paired_t_test(all_turns_diffs)
        tools_overall = paired_t_test(all_tools_diffs)
        
        print(f"\nAcross all models (n={total_tasks} task pairs):")
        print(f"  Turns: ij1 uses {statistics.mean(all_turns_diffs):+.1f} turns on average (p={turns_overall['p_value']:.4f})")
        print(f"  Tools: ij1 uses {statistics.mean(all_tools_diffs):+.1f} tool calls on average (p={tools_overall['p_value']:.4f})")
        
        if turns_overall["significant_05"]:
            direction = "MORE" if statistics.mean(all_turns_diffs) > 0 else "FEWER"
            print(f"\n  → Overall, IntelliJ guidance leads to {direction} conversation turns (SIGNIFICANT)")
        else:
            print(f"\n  → No significant overall difference in conversation turns")
        
        if tools_overall["significant_05"]:
            direction = "MORE" if statistics.mean(all_tools_diffs) > 0 else "FEWER"
            print(f"  → Overall, IntelliJ guidance leads to {direction} tool calls (SIGNIFICANT)")
        else:
            print(f"  → No significant overall difference in tool calls")


if __name__ == "__main__":
    main()
