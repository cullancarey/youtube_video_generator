# Lambda Services

This directory contains the two Lambda applications deployed as container images.

## Services

- youtube: builds and uploads a generated quote video to YouTube.
- tweet: tweets the latest uploaded YouTube video.

## Docker Images

- lambdas/youtube/Dockerfile
- lambdas/tweet/Dockerfile

Both images are pushed to ECR by:

- build_and_push_youtube.sh
- build_and_push_tweet.sh

## Local Testing

Use the root test runner:

```bash
./run-tests.sh install
```

Or run targeted tests:

```bash
source venv-youtube/bin/activate
PYTHONPATH=.:$PWD/lambdas/youtube python -m pytest tests/test_upload_video.py
PYTHONPATH=.:$PWD/lambdas/youtube python -m pytest tests/test_youtube_video_generator.py
deactivate

source venv-tweet/bin/activate
PYTHONPATH=. python -m pytest tests/test_tweet_youtube_video.py
deactivate
```

## Shared Notes

- OAuth and secret material is not stored in source control.
- Runtime artifacts are written under /tmp at Lambda runtime.
- Lambda image tags are short git SHA values from CI.
