# YouTube Video Generator + Tweet Bot

Serverless automation that:

1. Generates a quote video from Reddit content.
2. Uploads it to YouTube.
3. Tweets the newest channel video on a schedule.

The stack is AWS Lambda (container image), ECR, S3, SSM Parameter Store, Terraform, and GitHub Actions.

## Components

- YouTube Lambda in lambdas/youtube:
   - Scrapes latest safe post from r/quotes.
   - Generates narration with gTTS.
   - Downloads images.
   - Renders MP4 using ffmpeg.
   - Uploads and verifies YouTube processing status before reporting success.
- Tweet Lambda in lambdas/tweet:
   - Reads latest uploaded video from your YouTube channel.
   - Builds hashtags from title and description.
   - Publishes a tweet using X API credentials.
- Infra in terraform:
   - ECR repositories for both Lambda images.
   - Lambda functions and IAM roles.
   - S3 bucket for OAuth artifacts.
   - EventBridge schedules.

## Runtime And Scheduling

- Runtime: Python 3.13 Lambda base images.
- YouTube Lambda schedule: daily at 14:00 UTC.
- Tweet Lambda schedule: 01:10, 05:10, 09:10, 13:10, 17:10, 21:10 UTC.

## CI/CD

Workflow: .github/workflows/deploy-docker.yml

On push to main:

1. Build and push tweet image with build_and_push_tweet.sh.
2. Build and push youtube image with build_and_push_youtube.sh.
3. Run terraform init, fmt, validate, plan.
4. Run terraform apply only when commit message contains [tf-apply].

Required GitHub environment variables (production):

- ACCOUNT_ID
- REGION
- DEPLOYMENT_ROLE

## Local Development

Create virtual environments:

```bash
python3 -m venv venv-youtube
source venv-youtube/bin/activate
pip install -r lambdas/youtube/youtube_lambda_requirements-dev.txt
deactivate

python3 -m venv venv-tweet
source venv-tweet/bin/activate
pip install -r lambdas/tweet/tweet_lambda_requirements-dev.txt
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

Regenerate production requirements from dev lock files:

```bash
python generate_youtube_requirements.py
python generate_tweet_requirements.py
```

## Secrets And Config

Parameters expected in SSM Parameter Store:

- Reddit:
   - reddit_client_id
   - reddit_client_secret
   - reddit_user_agent
   - reddit_username
   - reddit_password
- Twitter/X:
   - twitter_api_key
   - twitter_api_key_secret
   - twitter_access_token
   - twitter_access_token_secret

OAuth files expected in S3 bucket youtube-uploader-bucket:

- client_secrets.json
- youtube_video_generator.py-oauth2.json
- tweet_youtube_video.py-oauth2.json

## Docs

- lambdas/README.md
- lambdas/youtube/README.md
- lambdas/tweet/README.md
- terraform/README.md