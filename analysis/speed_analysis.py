#!/usr/bin/env python3
"""
Speed analysis comparing ij0 (no IntelliJ guidance) vs ij1 (with IntelliJ guidance).

Analyzes:
1. Overall speed differences per model
2. Per-task speed comparisons
3. Speed differences on tasks where both settings passed vs all tasks
4. Statistical significance of speed differences (paired t-test)
"""

import json
from pathlib import Path
from collections import defaultdict
import statistics
import math


def t_cdf_approx(t: float, df: int) -> float:
    """
    Approximate the CDF of Student's t-distribution.
    Uses the relationship with the beta function for better accuracy.
    """
    if df <= 0:
        return 0.5
    
    x = df / (df + t * t)
    
    # Approximation using incomplete beta function relationship
    # For large df, t-distribution approaches normal
    if df > 100:
        # Use normal approximation
        return 0.5 * (1 + math.erf(t / math.sqrt(2)))
    
    # Simple approximation for moderate df
    # Based on the fact that P(T <= t) ≈ Φ(t * sqrt((df-0.5)/(df+1)))
    adjusted_t = t * math.sqrt((df - 0.5) / (df + 1)) if df > 1 else t
    return 0.5 * (1 + math.erf(adjusted_t / math.sqrt(2)))


def paired_t_test(differences: list) -> dict:
    """
    Perform a paired t-test on the differences.
    
    Tests H0: mean difference = 0
    
    Returns dict with t-statistic, p-value, and significance indicators.
    """
    n = len(differences)
    if n < 2:
        return {"t_stat": 0, "p_value": 1.0, "significant_05": False, "significant_01": False, "n": n}
    
    mean_diff = statistics.mean(differences)
    std_diff = statistics.stdev(differences)
    
    if std_diff == 0:
        # All differences are identical
        if mean_diff == 0:
            return {"t_stat": 0, "p_value": 1.0, "significant_05": False, "significant_01": False, "n": n}
        else:
            return {"t_stat": float('inf'), "p_value": 0.0, "significant_05": True, "significant_01": True, "n": n}
    
    # t-statistic
    se = std_diff / math.sqrt(n)
    t_stat = mean_diff / se
    df = n - 1
    
    # Two-tailed p-value
    # P(|T| > |t|) = 2 * P(T < -|t|)
    p_value = 2 * (1 - t_cdf_approx(abs(t_stat), df))
    p_value = min(1.0, max(0.0, p_value))  # Clamp to [0, 1]
    
    return {
        "t_stat": round(t_stat, 3),
        "p_value": round(p_value, 4),
        "significant_05": p_value < 0.05,
        "significant_01": p_value < 0.01,
        "n": n,
        "mean_diff": round(mean_diff, 2),
        "std_diff": round(std_diff, 2),
        "se": round(se, 2),
        "df": df,
        "ci_95_low": round(mean_diff - 2.0 * se, 2),  # Approximate 95% CI
        "ci_95_high": round(mean_diff + 2.0 * se, 2),
    }


def load_report(report_path: Path) -> dict:
    with open(report_path) as f:
        return json.load(f)


def load_agent_log(log_path: Path) -> dict:
    """Load agent_log.json and extract timing info."""
    try:
        with open(log_path) as f:
            return json.load(f)
    except Exception:
        return {}


def extract_timing_data(data_dir: Path, report: dict) -> dict:
    """
    Extract timing data for all task/model/settings combinations.
    
    Returns: {model: {task_id: {settings_id: {duration_ms, passed}}}}
    """
    timing_data = defaultdict(lambda: defaultdict(dict))
    
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
                        duration_ms = log_data.get("total_duration_ms")
                        
                        if duration_ms is not None:
                            timing_data[model][task_id][settings_id] = {
                                "duration_ms": duration_ms,
                                "duration_s": duration_ms / 1000,
                                "passed": result.get("test_passed", False),
                            }
    
    return dict(timing_data)


