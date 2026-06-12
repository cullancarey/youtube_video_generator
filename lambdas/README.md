# Lambda Services

This directory contains the YouTube Lambda application deployed as a container image.

## Service

- youtube: builds and uploads a generated quote video to YouTube.

## Docker Image

- lambdas/youtube/Dockerfile

Image is pushed to ECR by:

- build_and_push_youtube.sh

## Local Testing

Use the root test runner:

```bash
./run-tests.sh install
```

Or run targeted tests:

```bash
uv sync --group dev --no-install-project
PYTHONPATH=.:$PWD/lambdas/youtube .venv/bin/python -m pytest tests/test_upload_video.py
PYTHONPATH=.:$PWD/lambdas/youtube .venv/bin/python -m pytest tests/test_youtube_video_generator.py
```

## Shared Notes

- OAuth and secret material is not stored in source control.
- Runtime artifacts are written under /tmp at Lambda runtime.
- Lambda image tags are short git SHA values from CI.
