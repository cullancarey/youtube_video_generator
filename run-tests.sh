#!/bin/bash
set -e

PROJECT_ROOT=$(pwd)
MODE="${1:-upgrade}"  # Default to 'upgrade', or pass 'install' to skip upgrades

sync_environment() {
  echo "📦 Syncing Python environment with uv..."
  uv sync --group dev --no-install-project
  echo "✅ uv environment sync complete."
}

upgrade_environment() {
  echo "🔄 Upgrading dependencies with uv lock..."
  uv lock --upgrade
  uv sync --group dev --no-install-project
  python generate_youtube_requirements.py
  echo "✅ Dependency upgrade complete and requirements regenerated."
}

test_youtube_lambda() {
  echo "🔹 Running tests for upload_video.py and youtube_video_generator.py..."
  PYTHONPATH=.:$PROJECT_ROOT/lambdas/youtube "$PROJECT_ROOT/.venv/bin/python" -m pytest tests/test_upload_video.py
  PYTHONPATH=.:$PROJECT_ROOT/lambdas/youtube "$PROJECT_ROOT/.venv/bin/python" -m pytest tests/test_youtube_video_generator.py
}

echo "============================================"
echo " Running all Lambda tests locally"
echo "============================================"

if [[ "$MODE" == "upgrade" ]]; then
  echo "🔄 Upgrade mode: upgrading all packages..."
  upgrade_environment
elif [[ "$MODE" == "install" ]]; then
  echo "📦 Install mode: syncing environment from lock file..."
  sync_environment
else
  echo "❌ Unknown mode: $MODE. Use 'upgrade' (default) or 'install'."
  exit 1
fi

test_youtube_lambda

echo "✅ All tests completed"
