# YouTube Video Generator

Serverless automation that:

1. Generates a quote video from Reddit content.
2. Uploads it to YouTube.

The stack is AWS Lambda (container image), ECR, S3, SSM Parameter Store, Terraform, and GitHub Actions.

## Components

- YouTube Lambda in lambdas/youtube:
   - Scrapes latest safe post from r/quotes.
   - Generates narration with gTTS.
   - Downloads images.
   - Renders MP4 using ffmpeg.
   - Uploads and verifies YouTube processing status before reporting success.
- Infra in terraform:
   - ECR repository for the Lambda image.
   - Lambda function and IAM role.
   - S3 bucket for OAuth artifacts.
   - EventBridge schedule.

## Runtime And Scheduling

- Runtime: Python 3.13 Lambda base image.
- YouTube Lambda schedule: daily at 14:00 UTC.

## CI/CD

Workflow: .github/workflows/deploy-docker.yml

On push to main:

1. Build and push youtube image with build_and_push_youtube.sh.
2. Run terraform init, fmt, validate, plan.
3. Run terraform apply only when commit message contains [tf-apply].

Required GitHub environment variables (production):

- ACCOUNT_ID
- REGION
- DEPLOYMENT_ROLE

## Local Development

Create virtual environment:

```bash
python3 -m venv venv-youtube
source venv-youtube/bin/activate
pip install -r lambdas/youtube/youtube_lambda_requirements-dev.txt
deactivate
```

Run tests with dependency install mode:

```bash
./run-tests.sh install
```

Run tests with dependency upgrade mode (default):

```bash
./run-tests.sh
```

Regenerate production requirements from dev lock file:

```bash
python generate_youtube_requirements.py
```

## Secrets And Config

Parameters expected in SSM Parameter Store:

- reddit_client_id
- reddit_client_secret
- reddit_user_agent
- reddit_username
- reddit_password

OAuth files expected in S3 bucket youtube-uploader-bucket:

- client_secrets.json
- youtube_video_generator.py-oauth2.json

## Docs

- lambdas/README.md
- lambdas/youtube/README.md
- terraform/README.md