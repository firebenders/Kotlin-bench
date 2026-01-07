#!/usr/bin/env python3
"""
Analyze the time difference between read_lints tool calls vs gradle test commands.

This shows the efficiency gain from using IDE tools vs running actual builds/tests.
"""

import json
from pathlib import Path
from collections import defaultdict
import statistics
import re


def load_agent_log(log_path: Path) -> dict:
    """Load agent_log.json."""
    try:
        with open(log_path) as f:
            return json.load(f)
    except Exception as e:
        return {"_load_error": str(e)}


def extract_tool_timings(log_data: dict) -> dict:
    """
    Extract timing data for read_lints and gradle test commands.
    
    Returns dict with lists of timings for each tool type.
    """
    read_lints_times = []
    gradle_test_times = []
    gradle_build_times = []
    other_terminal_times = []
    
    iterations = log_data.get("iterations", [])
    
    for iteration in iterations:
        tool_calls = iteration.get("tool_calls", [])
        
        for tool_call in tool_calls:
            # Handle both old format (function.name) and new format (tool_name)
            tool_name = tool_call.get("tool_name")
            if not tool_name and "function" in tool_call:
                tool_name = tool_call.get("function", {}).get("name", "")
            
            duration_ms = tool_call.get("duration_ms")
            
            # Get arguments/input - handle both formats
            input_json = tool_call.get("input_json")
            if not input_json and "function" in tool_call:
                input_json = tool_call.get("function", {}).get("arguments", "")
            if not input_json:
                input_json = ""
            
            if duration_ms is None or not tool_name:
                continue
            
            if tool_name == "read_lints":
                read_lints_times.append({
                    "duration_ms": duration_ms,
                    "input": input_json,
                })
            elif tool_name == "run_terminal_cmd":
                # Check if it's a gradle command
                input_lower = input_json.lower()
                if "gradle" in input_lower or "gradlew" in input_lower:
                    if "test" in input_lower:
                        gradle_test_times.append({
                            "duration_ms": duration_ms,
                            "input": input_json,
                        })
                    elif "compile" in input_lower or "build" in input_lower or "assemble" in input_lower:
                        gradle_build_times.append({
                            "duration_ms": duration_ms,
                            "input": input_json,
                        })
                else:
                    other_terminal_times.append({
                        "duration_ms": duration_ms,
                        "input": input_json,
                    })
    
    return {
        "read_lints": read_lints_times,
        "gradle_test": gradle_test_times,
        "gradle_build": gradle_build_times,
        "other_terminal": other_terminal_times,
    }


def scan_all_logs(data_dir: Path) -> dict:
    """
    Scan all agent_log.json files and aggregate tool timing data.
    
    Returns: {settings_id: {model: {tool_type: [timings]}}}
    """
    results = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    files_scanned = 0
    files_with_data = 0
    
    # Walk through data directory
    for task_dir in data_dir.iterdir():
        if not task_dir.is_dir():
            continue
        
        for model_dir in task_dir.iterdir():
            if not model_dir.is_dir():
                continue
            
            model = model_dir.name
            
            for settings_dir in model_dir.iterdir():
                if not settings_dir.is_dir():
                    continue
                
                settings_id = settings_dir.name
                agent_log = settings_dir / "agent_log.json"
                
                if agent_log.exists():
                    files_scanned += 1
                    log_data = load_agent_log(agent_log)
                    # Check for actual error (not just None value)
                    if not log_data.get("_load_error"):
                        timings = extract_tool_timings(log_data)
                        
                        has_data = False
                        for tool_type, timing_list in timings.items():
                            if timing_list:
                                has_data = True
                                # Debug first few
                                if files_with_data < 3:
                                    print(f"  Found {len(timing_list)} {tool_type} in {settings_id}/{model}")
                            results[settings_id][model][tool_type].extend(timing_list)
                        
                        if has_data:
                            files_with_data += 1
    
    print(f"Scanned {files_scanned} agent_log.json files, {files_with_data} had tool timing data")
    print(f"Settings found: {list(results.keys())}")
    for s in results:
        print(f"  {s}: {list(results[s].keys())[:3]}... ({len(results[s])} models)")
    return dict(results)


