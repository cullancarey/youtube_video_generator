# Tweet Lambda

Main entrypoint: tweet_youtube_video.lambda_handler

## Purpose

Tweets the most recently uploaded video from your channel on a fixed schedule.

## Flow

1. Download OAuth files from S3 into /tmp.
2. Authenticate YouTube readonly API client.
3. Fetch latest channel video metadata.
4. Build hashtags from title and description.
5. Read Twitter/X secrets from SSM.
6. Publish tweet through Tweepy.

## Important Files

- tweet_youtube_video.py
- tweet_lambda_requirements.txt
- tweet_lambda_requirements-dev.txt
- Dockerfile

## Environment Dependencies

- SSM params: twitter_api_key, twitter_api_key_secret, twitter_access_token, twitter_access_token_secret
- S3 bucket: youtube-uploader-bucket
- S3 objects: client_secrets.json, tweet_youtube_video.py-oauth2.json

## Local Run Tips

Activate the Tweet virtual environment first:

```bash
source venv-tweet/bin/activate
```

Run tests:

```bash
PYTHONPATH=. python -m pytest tests/test_tweet_youtube_video.py
```