def compare_settings_speed(timing_data: dict, model: str, 
                           setting_a: str = "ij0_oracle1", 
                           setting_b: str = "ij1_oracle1",
                           filter_mode: str = "all") -> dict:
    """
    Compare speed between two settings for a model.
    
    filter_mode:
        - "all": Include all tasks where both settings have timing data
        - "both_passed": Only tasks where both settings passed
        - "a_passed": Only tasks where setting_a passed
        - "b_passed": Only tasks where setting_b passed
    """
    model_data = timing_data.get(model, {})
    
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
        elif filter_mode == "a_passed":
            if not data_a["passed"]:
                continue
        elif filter_mode == "b_passed":
            if not data_b["passed"]:
                continue
        
        time_a = data_a["duration_s"]
        time_b = data_b["duration_s"]
        diff = time_b - time_a  # positive = b slower, negative = b faster
        pct_diff = (diff / time_a * 100) if time_a > 0 else 0
        
        comparisons.append({
            "task_id": task_id,
            "time_a": time_a,
            "time_b": time_b,
            "diff_s": diff,
            "pct_diff": pct_diff,
            "a_passed": data_a["passed"],
            "b_passed": data_b["passed"],
        })
    
    if not comparisons:
        return {"n": 0, "t_test": None}
    
    diffs = [c["diff_s"] for c in comparisons]
    pct_diffs = [c["pct_diff"] for c in comparisons]
    times_a = [c["time_a"] for c in comparisons]
    times_b = [c["time_b"] for c in comparisons]
    
    # Perform paired t-test on the differences
    t_test_result = paired_t_test(diffs)
    
    return {
        "n": len(comparisons),
        "mean_time_a": statistics.mean(times_a),
        "mean_time_b": statistics.mean(times_b),
        "median_time_a": statistics.median(times_a),
        "median_time_b": statistics.median(times_b),
        "mean_diff_s": statistics.mean(diffs),
        "median_diff_s": statistics.median(diffs),
        "mean_pct_diff": statistics.mean(pct_diffs),
        "median_pct_diff": statistics.median(pct_diffs),
        "stdev_diff": statistics.stdev(diffs) if len(diffs) > 1 else 0,
        "b_faster_count": sum(1 for d in diffs if d < 0),
        "b_slower_count": sum(1 for d in diffs if d > 0),
        "comparisons": comparisons,
        "t_test": t_test_result,
    }


