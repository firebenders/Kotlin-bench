# Model Support - Kotlin-bench

This document describes the models supported in the Kotlin-bench evaluation system and their pricing configurations.

## Overview

The Kotlin-bench evaluation system accepts **any model identifier string**. The model name is passed directly to the Firebender agent server, which handles the LLM API calls. You don't need to modify code to add a new model - just use its identifier in the command line.

## Supported Models

### OpenAI GPT Models

| Model | Display Name | Input Price | Cached Input | Output Price | Context | Max Output | Notes |
|-------|--------------|-------------|--------------|--------------|---------|------------|-------|
| `gpt-5.2-codex` | GPT-5.2-Codex | $1.75 | $0.175 | $14.00 | 400K | 128K | Optimized for agentic coding tasks |
| `gpt-5.1-codex` | GPT-5.1-Codex | $1.25 | $0.125 | $10.00 | 200K | 100K | Previous generation |
| `gpt-5.2` | GPT-5.2 | $1.75 | $0.175 | $14.00 | 400K | 128K | General purpose |
| `gpt-4.1` | GPT-4.1 | $2.50 | $0.25 | $10.00 | 128K | 16K | Standard GPT-4 |

*Prices are per 1M tokens*

### Anthropic Claude Models

| Model | Display Name | Input Price | Cached Input | Output Price | Context | Max Output | Notes |
|-------|--------------|-------------|--------------|--------------|---------|------------|-------|
| `claude-opus-4-5` | Opus 4.5 | $5.00 | $0.50 | $25.00 | 200K | 16K | Most capable |
| `claude-sonnet-4-20250514` | Sonnet 4 | $3.00 | $0.30 | $15.00 | 200K | 16K | Balanced |
| `claude-sonnet-4-5-20250929` | Sonnet 4.5 | $3.00 | $0.30 | $15.00 | 200K | 16K | Latest Sonnet |
| `claude-3.7-sonnet` | Sonnet 3.7 | $3.00 | $0.30 | $15.00 | 200K | 16K | Previous gen |
| `claude-3.5-sonnet` | Sonnet 3.5 | $3.00 | $0.30 | $15.00 | 200K | 8K | Previous gen |

*Prices are per 1M tokens*

### Google Gemini Models

| Model | Display Name | Input Price | Cached Input | Output Price | Context | Max Output | Notes |
|-------|--------------|-------------|--------------|--------------|---------|------------|-------|
| `gemini-3-pro-preview` | Gemini Pro 3 | $2.00 | $0.20 | $12.00 | 2M | 8K | Most capable |
| `gemini-3-flash-preview` | Gemini Flash 3 | $0.50 | $0.05 | $3.00 | 1M | 8K | Fast & economical |
| `gemini-2.5-pro` | Gemini Pro 2.5 | $1.25 | $0.125 | $5.00 | 1M | 8K | Previous gen |

*Prices are per 1M tokens*

### Other Models

| Model | Display Name | Input Price | Cached Input | Output Price | Notes |
|-------|--------------|-------------|--------------|--------------|-------|
| `zai-glm-4.7` | GLM-4.7 | $0.60 | $0.30 | $2.20 | Chinese language model |
| `zai-glm-4.7-fp8` | GLM-4.7-FP8 | $0.60 | $0.30 | $2.20 | Quantized version |

*Prices are per 1M tokens*

## Usage Examples

### Running with GPT-5.2-Codex

```bash
# Single task with GPT-5.2-Codex
modal run agent-bench/run_eval.py \
  --task-id ankidroid__Anki-Android-16395 \
  --model gpt-5.2-codex

# All tasks for a specific repository
modal run agent-bench/run_eval.py \
  --all-tasks \
  --repo anki \
  --model gpt-5.2-codex

# Multiple models in parallel
modal run agent-bench/run_eval.py \
  --all-tasks \
  --models gpt-5.2-codex,gpt-5.1-codex,claude-opus-4-5
```

### Cost Analysis

After running evaluations, you can analyze costs:

```bash
# Overall cost comparison
python analysis/cost_comparison.py

# Comprehensive analysis including costs
python analysis/analyze_results.py
```

## Adding New Models

To add a new model to the cost analysis scripts:

1. **For basic usage**: No code changes needed! Just use the model identifier
2. **For cost analysis**: Add pricing to `MODEL_CONFIG` in:
   - `analysis/cost_comparison.py`
   - `analysis/analyze_results.py`

Example:

```python
"your-model-name": {
    "display_name": "Your Model Display Name",
    "input_price": 1.50,           # $ per 1M tokens
    "cached_input_price": 0.15,    # $ per 1M cached tokens
    "output_price": 10.00,         # $ per 1M tokens
},
```

## Model Selection Considerations

### For Research & Benchmarking

- **GPT-5.2-Codex**: Best for long-horizon agentic tasks, large context window
- **Claude Opus 4.5**: Strong reasoning, good for complex debugging
- **Gemini Pro 3**: Good balance of capability and cost

### For Cost Optimization

- **Gemini Flash 3**: Most economical, good for simple tasks
- **GPT-5.1-Codex**: Previous gen, lower cost
- **Claude Sonnet models**: Mid-tier pricing with good performance

### For Maximum Performance

- **GPT-5.2-Codex**: Latest OpenAI coding model
- **Claude Opus 4.5**: Anthropic's most capable model
- **Gemini Pro 3**: Google's flagship model

## Pricing Notes

1. **Cached Input**: Most models support prompt caching, reducing costs for repeated context
2. **Token Estimation**: Cost scripts estimate ~4 characters per token
3. **Cache Rate**: Estimated at 85% for multi-turn conversations
4. **Pricing Updates**: Check provider documentation for current pricing

## Configuration Files

Model configurations are maintained in:

- **Evaluation**: `agent-bench/run_eval.py` (accepts any model string)
- **Cost Analysis**: `analysis/cost_comparison.py` (pricing data)
- **Comprehensive Analysis**: `analysis/analyze_results.py` (pricing + display names)
- **Documentation**: This file (`MODEL_SUPPORT.md`)

## Model Availability

All models listed are configured for cost analysis. Actual model availability depends on:

1. Your Firebender configuration
2. API keys and access
3. Provider availability

The evaluation system will pass any model identifier to Firebender - it's your responsibility to ensure the model is accessible.
