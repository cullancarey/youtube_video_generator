"""Lambda function to scrape Reddit, generate video, and upload to YouTube"""

import praw
import os
import subprocess
import shlex
import shutil
import random
import logging
from datetime import datetime
from gtts import gTTS
import requests
from mutagen.mp3 import MP3
import boto3
from upload_video import UploadVideo

logger = logging.getLogger()
logger.setLevel("INFO")


def get_image_urls(query):
    try:
        url = f"https://www.google.be/search?q={query}&tbm=isch"
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            logger.info(f"Fetched image URLs for query: {query}")
            return response.text
        logger.error(f"Failed to fetch image URLs. Status: {response.status_code}")
    except requests.Timeout:
        logger.error(f"Timeout fetching image URLs for query: {query}")
    except Exception as e:
        logger.exception(f"Exception fetching image URLs for query: {query}: {e}")
    return None


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
    try:
        file_setup()

        reddit = praw.Reddit(
            client_id=get_param("reddit_client_id"),
            client_secret=get_param("reddit_client_secret"),
            user_agent=get_param("reddit_user_agent"),
            username=get_param("reddit_username"),
            password=get_param("reddit_password"),
        )

        author = url = ""
        with open("/tmp/story.txt", "w", encoding="utf-8") as f:
            for post in reddit.subreddit("quotes").new(limit=1):
                if not post.over_18:
                    f.write(f"{post.title}\n{post.selftext}")
                    author, url = post.author, post.url

        with open("/tmp/story.txt", "r", encoding="utf-8") as f:
            text = f.read()
            tts = gTTS(text)
            tts.save("/tmp/story.mp3")

        audio = MP3("/tmp/story.mp3")
        num_images = max(1, int(audio.info.length))

        raw_html = get_image_urls(text) or get_image_urls("coding with python")
        raw_urls = raw_html.split('"') if raw_html else []
        urls = [u.split(";s")[0] for u in raw_urls if "https://encrypted-" in u]

        for idx in range(min(num_images, len(urls))):
            image = download_image(urls[idx])
            if image:
                with open(f"/tmp/images/image{idx}.jpg", "wb") as f:
                    f.write(image)

        frame_rate = audio.info.length / num_images
        video_path = "/tmp/output.mp4"
        command = (
            f"ffmpeg -y -hide_banner -framerate 1/{frame_rate} -pix_fmt yuvj420p "
            f"-pattern_type glob -i '/tmp/images/*.jpg' -i /tmp/story.mp3 "
            f"-c:v libx264 -crf 18 -vf scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2 -c:a aac -b:a 192k -shortest {video_path}"
        )

        result = subprocess.run(shlex.split(command), capture_output=True)
        if result.returncode != 0:
            logger.error(f"ffmpeg failed: {result.stderr.decode()}")
            raise RuntimeError("Video generation failed")

        titles = [
            f"Daily Quote {datetime.today().strftime('%Y-%m-%d')}",
            "Quotes Daily",
            f"{datetime.today().strftime('%Y-%m-%d')} Quote",
            "Quotes",
            "Daily Quote",
            "Quote",
        ]
        description = f"""Please enjoy this daily quote from u/{author}!
These quotes are from r/quotes on Reddit.
Link to post: {url}
This video was created and uploaded via Python!"""
        keywords = ["quote", "quotes", "daily quote", "python", "reddit"]

        uploader = UploadVideo()
        uploader.execute(
            video_path, random.choice(titles), description, "22", keywords, "private"
        )

        for path in [
            "/tmp/images",
            "/tmp/story.txt",
            "/tmp/story.mp3",
            "/tmp/output.mp4",
            "/tmp/client_secrets.json",
        ]:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to delete {path}: {e}")

        logger.info("Lambda completed successfully.")

    except Exception as e:
        logger.critical(f"Fatal error in lambda_handler: {e}")