def main():
    data_dir = Path(__file__).parent.parent / "outputs" / "data"
    report_path = Path(__file__).parent.parent / "outputs" / "report.json"
    
    if not report_path.exists():
        print(f"Report not found: {report_path}")
        return
    
    report = load_report(report_path)
    timing_data = extract_timing_data(data_dir, report)
    
    models = sorted(timing_data.keys())
    
    print("=" * 100)
    print("SPEED ANALYSIS: ij0 (no IntelliJ guidance) vs ij1 (with IntelliJ guidance)")
    print("=" * 100)
    print()
    print("Positive diff = ij1 is SLOWER than ij0")
    print("Negative diff = ij1 is FASTER than ij0")
    print()
    
    # Summary table
    print("-" * 100)
    print(f"{'Model':<35} {'N':>5} {'ij0 mean':>10} {'ij1 mean':>10} {'Diff (s)':>10} {'Diff %':>10} {'ij1 faster':>12}")
    print("-" * 100)
    
    all_model_results = {}
    
    for model in models:
        result = compare_settings_speed(timing_data, model, "ij0_oracle1", "ij1_oracle1", "all")
        if result["n"] == 0:
            continue
        
        all_model_results[model] = result
        
        faster_pct = result["b_faster_count"] / result["n"] * 100
        
        print(f"{model:<35} {result['n']:>5} {result['mean_time_a']:>9.1f}s {result['mean_time_b']:>9.1f}s "
              f"{result['mean_diff_s']:>+9.1f}s {result['mean_pct_diff']:>+9.1f}% {faster_pct:>10.0f}%")
    
    print("-" * 100)
    
    # Analysis for tasks where BOTH passed
    print()
    print("=" * 100)
    print("SPEED ANALYSIS: Only tasks where BOTH ij0 and ij1 PASSED (with statistical significance)")
    print("=" * 100)
    print()
    
    print("-" * 130)
    print(f"{'Model':<35} {'N':>5} {'ij0 mean':>10} {'ij1 mean':>10} {'Diff (s)':>10} {'95% CI':>20} {'p-value':>10} {'Sig?':>8}")
    print("-" * 130)
    
    both_passed_results = {}
    
    for model in models:
        result = compare_settings_speed(timing_data, model, "ij0_oracle1", "ij1_oracle1", "both_passed")
        if result["n"] == 0:
            continue
        
        both_passed_results[model] = result
        t_test = result.get("t_test", {})
        
        if t_test:
            ci_str = f"[{t_test.get('ci_95_low', 0):+.1f}, {t_test.get('ci_95_high', 0):+.1f}]"
            p_value = t_test.get("p_value", 1.0)
            sig_marker = "**" if t_test.get("significant_01") else ("*" if t_test.get("significant_05") else "")
        else:
            ci_str = "N/A"
            p_value = 1.0
            sig_marker = ""
        
        print(f"{model:<35} {result['n']:>5} {result['mean_time_a']:>9.1f}s {result['mean_time_b']:>9.1f}s "
              f"{result['mean_diff_s']:>+9.1f}s {ci_str:>20} {p_value:>10.4f} {sig_marker:>8}")
    
    print("-" * 130)
    print()
    print("* = p < 0.05, ** = p < 0.01")
    print("Positive diff = ij1 (IntelliJ guidance) is SLOWER")
    print("Negative diff = ij1 (IntelliJ guidance) is FASTER")
    
    # Summary of significant speed differences
    print()
    print("=" * 100)
    print("STATISTICALLY SIGNIFICANT SPEED DIFFERENCES (p < 0.05)")
    print("=" * 100)
    
    sig_results = []
    for model, result in both_passed_results.items():
        t_test = result.get("t_test", {})
        if t_test and t_test.get("significant_05"):
            direction = "FASTER" if result["mean_diff_s"] < 0 else "SLOWER"
            sig_results.append((model, result, direction, t_test))
    
    if sig_results:
        for model, result, direction, t_test in sig_results:
            diff = abs(result["mean_diff_s"])
            p_val = t_test["p_value"]
            sig_level = "p < 0.01" if t_test.get("significant_01") else "p < 0.05"
            print(f"  {model}: IntelliJ guidance is {direction} by {diff:.1f}s ({sig_level})")
    else:
        print("  No statistically significant speed differences found.")
    
    print("-" * 100)
    
    # Detailed per-model breakdown
    print()
    print("=" * 100)
    print("DETAILED PER-TASK ANALYSIS")
    print("=" * 100)
    
    for model in models:
        result = all_model_results.get(model)
        if not result or result["n"] == 0:
            continue
        
        print(f"\n### {model}")
        print(f"Tasks compared: {result['n']}")
        print(f"Mean: ij0={result['mean_time_a']:.1f}s, ij1={result['mean_time_b']:.1f}s (diff: {result['mean_diff_s']:+.1f}s, {result['mean_pct_diff']:+.1f}%)")
        print(f"Median: ij0={result['median_time_a']:.1f}s, ij1={result['median_time_b']:.1f}s (diff: {result['median_diff_s']:+.1f}s, {result['median_pct_diff']:+.1f}%)")
        print(f"ij1 faster on {result['b_faster_count']}/{result['n']} tasks ({result['b_faster_count']/result['n']*100:.0f}%)")
        
        # Show biggest speedups and slowdowns
        comparisons = sorted(result["comparisons"], key=lambda x: x["diff_s"])
        
        print(f"\nBiggest speedups (ij1 faster than ij0):")
        for c in comparisons[:3]:
            if c["diff_s"] >= 0:
                break
            status = "both passed" if c["a_passed"] and c["b_passed"] else f"ij0={'P' if c['a_passed'] else 'F'}, ij1={'P' if c['b_passed'] else 'F'}"
            print(f"  {c['task_id']}: {c['time_a']:.1f}s → {c['time_b']:.1f}s ({c['diff_s']:+.1f}s, {c['pct_diff']:+.1f}%) [{status}]")
        
        print(f"\nBiggest slowdowns (ij1 slower than ij0):")
        for c in reversed(comparisons[-3:]):
            if c["diff_s"] <= 0:
                break
            status = "both passed" if c["a_passed"] and c["b_passed"] else f"ij0={'P' if c['a_passed'] else 'F'}, ij1={'P' if c['b_passed'] else 'F'}"
            print(f"  {c['task_id']}: {c['time_a']:.1f}s → {c['time_b']:.1f}s ({c['diff_s']:+.1f}s, {c['pct_diff']:+.1f}%) [{status}]")
    
    # Overall summary
    print()
    print("=" * 100)
    print("OVERALL SUMMARY")
    print("=" * 100)
    
    all_diffs = []
    all_pct_diffs = []
    total_tasks = 0
    ij1_faster_total = 0
    
    for model, result in all_model_results.items():
        if result["n"] > 0:
            all_diffs.extend([c["diff_s"] for c in result["comparisons"]])
            all_pct_diffs.extend([c["pct_diff"] for c in result["comparisons"]])
            total_tasks += result["n"]
            ij1_faster_total += result["b_faster_count"]
    
    if all_diffs:
        print(f"\nAcross all models and tasks (n={total_tasks}):")
        print(f"  Mean time difference: {statistics.mean(all_diffs):+.1f}s ({statistics.mean(all_pct_diffs):+.1f}%)")
        print(f"  Median time difference: {statistics.median(all_diffs):+.1f}s ({statistics.median(all_pct_diffs):+.1f}%)")
        print(f"  ij1 (with IntelliJ guidance) was faster on {ij1_faster_total}/{total_tasks} tasks ({ij1_faster_total/total_tasks*100:.0f}%)")
        
        if statistics.mean(all_diffs) > 0:
            print(f"\n  → On average, IntelliJ guidance (ij1) is SLOWER by {abs(statistics.mean(all_diffs)):.1f}s ({abs(statistics.mean(all_pct_diffs)):.1f}%)")
        else:
            print(f"\n  → On average, IntelliJ guidance (ij1) is FASTER by {abs(statistics.mean(all_diffs)):.1f}s ({abs(statistics.mean(all_pct_diffs)):.1f}%)")


if __name__ == "__main__":
    main()
