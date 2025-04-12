#!/bin/bash

set -e

PROJECT_ROOT=$(pwd)

upgrade_packages() {
  venv_path="$1"
  requirements_file="$2"
  lambda_name="$3"

  echo "🔄 Upgrading packages for $lambda_name..."
  source "$venv_path/bin/activate"

  # Get list of outdated packages in JSON format and upgrade each
  outdated=$(pip list --outdated --format=json | python3 -c '
import sys, json
for pkg in json.load(sys.stdin):
    print(pkg["name"])
  ')

  if [[ -n "$outdated" ]]; then
    echo "$outdated" | xargs -n1 pip install -U
  else
    echo "✅ All packages already up to date for $lambda_name."
  fi

  # Freeze updated versions into requirements file
  pip freeze > "$requirements_file"
  deactivate
}

test_tweet_lambda() {
  echo "🔹 Activating venv-tweet and running tests for tweet_youtube_video.py..."
  source "$PROJECT_ROOT/venv-tweet/bin/activate"
  PYTHONPATH=. python -m pytest tests/test_tweet_youtube_video.py
  deactivate
}

test_youtube_lambda() {
  echo "🔹 Activating venv-youtube and running tests for upload_video.py and youtube_video_generator.py..."
  source "$PROJECT_ROOT/venv-youtube/bin/activate"
  PYTHONPATH=. python -m pytest tests/test_upload_video.py
  PYTHONPATH=. python -m pytest tests/test_youtube_video_generator.py
  deactivate
}

echo "============================================"
echo " Running all Lambda tests locally"
echo "============================================"

# Upgrade dependencies
upgrade_packages "$PROJECT_ROOT/venv-tweet" "$PROJECT_ROOT/tweet_lambda_requirements-dev.txt" "Tweet Lambda"
upgrade_packages "$PROJECT_ROOT/venv-youtube" "$PROJECT_ROOT/youtube_lambda_requirements-dev.txt" "YouTube Lambda"

# Run tests
test_tweet_lambda
test_youtube_lambda

echo "✅ All tests completed"