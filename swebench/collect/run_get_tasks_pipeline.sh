#!/usr/bin/env bash

export PYTHONHTTPSVERIFY=1
export SSL_CERT_FILE="$(python -c 'import certifi; print(certifi.where())')"

# If you'd like to parallelize, do the following:
# * Create a .env file in this folder
# * Declare GITHUB_TOKENS=token1,token2,token3...

export GITHUB_TOKENS="YOUR_GITHUB_TOKEN_HERE"
python3 get_tasks_pipeline.py \
    --repos 'ktorio/ktor' \
    --path_prs 'data/prs' \
    --path_tasks 'data/tasks' \
    --cutoff_date '20230101'

# export GITHUB_TOKENS="YOUR_GITHUB_TOKEN_HERE"
# python3 get_tasks_pipeline.py \
#     --repos 'ankidroid/Anki-Android' \
#     --path_prs 'data/prs' \
#     --path_tasks 'data/tasks' \
#     --cutoff_date '20230101'

# export GITHUB_TOKENS="YOUR_GITHUB_TOKEN_HERE"
# python3 get_tasks_pipeline.py \
#     --repos 'google/dagger' \
#     --path_prs 'data/prs' \
#     --path_tasks 'data/tasks' \
#     --cutoff_date '20230101'
