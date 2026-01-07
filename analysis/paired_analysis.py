#!/usr/bin/env python3
"""
Paired statistical analysis of model performance on Kotlin-bench.

Uses McNemar's test to determine if model differences are statistically significant
when comparing on the same set of tasks.
"""

import json
from pathlib import Path
from collections import defaultdict
import math

def chi2_cdf_approx(x: float, df: int = 1) -> float:
    """Approximate chi-squared CDF using the Wilson-Hilferty transformation."""
    if x <= 0:
        return 0.0
    if df == 1:
        # For df=1, use normal approximation
        z = math.sqrt(x)
        # Standard normal CDF approximation
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return 0.5  # fallback

def mcnemar_test(b: int, c: int) -> dict:
    """
    McNemar's test for paired binary outcomes.
    
    b = cases where Model A passes, Model B fails
    c = cases where Model A fails, Model B passes
    
    Returns p-value and whether the difference is significant.
    """
    if b + c == 0:
        return {"statistic": 0, "p_value": 1.0, "significant_05": False, "significant_01": False, "b": b, "c": c, "disagreements": 0}
    
    # McNemar's chi-squared statistic (with continuity correction)
    statistic = (abs(b - c) - 1) ** 2 / (b + c) if (b + c) > 0 else 0
    
    # p-value from chi-squared distribution with 1 df
    p_value = 1 - chi2_cdf_approx(statistic, df=1) if statistic > 0 else 1.0
    
    return {
        "statistic": round(statistic, 3),
        "p_value": round(p_value, 4),
        "significant_05": p_value < 0.05,
        "significant_01": p_value < 0.01,
        "b": b,  # Model A wins
        "c": c,  # Model B wins
        "disagreements": b + c,
    }


def load_report(report_path: Path) -> dict:
    with open(report_path) as f:
        return json.load(f)


def extract_model_task_results(report: dict, settings_filter: str = None) -> dict:
    """
    Extract {model: {task_id: passed}} from report.
    
    If settings_filter provided (e.g., "ij1_oracle1"), only include those results.
    """
    model_results = defaultdict(dict)
    
    for task_id, task_data in report.get("results", {}).items():
        for model, results_list in task_data.items():
            for result in results_list:
                settings = result.get("settings", {})
                settings_id = f"ij{int(settings.get('intellij_guidance', True))}_oracle{int(settings.get('oracle_files', False))}"
                
                if settings_filter and settings_id != settings_filter:
                    continue
                
                passed = result.get("test_passed")
                if passed is not None:
                    model_results[model][task_id] = passed
    
    return dict(model_results)


def compare_models(results_a: dict, results_b: dict) -> dict:
    """
    Compare two models on their shared tasks.
    
    Returns the 2x2 contingency table and McNemar's test results.
    """
    # Find shared tasks
    shared_tasks = set(results_a.keys()) & set(results_b.keys())
    
    # Build contingency table
    both_pass = 0
    a_wins = 0  # A passes, B fails
    b_wins = 0  # B passes, A fails
    both_fail = 0
    
    for task in shared_tasks:
        a_passed = results_a[task]
        b_passed = results_b[task]
        
        if a_passed and b_passed:
            both_pass += 1
        elif a_passed and not b_passed:
            a_wins += 1
        elif not a_passed and b_passed:
            b_wins += 1
        else:
            both_fail += 1
    
    test_result = mcnemar_test(a_wins, b_wins)
    
    return {
        "shared_tasks": len(shared_tasks),
        "both_pass": both_pass,
        "a_wins": a_wins,
        "b_wins": b_wins,
        "both_fail": both_fail,
        "a_pass_rate": (both_pass + a_wins) / len(shared_tasks) if shared_tasks else 0,
        "b_pass_rate": (both_pass + b_wins) / len(shared_tasks) if shared_tasks else 0,
        "mcnemar": test_result,
    }


def main():
    report_path = Path(__file__).parent.parent / "outputs" / "report.json"
    
    if not report_path.exists():
        print(f"Report not found: {report_path}")
        return
    
    report = load_report(report_path)
    
    # Get available settings
    settings_variants = report.get("settings_variants", [])
    print(f"Available settings: {settings_variants}")
    print()
    
    for settings_id in settings_variants:
        print("=" * 80)
        print(f"ANALYSIS FOR: {settings_id}")
        print("=" * 80)
        
        model_results = extract_model_task_results(report, settings_id)
        models = sorted(model_results.keys())
        
        print(f"\nModels with data: {len(models)}")
        for m in models:
            n_tasks = len(model_results[m])
            n_passed = sum(model_results[m].values())
            print(f"  {m}: {n_passed}/{n_tasks} ({100*n_passed/n_tasks:.1f}%)")
        
        print("\n" + "-" * 80)
        print("PAIRWISE COMPARISONS (McNemar's Test)")
        print("-" * 80)
        
        # Track significant results
        significant_pairs = []
        
        # Compare all pairs
        for i, model_a in enumerate(models):
            for model_b in models[i+1:]:
                comparison = compare_models(
                    model_results[model_a],
                    model_results[model_b]
                )
                
                mcnemar = comparison["mcnemar"]
                
                # Determine winner
                if comparison["a_wins"] > comparison["b_wins"]:
                    winner = model_a
                    margin = comparison["a_wins"] - comparison["b_wins"]
                elif comparison["b_wins"] > comparison["a_wins"]:
                    winner = model_b
                    margin = comparison["b_wins"] - comparison["a_wins"]
                else:
                    winner = "TIE"
                    margin = 0
                
                sig_marker = ""
                loser = model_b if winner == model_a else model_a
                if mcnemar["significant_01"]:
                    sig_marker = " **"
                    significant_pairs.append((model_a, model_b, winner, mcnemar["p_value"], loser))
                elif mcnemar["significant_05"]:
                    sig_marker = " *"
                    significant_pairs.append((model_a, model_b, winner, mcnemar["p_value"], loser))
                
                print(f"\n{model_a} vs {model_b}:")
                print(f"  Shared tasks: {comparison['shared_tasks']}")
                print(f"  Both pass: {comparison['both_pass']}, Both fail: {comparison['both_fail']}")
                print(f"  {model_a} wins: {comparison['a_wins']}, {model_b} wins: {comparison['b_wins']}")
                print(f"  Disagreements: {mcnemar['disagreements']}")
                print(f"  McNemar p-value: {mcnemar['p_value']}{sig_marker}")
                if winner != "TIE":
                    print(f"  → {winner} better by {margin} tasks")
        
        # Summary of significant results
        print("\n" + "=" * 80)
        print("SIGNIFICANT DIFFERENCES (p < 0.05)")
        print("=" * 80)
        
        if significant_pairs:
            for model_a, model_b, winner, p_value, loser in significant_pairs:
                sig_level = "**" if p_value < 0.01 else "*"
                print(f"  {winner} > {loser} (p={p_value}) {sig_level}")
        else:
            print("  No statistically significant differences found.")
            print("  (This is expected with ~100 tasks and similar model performance)")
        
        print()


if __name__ == "__main__":
    main()
