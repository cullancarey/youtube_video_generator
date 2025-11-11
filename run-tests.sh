#!/bin/bash
set -e

PROJECT_ROOT=$(pwd)

upgrade_packages() {
  venv_path="$1"
  requirements_file="$2"
  lambda_name="$3"

  echo "🔄 Upgrading packages for $lambda_name..."
  source "$venv_path/bin/activate"

  # Step 1: update pip itself first (safer resolver)
  python -m pip install --upgrade pip setuptools wheel >/dev/null

  # Step 2: upgrade only *unpinned* packages, skip pinned ones
  echo "📦 Checking for outdated packages..."
  outdated=$(pip list --outdated --format=json | python3 -c '
import sys, json
for pkg in json.load(sys.stdin):
    print(pkg["name"])
  ')

  # Exclude packages with explicit pins in requirements
  pinned=$(grep -E "==" "$requirements_file" | cut -d"=" -f1)
  for p in $pinned; do
    outdated=$(echo "$outdated" | grep -v "^$p$" || true)
  done

  if [[ -n "$outdated" ]]; then
    echo "$outdated" | xargs -n1 pip install -U
  else
    echo "✅ All packages already up to date for $lambda_name."
  fi

  # Step 3: run dependency consistency check
  echo "🔍 Checking dependency consistency..."
  if ! pip check; then
    echo "⚠️ Detected dependency conflicts — rolling back to pinned versions."
    pip install -r "$requirements_file"
  fi

  # Step 4: refresh lockfile with final resolved state
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
  PYTHONPATH=.:$PROJECT_ROOT/lambdas/youtube python -m pytest tests/test_upload_video.py
  PYTHONPATH=.:$PROJECT_ROOT/lambdas/youtube python -m pytest tests/test_youtube_video_generator.py
  deactivate
}

echo "============================================"
echo " Running all Lambda tests locally"
echo "============================================"

upgrade_packages "$PROJECT_ROOT/venv-tweet" "$PROJECT_ROOT/lambdas/tweet/tweet_lambda_requirements-dev.txt" "Tweet Lambda"
upgrade_packages "$PROJECT_ROOT/venv-youtube" "$PROJECT_ROOT/lambdas/youtube/youtube_lambda_requirements-dev.txt" "YouTube Lambda"

test_tweet_lambda
test_youtube_lambda

echo "✅ All tests completed"