def main():
    data_dir = Path(__file__).parent.parent / "outputs" / "data"
    
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return
    
    print("Scanning all agent logs...")
    results = scan_all_logs(data_dir)
    
    print("=" * 100)
    print("TOOL TIMING ANALYSIS: read_lints vs Gradle Commands")
    print("=" * 100)
    print()
    
    for settings_id in sorted(results.keys()):
        print(f"\n{'='*100}")
        print(f"SETTINGS: {settings_id}")
        print("=" * 100)
        
        settings_data = results[settings_id]
        
        # Aggregate across all models for this setting
        all_read_lints = []
        all_gradle_test = []
        all_gradle_build = []
        
        for model in sorted(settings_data.keys()):
            model_data = settings_data[model]
            all_read_lints.extend(model_data.get("read_lints", []))
            all_gradle_test.extend(model_data.get("gradle_test", []))
            all_gradle_build.extend(model_data.get("gradle_build", []))
        
        # Print summary
        print(f"\n### AGGREGATE SUMMARY (all models)")
        print("-" * 80)
        
        if all_read_lints:
            times = [t["duration_ms"] for t in all_read_lints]
            print(f"read_lints:")
            print(f"  Count: {len(times)}")
            print(f"  Mean: {statistics.mean(times):.0f}ms")
            print(f"  Median: {statistics.median(times):.0f}ms")
            print(f"  Min: {min(times):.0f}ms")
            print(f"  Max: {max(times):.0f}ms")
            if len(times) > 1:
                print(f"  Stdev: {statistics.stdev(times):.0f}ms")
        else:
            print(f"read_lints: No calls found")
        
        print()
        
        if all_gradle_test:
            times = [t["duration_ms"] for t in all_gradle_test]
            print(f"Gradle Test Commands (run_terminal_cmd with gradle test):")
            print(f"  Count: {len(times)}")
            print(f"  Mean: {statistics.mean(times):.0f}ms ({statistics.mean(times)/1000:.1f}s)")
            print(f"  Median: {statistics.median(times):.0f}ms ({statistics.median(times)/1000:.1f}s)")
            print(f"  Min: {min(times):.0f}ms ({min(times)/1000:.1f}s)")
            print(f"  Max: {max(times):.0f}ms ({max(times)/1000:.1f}s)")
            if len(times) > 1:
                print(f"  Stdev: {statistics.stdev(times):.0f}ms")
        else:
            print(f"Gradle Test Commands: No calls found")
        
        print()
        
        if all_gradle_build:
            times = [t["duration_ms"] for t in all_gradle_build]
            print(f"Gradle Build Commands (run_terminal_cmd with gradle, no test):")
            print(f"  Count: {len(times)}")
            print(f"  Mean: {statistics.mean(times):.0f}ms ({statistics.mean(times)/1000:.1f}s)")
            print(f"  Median: {statistics.median(times):.0f}ms ({statistics.median(times)/1000:.1f}s)")
            print(f"  Min: {min(times):.0f}ms ({min(times)/1000:.1f}s)")
            print(f"  Max: {max(times):.0f}ms ({max(times)/1000:.1f}s)")
        else:
            print(f"Gradle Build Commands: No calls found")
        
        # Calculate speedup
        if all_read_lints and all_gradle_test:
            lint_mean = statistics.mean([t["duration_ms"] for t in all_read_lints])
            gradle_mean = statistics.mean([t["duration_ms"] for t in all_gradle_test])
            speedup = gradle_mean / lint_mean if lint_mean > 0 else 0
            time_saved = gradle_mean - lint_mean
            
            print()
            print("-" * 80)
            print("### TIME COMPARISON: read_lints vs Gradle Tests")
            print("-" * 80)
            print(f"  read_lints mean: {lint_mean:.0f}ms ({lint_mean/1000:.2f}s)")
            print(f"  Gradle test mean: {gradle_mean:.0f}ms ({gradle_mean/1000:.1f}s)")
            print(f"  Speedup: {speedup:.0f}x faster")
            print(f"  Time saved per call: {time_saved:.0f}ms ({time_saved/1000:.1f}s)")
        
        # Per-model breakdown
        print()
        print("-" * 80)
        print("### PER-MODEL BREAKDOWN")
        print("-" * 80)
        print(f"{'Model':<40} {'read_lints':<20} {'Gradle Tests':<25} {'Speedup':<15}")
        print(f"{'':40} {'(count, mean ms)':<20} {'(count, mean s)':<25} {'(x faster)':<15}")
        print("-" * 100)
        
        for model in sorted(settings_data.keys()):
            model_data = settings_data[model]
            
            lint_calls = model_data.get("read_lints", [])
            gradle_calls = model_data.get("gradle_test", [])
            
            if lint_calls:
                lint_str = f"{len(lint_calls)}, {statistics.mean([t['duration_ms'] for t in lint_calls]):.0f}ms"
            else:
                lint_str = "0 calls"
            
            if gradle_calls:
                gradle_mean = statistics.mean([t['duration_ms'] for t in gradle_calls])
                gradle_str = f"{len(gradle_calls)}, {gradle_mean/1000:.1f}s"
            else:
                gradle_str = "0 calls"
            
            if lint_calls and gradle_calls:
                lint_mean = statistics.mean([t['duration_ms'] for t in lint_calls])
                gradle_mean = statistics.mean([t['duration_ms'] for t in gradle_calls])
                speedup = gradle_mean / lint_mean if lint_mean > 0 else 0
                speedup_str = f"{speedup:.0f}x"
            else:
                speedup_str = "-"
            
            print(f"{model:<40} {lint_str:<20} {gradle_str:<25} {speedup_str:<15}")
    
    # Cross-setting comparison: ij1 read_lints vs ij0 gradle tests
    print()
    print("=" * 100)
    print("KEY COMPARISON: ij1 read_lints vs ij0 gradle test commands")
    print("=" * 100)
    print()
    print("This compares the IDE linting tool (available with IntelliJ guidance)")
    print("vs the gradle test fallback (used without IntelliJ guidance)")
    print()
    
    ij1_read_lints = []
    ij0_gradle_tests = []
    
    if "ij1_oracle1" in results:
        for model, model_data in results["ij1_oracle1"].items():
            ij1_read_lints.extend(model_data.get("read_lints", []))
    
    if "ij0_oracle1" in results:
        for model, model_data in results["ij0_oracle1"].items():
            ij0_gradle_tests.extend(model_data.get("gradle_test", []))
    
    if ij1_read_lints and ij0_gradle_tests:
        lint_times = [t["duration_ms"] for t in ij1_read_lints]
        gradle_times = [t["duration_ms"] for t in ij0_gradle_tests]
        
        lint_mean = statistics.mean(lint_times)
        gradle_mean = statistics.mean(gradle_times)
        speedup = gradle_mean / lint_mean if lint_mean > 0 else 0
        
        print(f"ij1 read_lints (with IntelliJ tools):")
        print(f"  Count: {len(lint_times)}")
        print(f"  Mean: {lint_mean:.0f}ms ({lint_mean/1000:.2f}s)")
        print(f"  Median: {statistics.median(lint_times):.0f}ms ({statistics.median(lint_times)/1000:.2f}s)")
        print()
        print(f"ij0 gradle test (without IntelliJ tools):")
        print(f"  Count: {len(gradle_times)}")
        print(f"  Mean: {gradle_mean:.0f}ms ({gradle_mean/1000:.1f}s)")
        print(f"  Median: {statistics.median(gradle_times):.0f}ms ({statistics.median(gradle_times)/1000:.1f}s)")
        print()
        print("-" * 80)
        print(f"  **SPEEDUP: {speedup:.0f}x faster using read_lints vs gradle test**")
        print(f"  **TIME SAVED PER CALL: {(gradle_mean - lint_mean)/1000:.1f}s**")
        print("-" * 80)
        
        # Per-model cross-comparison
        print()
        print("Per-Model Comparison:")
        print("-" * 100)
        print(f"{'Model':<35} {'ij1 read_lints':<25} {'ij0 gradle test':<25} {'Speedup':<15}")
        print("-" * 100)
        
        all_models = set()
        if "ij1_oracle1" in results:
            all_models.update(results["ij1_oracle1"].keys())
        if "ij0_oracle1" in results:
            all_models.update(results["ij0_oracle1"].keys())
        
        for model in sorted(all_models):
            ij1_data = results.get("ij1_oracle1", {}).get(model, {})
            ij0_data = results.get("ij0_oracle1", {}).get(model, {})
            
            lint_calls = ij1_data.get("read_lints", [])
            gradle_calls = ij0_data.get("gradle_test", [])
            
            if lint_calls:
                lint_mean_m = statistics.mean([t['duration_ms'] for t in lint_calls])
                lint_str = f"{len(lint_calls)}, {lint_mean_m/1000:.2f}s"
            else:
                lint_str = "0 calls"
                lint_mean_m = None
            
            if gradle_calls:
                gradle_mean_m = statistics.mean([t['duration_ms'] for t in gradle_calls])
                gradle_str = f"{len(gradle_calls)}, {gradle_mean_m/1000:.1f}s"
            else:
                gradle_str = "0 calls"
                gradle_mean_m = None
            
            if lint_mean_m and gradle_mean_m:
                speedup_m = gradle_mean_m / lint_mean_m
                speedup_str = f"{speedup_m:.0f}x"
            else:
                speedup_str = "-"
            
            print(f"{model:<35} {lint_str:<25} {gradle_str:<25} {speedup_str:<15}")
        
        print("-" * 100)
    else:
        print("Insufficient data for cross-setting comparison")
    
    # Overall summary
    print()
    print("=" * 100)
    print("OVERALL SUMMARY (all settings combined)")
    print("=" * 100)
    
    total_read_lints = []
    total_gradle_tests = []
    
    for settings_id, settings_data in results.items():
        for model, model_data in settings_data.items():
            total_read_lints.extend(model_data.get("read_lints", []))
            total_gradle_tests.extend(model_data.get("gradle_test", []))
    
    if total_read_lints and total_gradle_tests:
        lint_mean = statistics.mean([t["duration_ms"] for t in total_read_lints])
        gradle_mean = statistics.mean([t["duration_ms"] for t in total_gradle_tests])
        speedup = gradle_mean / lint_mean if lint_mean > 0 else 0
        
        print(f"\nAcross all settings and models:")
        print(f"  Total read_lints calls: {len(total_read_lints)}")
        print(f"  Total gradle test calls: {len(total_gradle_tests)}")
        print(f"  read_lints mean: {lint_mean:.0f}ms ({lint_mean/1000:.2f}s)")
        print(f"  Gradle test mean: {gradle_mean:.0f}ms ({gradle_mean/1000:.1f}s)")
        print(f"  **Speedup: {speedup:.0f}x faster using read_lints**")
        print(f"  **Time saved per check: {(gradle_mean - lint_mean)/1000:.1f}s**")
        
        # Estimate total time saved
        total_lint_time = sum(t["duration_ms"] for t in total_read_lints)
        hypothetical_gradle_time = len(total_read_lints) * gradle_mean
        time_saved = hypothetical_gradle_time - total_lint_time
        
        print(f"\n  If all read_lints calls had been gradle tests instead:")
        print(f"    Actual time spent on read_lints: {total_lint_time/1000/60:.1f} minutes")
        print(f"    Hypothetical time with gradle: {hypothetical_gradle_time/1000/60:.1f} minutes")
        print(f"    **Time saved: {time_saved/1000/60:.1f} minutes**")


if __name__ == "__main__":
    main()
