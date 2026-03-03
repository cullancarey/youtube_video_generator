"""Lambda function to scrape Reddit, generate video, and upload to YouTube"""

import praw
import os
import subprocess
import shlex
import shutil
import logging
import requests
from mutagen.mp3 import MP3
import boto3

# from .upload_video import UploadVideo # for local testing
from metadata_optimizer import optimize_metadata
from upload_video import UploadVideo

logger = logging.getLogger()
logger.setLevel("INFO")


def get_images_unsplash(query, num_images=5):
    """Fetch images from Unsplash API (free, copyright-friendly)."""
    try:
        url = "https://api.unsplash.com/search/photos"
        params = {"query": query, "per_page": num_images, "order_by": "relevant"}
        response = requests.get(url, params=params, timeout=60)
        if response.status_code == 200:
            data = response.json()
            urls = [photo["urls"]["regular"] for photo in data.get("results", [])]
            logger.info(f"Fetched {len(urls)} images from Unsplash for: {query}")
            return urls
        logger.error(f"Unsplash API error: {response.status_code}")
    except requests.Timeout:
        logger.error(f"Timeout fetching images from Unsplash for query: {query}")
    except Exception as e:
        logger.exception(
            f"Exception fetching images from Unsplash for query: {query}: {e}"
        )
    return []


def download_image(url):
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            return response.content
        logger.error(f"Failed to download image. Status: {response.status_code}")
    except requests.Timeout:
        logger.error(f"Timeout downloading image: {url}")
    except Exception as e:
        logger.exception(f"Exception downloading image: {url}: {e}")
    return None


def get_param(param_name):
    client = boto3.client("ssm")
    try:
        logger.info(f"Retrieving parameter {param_name}...")
        response = client.get_parameter(Name=param_name, WithDecryption=True)
        return response["Parameter"]["Value"]
    except Exception as e:
        logger.exception(f"Error retrieving parameter {param_name}: {e}")
        return None


def generate_audio_with_polly(text):
    """Generate audio using AWS Polly TTS."""
    try:
        polly = boto3.client("polly", region_name="us-east-2")
        logger.info("Generating audio with AWS Polly...")
        response = polly.synthesize_speech(
            Text=text, OutputFormat="mp3", VoiceId="Joanna", Engine="neural"
        )
        with open("/tmp/story.mp3", "wb") as f:
            f.write(response["AudioStream"].read())
        logger.info("Audio generated successfully with Polly.")
    except Exception as e:
        logger.exception(f"Polly TTS generation failed: {e}")
        raise


def file_setup():
    try:
        s3 = boto3.resource("s3")
        bucket = "youtube-uploader-bucket"
        keys = [
            "youtube_video_generator.py-oauth2.json",
            "story.txt",
            "story.mp3",
            "output.mp4",
            "client_secrets.json",
        ]
        for key in keys:
            s3.Bucket(bucket).download_file(key, f"/tmp/{key}")
        os.makedirs("/tmp/images", exist_ok=True)
        logger.info("S3 files downloaded and image directory created.")
    except Exception as e:
        logger.critical(f"Failed in file_setup: {e}")


def lambda_handler(event, context):
    # Step 1: Setup
    try:
        file_setup()
    except Exception as e:
        logger.critical(f"File setup failed: {e}", exc_info=True)
        return

    # Step 2: Initialize Reddit
    try:
        reddit = praw.Reddit(
            client_id=get_param("reddit_client_id"),
            client_secret=get_param("reddit_client_secret"),
            user_agent=get_param("reddit_user_agent"),
            username=get_param("reddit_username"),
            password=get_param("reddit_password"),
        )
    except Exception as e:
        logger.critical(f"Reddit initialization failed: {e}", exc_info=True)
        return

    # Step 3: Fetch and write Reddit content
    try:
        author = url = ""
        with open("/tmp/story.txt", "w", encoding="utf-8") as f:
            for post in reddit.subreddit("quotes").new(limit=1):
                if not post.over_18:
                    f.write(f"{post.title}\n{post.selftext}")
                    author, url = post.author, post.url
        logger.info("Reddit content written to /tmp/story.txt.")
    except Exception as e:
        logger.critical(f"Failed to fetch or write Reddit post: {e}", exc_info=True)
        return

    # Step 4: Generate audio
    try:
        with open("/tmp/story.txt", "r", encoding="utf-8") as f:
            text = f.read()
            generate_audio_with_polly(text)
    except Exception as e:
        logger.critical(f"Audio generation failed: {e}", exc_info=True)
        return

    # Step 5: Analyze audio and collect images
    try:
        audio = MP3("/tmp/story.mp3")
        num_images = max(1, int(audio.info.length))

        # Fetch images from Unsplash using post text as query
        urls = get_images_unsplash(text, num_images=num_images)

        # Fallback to generic search if specific query yields no results
        if not urls:
            logger.warning(f"No images found for query, falling back to generic search")
            urls = get_images_unsplash(
                "motivation quote inspiration", num_images=num_images
            )

        for idx, url in enumerate(urls):
            image = download_image(url)
            if image:
                with open(f"/tmp/images/image{idx}.jpg", "wb") as f:
                    f.write(image)
        logger.info(f"Downloaded {len(urls)} images from Unsplash.")
    except Exception as e:
        logger.critical(f"Image processing failed: {e}", exc_info=True)
        return

    # Step 6: Generate video
    try:
        frame_rate = audio.info.length / num_images
        video_path = "/tmp/output.mp4"
        command = (
            f"{os.getcwd()}/ffmpeg -y -hide_banner -framerate 1/{frame_rate} "
            f"-pix_fmt yuvj420p -pattern_type glob -i '/tmp/images/*.jpg' "
            f"-i /tmp/story.mp3 -c:v libx264 -crf 18 "
            f"-vf scale=1280:720:force_original_aspect_ratio=decrease,"
            f"pad=1280:720:(ow-iw)/2:(oh-ih)/2 -c:a aac -b:a 192k -shortest {video_path}"
        )

        result = subprocess.run(shlex.split(command), capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")
        logger.info("Video created successfully.")
    except Exception as e:
        logger.critical(f"Video generation failed: {e}", exc_info=True)
        return

    # Step 7: Upload
    try:
        title, description, keywords, thumbnail = optimize_metadata(text, author, url)
        uploader = UploadVideo()
        uploader.execute(video_path, title, description, "22", keywords, "public")
        logger.info("Video uploaded successfully.")
    except Exception as e:
        logger.critical(f"Upload failed: {e}", exc_info=True)
        return

    # Step 8: Cleanup
    try:
        for path in [
            "/tmp/images",
            "/tmp/story.txt",
            "/tmp/story.mp3",
            "/tmp/output.mp4",
            "/tmp/client_secrets.json",
        ]:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)
        logger.info("Cleanup complete. Lambda finished successfully.")
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}", exc_info=True)
