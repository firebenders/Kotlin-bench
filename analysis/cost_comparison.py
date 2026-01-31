#!/usr/bin/env python3
import json
import os
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple
import statistics

# Model display names and pricing (per 1M tokens)
MODEL_CONFIG = {
    "claude-opus-4-5": {
        "display_name": "Opus 4.5",
        "input_price": 5.00,
        "cached_input_price": 0.50,
        "output_price": 25.00,
    },
    "claude-sonnet-4-20250514": {
        "display_name": "Sonnet 4",
        "input_price": 3.00,
        "cached_input_price": 0.30,
        "output_price": 15.00,
    },
    "claude-sonnet-4-5-20250929": {
        "display_name": "Sonnet 4.5",
        "input_price": 3.00,
        "cached_input_price": 0.30,
        "output_price": 15.00,
    },
    "gemini-3-flash-preview": {
        "display_name": "Gemini Flash 3",
        "input_price": 0.50,
        "cached_input_price": 0.05,
        "output_price": 3.00,
    },
    "gemini-3-pro-preview": {
        "display_name": "Gemini Pro 3",
        "input_price": 2.00,
        "cached_input_price": 0.20,
        "output_price": 12.00,
    },
    "gpt-5.2": {
        "display_name": "GPT-5.2",
        "input_price": 1.75,
        "cached_input_price": 0.175,
        "output_price": 14.00,
    },
    "gpt-5.2-codex": {
        "display_name": "GPT-5.2-Codex",
        "input_price": 1.75,
        "cached_input_price": 0.175,
        "output_price": 14.00,
    },
    "gpt-5.1-codex": {
        "display_name": "GPT-5.1-Codex",
        "input_price": 1.25,
        "cached_input_price": 0.125,
        "output_price": 10.00,
    },
    "gpt-4.1": {
        "display_name": "GPT-4.1",
        "input_price": 2.50,
        "cached_input_price": 0.25,
        "output_price": 10.00,
    },
    "zai-glm-4.7": {
        "display_name": "GLM-4.7",
        "input_price": 0.60,
        "cached_input_price": 0.30,
        "output_price": 2.20,
    },
    "zai-glm-4.7-fp8": {
        "display_name": "GLM-4.7-FP8",
        "input_price": 0.60,
        "cached_input_price": 0.30,
        "output_price": 2.20,
    },
}

def get_pricing(model: str) -> Tuple[float, float, float]:
    config = MODEL_CONFIG.get(model, {"input_price": 1.0, "cached_input_price": 0.25, "output_price": 5.0})
    return config["input_price"], config.get("cached_input_price", config["input_price"] * 0.25), config["output_price"]

