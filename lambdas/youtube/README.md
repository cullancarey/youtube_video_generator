# YouTube Lambda

Main entrypoint: youtube_video_generator.lambda_handler

## Purpose

Creates a daily video from Reddit quotes and uploads it to YouTube.

## Flow

1. Download OAuth and working files from S3 into /tmp.
2. Read Reddit credentials from SSM and fetch latest safe post from r/quotes.
3. Create narration audio with gTTS.
4. Download image candidates from Google image search response.
5. Render MP4 using ffmpeg.
6. Upload to YouTube and poll processing status until success or failure.
7. Clean up /tmp artifacts.

## Upload Validation Behavior

The uploader now verifies:

- Local MP4 exists and is non-trivial size before upload.
- YouTube processing status reaches succeeded before reporting success.
- Processing failure, rejection, or timeout raise errors so CloudWatch reflects the real outcome.

## Important Files

- youtube_video_generator.py
- upload_video.py
- metadata_optimizer.py
- youtube_lambda_requirements.txt
- youtube_lambda_requirements-dev.txt
- Dockerfile

## Environment Dependencies

- SSM params: reddit_client_id, reddit_client_secret, reddit_user_agent, reddit_username, reddit_password
- S3 bucket: youtube-uploader-bucket
- S3 objects: client_secrets.json, youtube_video_generator.py-oauth2.json
- OAuth scopes required in youtube_video_generator.py-oauth2.json:
	- https://www.googleapis.com/auth/youtube.upload
	- https://www.googleapis.com/auth/youtube.readonly

If a token was created before readonly scope was required, regenerate the OAuth token and replace the S3 object.

## Local Run Tips

Activate the YouTube virtual environment first:

```bash
source venv-youtube/bin/activate
```

Run tests:

```bash
PYTHONPATH=.:$PWD/lambdas/youtube python -m pytest tests/test_upload_video.py
PYTHONPATH=.:$PWD/lambdas/youtube python -m pytest tests/test_youtube_video_generator.py
```
