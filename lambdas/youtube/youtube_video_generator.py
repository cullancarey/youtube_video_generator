"""Lambda function to scrape Reddit, generate video, and upload to YouTube"""

import praw
import os
import glob
import hashlib
import json
import subprocess
import shutil
import logging
from datetime import datetime, timedelta, timezone
from gtts import gTTS
import requests
from botocore.exceptions import ClientError
from mutagen.mp3 import MP3
import boto3

from content_safety import find_denylisted_term
from metadata_optimizer import optimize_metadata
from upload_video import UploadVideo

logger = logging.getLogger()
logger.setLevel("INFO")

S3_BUCKET = "youtube-uploader-bucket"
POST_HISTORY_KEY = "used_reddit_posts.json"
POST_HISTORY_PATH = f"/tmp/{POST_HISTORY_KEY}"
POST_HISTORY_RETENTION_DAYS = 180


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
        bucket = S3_BUCKET
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
        raise


def load_post_history():
    """Fetch the record of previously-used Reddit post IDs; empty dict on first run."""
    try:
        boto3.resource("s3").Bucket(S3_BUCKET).download_file(
            POST_HISTORY_KEY, POST_HISTORY_PATH
        )
    except ClientError:
        logger.info("No existing post history found in S3; starting fresh.")
        return {}
    try:
        with open(POST_HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not parse post history file; starting fresh.")
        return {}


def save_post_history(history):
    """Prune entries older than the retention window and persist history to S3."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=POST_HISTORY_RETENTION_DAYS)
    pruned = {}
    for post_id, used_at in history.items():
        try:
            used_time = datetime.fromisoformat(used_at)
        except ValueError:
            continue
        if used_time >= cutoff:
            pruned[post_id] = used_at

    with open(POST_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(pruned, f)
    boto3.resource("s3").Bucket(S3_BUCKET).upload_file(
        POST_HISTORY_PATH, POST_HISTORY_KEY
    )


def select_safe_post(reddit, used_post_ids):
    """Pick an unused, non-NSFW, non-denylisted post, preferring community-vetted
    (upvoted) candidates over unvetted brand-new submissions."""
    search_tiers = [
        ("day", 50),
        ("week", 50),
        ("month", 50),
        (None, 25),  # last resort: unvetted newest posts
    ]
    for time_filter, limit in search_tiers:
        subreddit = reddit.subreddit("quotes")
        candidates = (
            subreddit.new(limit=limit)
            if time_filter is None
            else subreddit.top(time_filter=time_filter, limit=limit)
        )
        for post in candidates:
            if post.over_18 or post.id in used_post_ids:
                continue
            flagged_term = find_denylisted_term(f"{post.title}\n{post.selftext}")
            if flagged_term:
                logger.warning(
                    f"Skipping post {post.id} flagged for denylisted term '{flagged_term}'."
                )
                continue
            return post
    return None


def lambda_handler(event, context):
    # Step 1: Setup
    try:
        file_setup()
    except Exception as e:
        logger.critical(f"File setup failed: {e}", exc_info=True)
        raise

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
        raise

    # Step 3: Fetch and write Reddit content
    try:
        author = reddit_url = ""
        post_history = load_post_history()
        selected_post = select_safe_post(reddit, set(post_history.keys()))

        if selected_post is None:
            raise RuntimeError(
                "No safe, unused Reddit post found across day/week/month/new candidates."
            )

        with open("/tmp/story.txt", "w", encoding="utf-8") as f:
            f.write(f"{selected_post.title}\n{selected_post.selftext}")
        author = str(selected_post.author)
        reddit_url = f"https://www.reddit.com{selected_post.permalink}"
        logger.info("Reddit content written to /tmp/story.txt.")
    except Exception as e:
        logger.critical(f"Failed to fetch or write Reddit post: {e}", exc_info=True)
        raise

    # Step 4: Generate audio
    try:
        with open("/tmp/story.txt", "r", encoding="utf-8") as f:
            text = f.read()
            tts = gTTS(text)
            tts.save("/tmp/story.mp3")
        logger.info("Audio generated successfully.")
    except Exception as e:
        logger.critical(f"TTS or audio generation failed: {e}", exc_info=True)
        raise

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
        raise

    # Step 6: Generate video
    try:
        frame_rate = max(0.1, audio.info.length / max(1, num_images))
        video_path = "/tmp/output.mp4"
        video_path_short = "/tmp/output_short.mp4"
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

        def render_video(output_path, scale_filter):
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
                scale_filter,
                "-r",
                "30",
                "-movflags",
                "+faststart",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                output_path,
            ]
            result = subprocess.run(command, capture_output=True)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")
            if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
                raise RuntimeError("Generated video file is missing or too small.")

        render_video(
            video_path,
            "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
        )
        logger.info("Video created successfully.")

        short_video_ready = False
        try:
            render_video(
                video_path_short,
                "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            )
            short_video_ready = True
            logger.info("Vertical (Shorts) video created successfully.")
        except Exception as e:
            logger.warning(f"Shorts video generation failed: {e}", exc_info=True)
    except Exception as e:
        logger.critical(f"Video generation failed: {e}", exc_info=True)
        raise

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
        raise

    # Shorts upload is best-effort: a failure here shouldn't fail the whole run
    # since the primary long-form video already uploaded successfully.
    if short_video_ready:
        try:
            short_id = uploader.execute(
                video_path_short,
                f"{title} #Shorts",
                description,
                "22",
                keywords + ["shorts"],
                "public",
            )
            logger.info(f"Shorts video uploaded successfully. video_id={short_id}")
        except Exception as e:
            logger.warning(f"Shorts upload failed: {e}", exc_info=True)

    # Record the post as used only after a successful upload, so a downstream
    # failure doesn't permanently burn a quote that was never actually posted.
    try:
        post_history[selected_post.id] = datetime.now(timezone.utc).isoformat()
        save_post_history(post_history)
    except Exception as e:
        logger.warning(f"Failed to persist post history: {e}", exc_info=True)

    # Step 8: Cleanup
    try:
        for path in [
            "/tmp/images",
            "/tmp/images_concat.txt",
            "/tmp/story.txt",
            "/tmp/story.mp3",
            "/tmp/output.mp4",
            "/tmp/output_short.mp4",
            "/tmp/client_secrets.json",
        ]:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)
        logger.info("Cleanup complete. Lambda finished successfully.")
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}", exc_info=True)
