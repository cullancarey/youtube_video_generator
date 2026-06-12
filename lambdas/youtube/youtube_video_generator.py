"""Lambda function to scrape Reddit, generate video, and upload to YouTube"""

import praw
import os
import glob
import hashlib
import subprocess
import shutil
import logging
from gtts import gTTS
import requests
from mutagen.mp3 import MP3
import boto3

# from .upload_video import UploadVideo # for local testing
from metadata_optimizer import optimize_metadata
from upload_video import UploadVideo

logger = logging.getLogger()
logger.setLevel("INFO")


def download_image(url):
    try:
        response = requests.get(url, timeout=60, allow_redirects=True)
        if response.status_code == 200:
            return response.content
        logger.error(f"Failed to download image. Status: {response.status_code}")
    except requests.Timeout:
        logger.error(f"Timeout downloading image: {url}")
    except Exception as e:
        logger.exception(f"Exception downloading image: {url}: {e}")
    return None


def build_image_urls(text, num_images):
    """Build Lorem Picsum URLs seeded from the quote text for reproducible variety."""
    base_seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % 1000
    return [
        f"https://picsum.photos/seed/{(base_seed + i) % 1000}/1280/720"
        for i in range(num_images)
    ]


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
        author = reddit_url = ""
        with open("/tmp/story.txt", "w", encoding="utf-8") as f:
            for post in reddit.subreddit("quotes").new(limit=1):
                if not post.over_18:
                    f.write(f"{post.title}\n{post.selftext}")
                    author = str(post.author)
                    reddit_url = f"https://www.reddit.com{post.permalink}"
        logger.info("Reddit content written to /tmp/story.txt.")
    except Exception as e:
        logger.critical(f"Failed to fetch or write Reddit post: {e}", exc_info=True)
        return

    # Step 4: Generate audio
    try:
        with open("/tmp/story.txt", "r", encoding="utf-8") as f:
            text = f.read()
            tts = gTTS(text)
            tts.save("/tmp/story.mp3")
        logger.info("Audio generated successfully.")
    except Exception as e:
        logger.critical(f"TTS or audio generation failed: {e}", exc_info=True)
        return

    # Step 5: Analyze audio and collect images
    try:
        audio = MP3("/tmp/story.mp3")
        num_images = max(1, int(audio.info.length))
        urls = build_image_urls(text, num_images)
        logger.info(f"Fetching {len(urls)} image(s) from Picsum for text: {text[:80]}")

        saved = 0
        for image_url in urls:
            if saved >= num_images:
                break
            image = download_image(image_url)
            if not image:
                continue
            # Validate the downloaded bytes are a real JPEG or PNG before saving,
            # so ffmpeg never receives a corrupt/WebP/AVIF file mislabeled as .jpg.
            if image[:3] == b"\xff\xd8\xff":
                ext = "jpg"
            elif image[:8] == b"\x89PNG\r\n\x1a\n":
                ext = "png"
            else:
                logger.warning("Skipping non-JPEG/PNG image from %s", image_url)
                continue
            with open(f"/tmp/images/image{saved}.{ext}", "wb") as f:
                f.write(image)
            saved += 1

        if saved == 0:
            raise RuntimeError("No valid images were downloaded for video generation.")
        num_images = saved
        logger.info(f"{num_images} image(s) prepared.")
    except Exception as e:
        logger.critical(f"Image processing failed: {e}", exc_info=True)
        return

    # Step 6: Generate video
    try:
        frame_rate = max(0.1, audio.info.length / max(1, num_images))
        video_path = "/tmp/output.mp4"
        concat_file = "/tmp/images_concat.txt"

        image_files = sorted(glob.glob("/tmp/images/image*"))
        if not image_files:
            raise RuntimeError("No image files found after downloading.")

        # Build concat input with explicit per-image durations so ffmpeg does not rely on glob support.
        with open(concat_file, "w", encoding="utf-8") as f:
            for image_file in image_files:
                f.write(f"file '{image_file}'\n")
                f.write(f"duration {frame_rate:.6f}\n")
            # Repeat last image; ffmpeg concat demuxer ignores duration on final entry otherwise.
            f.write(f"file '{image_files[-1]}'\n")

        command = [
            f"{os.getcwd()}/ffmpeg",
            "-y",
            "-hide_banner",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_file,
            "-i",
            "/tmp/story.mp3",
            "-vsync",
            "vfr",
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-level",
            "4.0",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-vf",
            "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            "-r",
            "30",
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            video_path,
        ]

        result = subprocess.run(command, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")
        if not os.path.exists(video_path) or os.path.getsize(video_path) < 1024:
            raise RuntimeError("Generated video file is missing or too small.")
        logger.info("Video created successfully.")
    except Exception as e:
        logger.critical(f"Video generation failed: {e}", exc_info=True)
        return

    # Step 7: Upload
    try:
        title, description, keywords, thumbnail = optimize_metadata(
            text, author, reddit_url
        )
        uploader = UploadVideo()
        video_id = uploader.execute(
            video_path, title, description, "22", keywords, "public"
        )
        logger.info(f"Video uploaded and processed successfully. video_id={video_id}")
    except Exception as e:
        logger.critical(f"Upload failed: {e}", exc_info=True)
        return

    # Step 8: Cleanup
    try:
        for path in [
            "/tmp/images",
            "/tmp/images_concat.txt",
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
