# YouTube Quote Video Generator + Tweet Bot

This project automates the generation of short YouTube quote videos using content scraped from Reddit and then tweets about the uploaded video. It's fully serverless, modular, and containerized using AWS Lambda + Docker, with Terraform-managed infrastructure and GitHub Actions for CI/CD.

---

## 🎥 Overview

1. **YouTube Lambda**:
   - Scrapes Reddit quotes
   - Converts them to speech using `gTTS`
   - Downloads relevant images
   - Creates a video with `ffmpeg`
   - Uploads the final video to YouTube

2. **Tweet Lambda**:
   - Runs on a separate schedule
   - Pulls the latest uploaded video from YouTube
   - Posts a tweet using credentials stored in SSM

---

## 🏐 Architecture

- **AWS Lambda**: Two functions, each containerized using Docker
- **Amazon ECR**: Stores Docker images for the Lambdas
- **Amazon S3**: Stores temp and reusable content like `story.txt`, `story.mp3`, and `output.mp4`
- **AWS Systems Manager (SSM)**: Stores secure parameters (Twitter/Reddit/YouTube credentials)
- **Terraform**: Manages infrastructure including IAM, Lambda, CloudWatch, ECR, S3
- **GitHub Actions**: Automates Docker builds and Terraform deployments

---

## 🚀 Deployment Flow

1. Push to `main` triggers GitHub Actions
2. Actions:
   - Build Docker images for each Lambda
   - Push them to ECR
   - Run `terraform apply` using updated image URIs

---

## 📚 File Structure

```
.
├── lambdas/
│   ├── tweet/
│   │   ├── Dockerfile
│   │   ├── tweet_lambda_requirements.txt
│   │   ├── tweet_lambda_requirements-dev.txt
│   │   └── tweet_youtube_video.py
│   └── youtube/
│       ├── Dockerfile
│       ├── youtube_lambda_requirements.txt
│       ├── youtube_lambda_requirements-dev.txt
│       ├── youtube_video_generator.py
│       └── upload_video.py
├── ffmpeg                 # Static ffmpeg binary
├── tests/                 # Unit tests
├── terraform/             # All .tf files
├── build_and_push_*.sh    # Docker build scripts
├── run-tests.sh           # Local test runner
```

---

## ⚙️ Local Development

### Setup
```bash
# Activate venv for YouTube Lambda\python3 -m venv venv-youtube
source venv-youtube/bin/activate
pip install -r lambdas/youtube/youtube_lambda_requirements-dev.txt

# Or activate venv for Tweet Lambda
python3 -m venv venv-tweet
source venv-tweet/bin/activate
pip install -r lambdas/tweet/tweet_lambda_requirements-dev.txt
```

### Testing
```bash
./run-tests.sh
```
This script will:
- Update outdated packages
- Freeze them to dev requirements
- Run pytest for all test suites

### Regenerate production requirements
```bash
python lambdas/youtube/generate_youtube_requirements.py
python lambdas/tweet/generate_tweet_requirements.py
```

---

## 📅 Scheduling
- **YouTube Lambda**: Daily @ 2:00 PM UTC
- **Tweet Lambda**: Every 4 hours @ :10 past the hour
- Triggered by CloudWatch Event Rules

---

## 🚧 Future Enhancements
- Slack alerting on failures
- Enhanced image scraping with real APIs
- Retry logic and dead letter queues
- SHA-based image tagging instead of `:latest`
- Split shared Python logic into its own layer