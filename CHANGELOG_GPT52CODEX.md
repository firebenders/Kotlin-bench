# GPT-5.2-Codex Support Addition - Changelog

## Summary

Added full support for **GPT-5.2-Codex** to the Kotlin-bench evaluation system, including cost analysis, documentation, and usage examples.

## Changes Made

### 1. Cost Analysis Scripts

#### `analysis/cost_comparison.py`
- ✅ Added GPT-5.2-Codex pricing configuration
- ✅ Added GPT-5.1-Codex pricing (for comparison)
- ✅ Added GPT-4.1 pricing (for comparison)

#### `analysis/analyze_results.py`
- ✅ Added GPT-5.2-Codex pricing configuration
- ✅ Added GPT-5.1-Codex pricing
- ✅ Added GPT-4.1 pricing

### 2. Documentation Updates

#### `agent-bench/run_eval.py`
- ✅ Updated usage examples to feature GPT-5.2-Codex
- ✅ Updated CLI help text with GPT-5.2-Codex examples
- ✅ Updated multi-model examples

#### `agent-bench/README.md`
- ✅ Added "Supported Models" section with examples
- ✅ Updated running evaluations examples to use GPT-5.2-Codex
- ✅ Listed common models (GPT, Claude, Gemini)

### 3. New Documentation

#### `MODEL_SUPPORT.md` (NEW)
- ✅ Comprehensive model reference with pricing tables
- ✅ Usage examples for all model types
- ✅ Model selection guidelines
- ✅ Instructions for adding new models

#### `CHANGELOG_GPT52CODEX.md` (NEW)
- ✅ This file documenting all changes

## Model Specifications

### GPT-5.2-Codex
- **Display Name**: GPT-5.2-Codex
- **Input Price**: $1.75 per 1M tokens
- **Cached Input**: $0.175 per 1M tokens
- **Output Price**: $14.00 per 1M tokens
- **Context Window**: 400,000 tokens
- **Max Output**: 128,000 tokens
- **Optimized For**: Long-horizon, agentic coding tasks

## Usage Examples

### Basic Usage
```bash
# Single task
modal run agent-bench/run_eval.py \
  --task-id ankidroid__Anki-Android-16395 \
  --model gpt-5.2-codex

# All tasks for a repo
modal run agent-bench/run_eval.py \
  --all-tasks \
  --repo anki \
  --model gpt-5.2-codex
```

### Multi-Model Comparison
```bash
# Run multiple models in parallel
modal run agent-bench/run_eval.py \
  --all-tasks \
  --models gpt-5.2-codex,gpt-5.1-codex,claude-opus-4-5
```

### Cost Analysis
```bash
# After running evaluations, analyze costs
python analysis/cost_comparison.py
python analysis/analyze_results.py
```

## Testing Recommendations

1. **Verify Basic Functionality**
   ```bash
   modal run agent-bench/run_eval.py \
     --task-id ankidroid__Anki-Android-14182 \
     --model gpt-5.2-codex
   ```

2. **Test Cost Analysis**
   ```bash
   # Run a few tasks
   modal run agent-bench/run_eval.py \
     --task-ids ankidroid__Anki-Android-14182,ankidroid__Anki-Android-14360 \
     --model gpt-5.2-codex
   
   # Check costs are calculated correctly
   python analysis/cost_comparison.py
   ```

3. **Verify Multi-Model Runs**
   ```bash
   modal run agent-bench/run_eval.py \
     --task-id ankidroid__Anki-Android-14182 \
     --models gpt-5.2-codex,gpt-5.1-codex
   ```

## Notes

- The evaluation system accepts **any model identifier** - GPT-5.2-Codex works without code changes
- Cost analysis scripts now recognize GPT-5.2-Codex and will calculate costs correctly
- Pricing follows OpenAI's published rates as of January 2026
- The model uses the same pricing structure as GPT-5.2 (identical input/output rates)

## Files Modified

```
agent-bench/
├── run_eval.py              # Updated examples & help text
└── README.md                # Added model support section

analysis/
├── cost_comparison.py       # Added GPT-5.2-Codex pricing
└── analyze_results.py       # Added GPT-5.2-Codex pricing

(new files)
├── MODEL_SUPPORT.md         # Comprehensive model documentation
└── CHANGELOG_GPT52CODEX.md  # This changelog
```

## Backward Compatibility

✅ All changes are **100% backward compatible**:
- Existing model configurations unchanged
- No breaking changes to APIs or scripts
- Existing data and results unaffected
- All previous functionality preserved

## Next Steps

1. Test the new model with a sample task
2. Run cost analysis to verify pricing calculations
3. Update any project-specific documentation
4. Consider running benchmark comparisons between GPT-5.2-Codex and GPT-5.1-Codex

---

**Date**: January 2026  
**Status**: Complete ✅
