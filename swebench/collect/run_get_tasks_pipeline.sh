#!/usr/bin/env bash

# If you'd like to parallelize, do the following:
# * Create a .env file in this folder
# * Declare GITHUB_TOKENS=token1,token2,token3...
export PYTHONHTTPSVERIFY=1
export SSL_CERT_FILE="$(python -c 'import certifi; print(certifi.where())')"

python get_tasks_pipeline.py \
    --repos 'wordpress-mobile/WordPress-Android' \
    --path_prs 'data/prs' \
    --path_tasks 'data/tasks' \
    --cutoff_date '20230101'