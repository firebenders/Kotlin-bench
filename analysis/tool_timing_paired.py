#!/usr/bin/env python3
"""
Paired tool timing analysis: Compare total validation time between ij0 and ij1
for tasks that succeeded in BOTH settings.

ij1 total = read_lints + gradle test (IDE linting + actual test runs)
ij0 total = gradle test only (used for both linting and test runs)
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
        "ci_95_low": round(mean_diff - 2.0 * se, 2),
        "ci_95_high": round(mean_diff + 2.0 * se, 2),
    }


def load_report(report_path: Path) -> dict:
    with open(report_path) as f:
        return json.load(f)


def load_agent_log(log_path: Path) -> dict:
    """Load agent_log.json."""
    try:
        with open(log_path) as f:
            return json.load(f)
    except Exception:
        return {}


def extract_tool_times_from_log(log_data: dict) -> dict:
    """
    Extract total time spent on read_lints and gradle test commands.
    
    Returns: {read_lints_total_ms, gradle_test_total_ms, read_lints_count, gradle_test_count}
    """
    read_lints_total = 0
    gradle_test_total = 0
    read_lints_count = 0
    gradle_test_count = 0
    
    iterations = log_data.get("iterations", [])
    
    for iteration in iterations:
        tool_calls = iteration.get("tool_calls", [])
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("tool_name")
            duration_ms = tool_call.get("duration_ms")
            input_json = tool_call.get("input_json", "")
            
            if duration_ms is None or not tool_name:
                continue
            
            if tool_name == "read_lints":
                read_lints_total += duration_ms
                read_lints_count += 1
            elif tool_name == "run_terminal_cmd":
                input_lower = input_json.lower()
                if ("gradle" in input_lower or "gradlew" in input_lower) and "test" in input_lower:
                    gradle_test_total += duration_ms
                    gradle_test_count += 1
    
    return {
        "read_lints_total_ms": read_lints_total,
        "gradle_test_total_ms": gradle_test_total,
        "read_lints_count": read_lints_count,
        "gradle_test_count": gradle_test_count,
    }


def get_tasks_passed_in_both(report: dict) -> dict:
    """
    Find tasks that passed in both ij0_oracle1 and ij1_oracle1 for each model.
    
    Returns: {model: [list of task_ids]}
    """
    tasks_by_model = defaultdict(list)
    
    for task_id, task_data in report.get("results", {}).items():
        for model, results_list in task_data.items():
            ij0_passed = False
            ij1_passed = False
            
            for result in results_list:
                settings = result.get("settings", {})
                settings_id = f"ij{int(settings.get('intellij_guidance', True))}_oracle{int(settings.get('oracle_files', False))}"
                
                if settings_id == "ij0_oracle1" and result.get("test_passed"):
                    ij0_passed = True
                elif settings_id == "ij1_oracle1" and result.get("test_passed"):
                    ij1_passed = True
            
            if ij0_passed and ij1_passed:
                tasks_by_model[model].append(task_id)
    
    return dict(tasks_by_model)


def main():
    data_dir = Path(__file__).parent.parent / "outputs" / "data"
    report_path = Path(__file__).parent.parent / "outputs" / "report.json"
    
    if not report_path.exists():
        print(f"Report not found: {report_path}")
        return
    
    report = load_report(report_path)
    tasks_passed_both = get_tasks_passed_in_both(report)
    
    print("=" * 100)
    print("PAIRED TOOL TIMING ANALYSIS")
    print("Comparing total validation time: ij1 (read_lints + gradle test) vs ij0 (gradle test)")
    print("Only tasks that PASSED in BOTH settings")
    print("=" * 100)
    print()
    
    # Collect paired data per model
    all_comparisons = []
    model_results = {}
    
    for model, task_ids in sorted(tasks_passed_both.items()):
        comparisons = []
        
        for task_id in task_ids:
            # Get ij0 data
            ij0_log_path = data_dir / task_id / model / "ij0_oracle1" / "agent_log.json"
            ij1_log_path = data_dir / task_id / model / "ij1_oracle1" / "agent_log.json"
            
            if not ij0_log_path.exists() or not ij1_log_path.exists():
                continue
            
            ij0_log = load_agent_log(ij0_log_path)
            ij1_log = load_agent_log(ij1_log_path)
            
            if not ij0_log or not ij1_log:
                continue
            
            ij0_times = extract_tool_times_from_log(ij0_log)
            ij1_times = extract_tool_times_from_log(ij1_log)
            
            # ij0 total = gradle test only
            ij0_total = ij0_times["gradle_test_total_ms"]
            
            # ij1 total = read_lints + gradle test
            ij1_total = ij1_times["read_lints_total_ms"] + ij1_times["gradle_test_total_ms"]
            
            # Only include if there was some validation activity
            if ij0_total > 0 or ij1_total > 0:
                diff = ij1_total - ij0_total  # positive = ij1 slower
                comparisons.append({
                    "task_id": task_id,
                    "ij0_total_ms": ij0_total,
                    "ij1_total_ms": ij1_total,
                    "ij1_read_lints_ms": ij1_times["read_lints_total_ms"],
                    "ij1_gradle_ms": ij1_times["gradle_test_total_ms"],
                    "ij0_gradle_ms": ij0_times["gradle_test_total_ms"],
                    "ij1_read_lints_count": ij1_times["read_lints_count"],
                    "ij1_gradle_count": ij1_times["gradle_test_count"],
                    "ij0_gradle_count": ij0_times["gradle_test_count"],
                    "diff_ms": diff,
                })
        
        if comparisons:
            model_results[model] = comparisons
            all_comparisons.extend(comparisons)
    
    # Print per-model results
    print("-" * 120)
    print(f"{'Model':<35} {'N':>5} {'ij0 gradle':>15} {'ij1 total':>15} {'Diff':>12} {'p-value':>10} {'Sig?':>6}")
    print(f"{'':35} {'':>5} {'(mean s)':>15} {'(lint+gradle)':>15} {'(s)':>12}")
    print("-" * 120)
    
    for model in sorted(model_results.keys()):
        comparisons = model_results[model]
        n = len(comparisons)
        
        ij0_totals = [c["ij0_total_ms"] for c in comparisons]
        ij1_totals = [c["ij1_total_ms"] for c in comparisons]
        diffs = [c["diff_ms"] for c in comparisons]
        
        ij0_mean = statistics.mean(ij0_totals) / 1000
        ij1_mean = statistics.mean(ij1_totals) / 1000
        diff_mean = statistics.mean(diffs) / 1000
        
        t_test = paired_t_test(diffs)
        sig_marker = "**" if t_test.get("significant_01") else ("*" if t_test.get("significant_05") else "")
        
        print(f"{model:<35} {n:>5} {ij0_mean:>14.1f}s {ij1_mean:>14.1f}s {diff_mean:>+11.1f}s {t_test['p_value']:>10.4f} {sig_marker:>6}")
    
    print("-" * 120)
    print("* = p < 0.05, ** = p < 0.01")
    print("Positive diff = ij1 (with IntelliJ tools) takes MORE time")
    print("Negative diff = ij1 (with IntelliJ tools) takes LESS time")
    
    # Overall summary
    if all_comparisons:
        print()
        print("=" * 100)
        print("OVERALL SUMMARY (all models, tasks where both passed)")
        print("=" * 100)
        
        ij0_totals = [c["ij0_total_ms"] for c in all_comparisons]
        ij1_totals = [c["ij1_total_ms"] for c in all_comparisons]
        ij1_lints = [c["ij1_read_lints_ms"] for c in all_comparisons]
        ij1_gradles = [c["ij1_gradle_ms"] for c in all_comparisons]
        diffs = [c["diff_ms"] for c in all_comparisons]
        
        ij0_gradle_counts = [c["ij0_gradle_count"] for c in all_comparisons]
        ij1_lint_counts = [c["ij1_read_lints_count"] for c in all_comparisons]
        ij1_gradle_counts = [c["ij1_gradle_count"] for c in all_comparisons]
        
        t_test = paired_t_test(diffs)
        
        print(f"\nTasks compared: {len(all_comparisons)}")
        print()
        print("ij0 (without IntelliJ tools):")
        print(f"  Total gradle test time: {sum(ij0_totals)/1000/60:.1f} minutes")
        print(f"  Mean per task: {statistics.mean(ij0_totals)/1000:.1f}s")
        print(f"  Total gradle test calls: {sum(ij0_gradle_counts)}")
        print(f"  Mean calls per task: {statistics.mean(ij0_gradle_counts):.1f}")
        print()
        print("ij1 (with IntelliJ tools):")
        print(f"  Total read_lints time: {sum(ij1_lints)/1000/60:.1f} minutes")
        print(f"  Total gradle test time: {sum(ij1_gradles)/1000/60:.1f} minutes")
        print(f"  Combined total: {sum(ij1_totals)/1000/60:.1f} minutes")
        print(f"  Mean per task: {statistics.mean(ij1_totals)/1000:.1f}s")
        print(f"  Total read_lints calls: {sum(ij1_lint_counts)}")
        print(f"  Total gradle test calls: {sum(ij1_gradle_counts)}")
        print()
        print("-" * 80)
        diff_mean = statistics.mean(diffs)
        if diff_mean < 0:
            print(f"  **ij1 is FASTER by {abs(diff_mean)/1000:.1f}s per task on average**")
        else:
            print(f"  **ij1 is SLOWER by {diff_mean/1000:.1f}s per task on average**")
        print(f"  p-value: {t_test['p_value']:.4f} {'(SIGNIFICANT)' if t_test['significant_05'] else '(not significant)'}")
        print(f"  95% CI: [{t_test['ci_95_low']/1000:.1f}s, {t_test['ci_95_high']/1000:.1f}s]")
        print("-" * 80)
        
        # Time savings breakdown
        print()
        print("Time Breakdown:")
        total_ij0 = sum(ij0_totals)
        total_ij1 = sum(ij1_totals)
        total_ij1_lints = sum(ij1_lints)
        total_ij1_gradle = sum(ij1_gradles)
        
        print(f"  ij0 gradle test total: {total_ij0/1000/60:.1f} min")
        print(f"  ij1 read_lints total:  {total_ij1_lints/1000/60:.1f} min")
        print(f"  ij1 gradle test total: {total_ij1_gradle/1000/60:.1f} min")
        print(f"  ij1 combined total:    {total_ij1/1000/60:.1f} min")
        print()
        if total_ij1 < total_ij0:
            print(f"  **TOTAL TIME SAVED: {(total_ij0 - total_ij1)/1000/60:.1f} minutes**")
        else:
            print(f"  **TOTAL EXTRA TIME: {(total_ij1 - total_ij0)/1000/60:.1f} minutes**")


if __name__ == "__main__":
    main()