def extract_text_from_content(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif block.get("type") == "thinking":
                    texts.append(block.get("thinking", ""))
            elif isinstance(block, str):
                texts.append(block)
        return " ".join(texts)
    return ""

def parse_agent_log(log_path: Path) -> dict:
    metrics = {
        "num_assistant_turns": 0,
        "total_input_chars": 0,
        "total_output_chars": 0,
        "success": True,
    }
    try:
        with open(log_path, 'r') as f:
            data = json.load(f)
        metrics["success"] = data.get("success", True)
        conversation = data.get("conversation_history", [])
        for msg in conversation:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                text = extract_text_from_content(content)
                metrics["total_input_chars"] += len(text)
            elif role == "assistant":
                metrics["num_assistant_turns"] += 1
                text = extract_text_from_content(content)
                metrics["total_output_chars"] += len(text)
                tool_calls = msg.get("tool_calls", [])
                for tc in tool_calls:
                    func = tc.get("function", {})
                    args = func.get("arguments", "")
                    if isinstance(args, str):
                        metrics["total_output_chars"] += len(args)
            elif role == "tool":
                tool_content = msg.get("content", "")
                if isinstance(tool_content, str):
                    metrics["total_input_chars"] += len(tool_content)
    except Exception:
        metrics["success"] = False
    return metrics

def estimate_cached_tokens(num_assistant_turns: int, total_input_tokens: int) -> Tuple[int, int]:
    if num_assistant_turns <= 1:
        return 0, total_input_tokens
    cache_rate = min(0.85, (num_assistant_turns - 1) / num_assistant_turns * 0.90)
    cached_tokens = int(total_input_tokens * cache_rate)
    uncached_tokens = total_input_tokens - cached_tokens
    return cached_tokens, uncached_tokens

def estimate_cost(model: str, uncached_input_tokens: int, cached_input_tokens: int, output_tokens: int) -> float:
    input_price, cached_input_price, output_price = get_pricing(model)
    uncached_input_cost = (uncached_input_tokens / 1_000_000) * input_price
    cached_input_cost = (cached_input_tokens / 1_000_000) * cached_input_price
    output_cost = (output_tokens / 1_000_000) * output_price
    return uncached_input_cost + cached_input_cost + output_cost

def main():
    data_dir = Path("outputs/data")
    comparison = defaultdict(lambda: {"ij0": [], "ij1": []})
    
    for task_dir in data_dir.iterdir():
        if not task_dir.is_dir(): continue
        for model_dir in task_dir.iterdir():
            if not model_dir.is_dir(): continue
            model = model_dir.name
            
            for setting in ["ij0_oracle1", "ij1_oracle1"]:
                log_path = model_dir / setting / "agent_log.json"
                test_res_path = model_dir / setting / "test_result.json"
                
                if log_path.exists():
                    log_data = parse_agent_log(log_path)
                    passed = False
                    if test_res_path.exists():
                        try:
                            with open(test_res_path) as f:
                                passed = json.load(f).get("passed", False)
                        except: pass
                    
                    input_tokens = log_data["total_input_chars"] // 4
                    output_tokens = log_data["total_output_chars"] // 4
                    cached, uncached = estimate_cached_tokens(log_data["num_assistant_turns"], input_tokens)
                    cost = estimate_cost(model, uncached, cached, output_tokens)
                    
                    comparison[model][setting[:3]].append({
                        "cost": cost,
                        "passed": passed,
                        "turns": log_data["num_assistant_turns"]
                    })

    print(f"{'Model':<30} | {'ij0 Cost':>10} | {'ij1 Cost':>10} | {'Diff %':>8} | {'ij0 Pass':>8} | {'ij1 Pass':>8}")
    print("-" * 95)
    
    for model in sorted(comparison.keys()):
        ij0_data = comparison[model]["ij0"]
        ij1_data = comparison[model]["ij1"]
        
        if not ij0_data or not ij1_data: continue
        
        avg_cost_ij0 = statistics.mean([x["cost"] for x in ij0_data])
        avg_cost_ij1 = statistics.mean([x["cost"] for x in ij1_data])
        pass_rate_ij0 = sum(1 for x in ij0_data if x["passed"]) / len(ij0_data)
        pass_rate_ij1 = sum(1 for x in ij1_data if x["passed"]) / len(ij1_data)
        
        diff_pct = (avg_cost_ij1 - avg_cost_ij0) / avg_cost_ij0 * 100 if avg_cost_ij0 > 0 else 0
        
        print(f"{model:<30} | ${avg_cost_ij0:>9.4f} | ${avg_cost_ij1:>9.4f} | {diff_pct:>+7.1f}% | {pass_rate_ij0:>7.1%} | {pass_rate_ij1:>7.1%}")

    # Paired analysis: only tasks where both exist
    print("\nPAIRED ANALYSIS (Tasks where BOTH ij0 and ij1 were run)")
    print(f"{'Model':<30} | {'N':>4} | {'ij0 Avg':>10} | {'ij1 Avg':>10} | {'Diff %':>8}")
    print("-" * 75)
    
    paired_comparison = defaultdict(list)
    for task_dir in data_dir.iterdir():
        if not task_dir.is_dir(): continue
        for model_dir in task_dir.iterdir():
            if not model_dir.is_dir(): continue
            model = model_dir.name
            
            ij0_log = model_dir / "ij0_oracle1" / "agent_log.json"
            ij1_log = model_dir / "ij1_oracle1" / "agent_log.json"
            
            if ij0_log.exists() and ij1_log.exists():
                costs = {}
                for s, p in [("ij0", ij0_log), ("ij1", ij1_log)]:
                    log_data = parse_agent_log(p)
                    input_tokens = log_data["total_input_chars"] // 4
                    output_tokens = log_data["total_output_chars"] // 4
                    cached, uncached = estimate_cached_tokens(log_data["num_assistant_turns"], input_tokens)
                    costs[s] = estimate_cost(model, uncached, cached, output_tokens)
                
                paired_comparison[model].append(costs)

    for model in sorted(paired_comparison.keys()):
        data = paired_comparison[model]
        if not data: continue
        avg_ij0 = statistics.mean([x["ij0"] for x in data])
        avg_ij1 = statistics.mean([x["ij1"] for x in data])
        diff_pct = (avg_ij1 - avg_ij0) / avg_ij0 * 100 if avg_ij0 > 0 else 0
        print(f"{model:<30} | {len(data):>4} | ${avg_ij0:>9.4f} | ${avg_ij1:>9.4f} | {diff_pct:>+7.1f}%")

    # Turn count analysis
    print("\nTURN COUNT ANALYSIS (Paired)")
    print(f"{'Model':<30} | {'ij0 Turns':>10} | {'ij1 Turns':>10} | {'Diff':>8}")
    print("-" * 65)
    
    paired_turns = defaultdict(list)
    for task_dir in data_dir.iterdir():
        if not task_dir.is_dir(): continue
        for model_dir in task_dir.iterdir():
            if not model_dir.is_dir(): continue
            model = model_dir.name
            ij0_log = model_dir / "ij0_oracle1" / "agent_log.json"
            ij1_log = model_dir / "ij1_oracle1" / "agent_log.json"
            if ij0_log.exists() and ij1_log.exists():
                turns = {}
                for s, p in [("ij0", ij0_log), ("ij1", ij1_log)]:
                    log_data = parse_agent_log(p)
                    turns[s] = log_data["num_assistant_turns"]
                paired_turns[model].append(turns)

    for model in sorted(paired_turns.keys()):
        data = paired_turns[model]
        avg_ij0 = statistics.mean([x["ij0"] for x in data])
        avg_ij1 = statistics.mean([x["ij1"] for x in data])
        diff = avg_ij1 - avg_ij0
        print(f"{model:<30} | {avg_ij0:>10.1f} | {avg_ij1:>10.1f} | {diff:>+8.1f}")

    # Input token analysis
    print("\nINPUT TOKEN ANALYSIS (Paired)")
    print(f"{'Model':<30} | {'ij0 Input':>10} | {'ij1 Input':>10} | {'Diff %':>8}")
    print("-" * 65)
    
    paired_tokens = defaultdict(list)
    for task_dir in data_dir.iterdir():
        if not task_dir.is_dir(): continue
        for model_dir in task_dir.iterdir():
            if not model_dir.is_dir(): continue
            model = model_dir.name
            ij0_log = model_dir / "ij0_oracle1" / "agent_log.json"
            ij1_log = model_dir / "ij1_oracle1" / "agent_log.json"
            if ij0_log.exists() and ij1_log.exists():
                tokens = {}
                for s, p in [("ij0", ij0_log), ("ij1", ij1_log)]:
                    log_data = parse_agent_log(p)
                    tokens[s] = log_data["total_input_chars"] // 4
                paired_tokens[model].append(tokens)

    for model in sorted(paired_tokens.keys()):
        data = paired_tokens[model]
        avg_ij0 = statistics.mean([x["ij0"] for x in data])
        avg_ij1 = statistics.mean([x["ij1"] for x in data])
        diff_pct = (avg_ij1 - avg_ij0) / avg_ij0 * 100 if avg_ij0 > 0 else 0
        print(f"{model:<30} | {avg_ij0:>10.0f} | {avg_ij1:>10.0f} | {diff_pct:>+7.1f}%")

if __name__ == "__main__":
    main()
