# Generating AI Predictions
Aman Gottumukkala &bull; March 25, 2025

In this tutorial, we explain how to use your previously validated task instances to generate AI predictions for SWE-bench evaluation.


## Creating a Dataset for Evaluation

The first step is to convert your task instances into a dataset format that includes the necessary prompts and context for evaluation. This will fetch context from the repository for each task instance and add it to the prompt in place with the 'oracle' setting.

Read `run_create_dataset.py` for more context on the flags and different retrieval settings:

```bash
python run_create_dataset.py \
    --dataset_name_or_path  \ # Path to HF directory created from validation.ipynb
    --output_dir  \ # datasets directory
    --retrieval_file \
    --prompt_style style-3 \
    --file_source oracle \
    --splits test \
    --include_test_files \ # Optional! Add if you want to include test files in the prompt
```

## Generating Model Predictions

After creating your dataset, you can generate predictions from various AI models. This will output the models' solutions to your prompts in .jsonl format:

```bash
# Set your API keys for different model providers
export ANTHROPIC_API_KEY=your_anthropic_api_key
export OPENAI_API_KEY=your_openai_api_key
export FIREWORKS_API_KEY=your_fireworks_api_key
export GEMINI_API_KEY=your_gemini_api_key

# To run inference on a specific model, you can run a command like this
python3 ./inference/run_api.py \
    --dataset_name_or_path \
    --models o1 o3 o4-mini o3-mini gpt-4.5-preview gpt-4o-2024-11-20 claude-3-5-sonnet-20241022 claude-3-7-sonnet-20250219 claude-3-7-sonnet-20250219-thinking gemini-2.5-pro-exp-03-25 deepseek-r1 deepseek-v3 llama-v3p3-70b-instruct \
    --output_dir \
    --split

python3 ./inference/run_api.py \
    --dataset_name_or_path ./datasets/Kotlin-bench__style-3__fs-oracle \
    --models o1 o3 o4-mini o3-mini gpt-4.5-preview gpt-4o-2024-11-20 claude-3-5-sonnet-20241022 claude-3-7-sonnet-20250219 claude-3-7-sonnet-20250219-thinking gemini-2.5-pro-exp-03-25 deepseek-r1 deepseek-v3 llama-v3p3-70b-instruct \
    --output_dir ./predictions/Kotlin-bench \
    --split test

python3 ./inference/run_api.py \
    --dataset_name_or_path ./datasets/Kotlin-bench__style-3__fs-oracle \
    --models o3 \
    --output_dir ./predictions/Kotlin-bench \
    --split test
```