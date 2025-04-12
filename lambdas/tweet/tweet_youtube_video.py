"""Tweet the most recent YouTube video using Twitter API"""

import os
import logging
import re
from datetime import datetime
from dateutil.tz import gettz

import boto3
import tweepy
import httplib2
from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def extract_keywords_from_text(text, max_keywords=5):
    """Extract keyword-like hashtags from a text block."""
    stopwords = {
        "the",
        "a",
        "of",
        "in",
        "on",
        "and",
        "to",
        "for",
        "is",
        "with",
        "this",
        "that",
        "your",
    }
    words = re.findall(r"\b\w+\b", text.lower())
    keywords = [word for word in words if word not in stopwords and len(word) > 3]
    unique_keywords = list(dict.fromkeys(keywords))
    return [f"#{kw}" for kw in unique_keywords[:max_keywords]]


def get_authenticated_service():
    """Authenticate with YouTube API using OAuth2 credentials"""
    try:
        httplib2.RETRIES = 1
        client_secrets_file = "/tmp/client_secrets.json"
        flow = flow_from_clientsecrets(
            client_secrets_file,
            scope="https://www.googleapis.com/auth/youtube.readonly",
            message=(
                f"Missing OAuth configuration in {client_secrets_file}. "
                "Download credentials from Google API Console."
            ),
        )

        storage = Storage("/tmp/tweet_youtube_video.py-oauth2.json")
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            logger.warning("Invalid or missing YouTube credentials. Running auth flow.")
            credentials = run_flow(
                flow, storage, argparser.parse_args(args=["--noauth_local_webserver"])
            )

        logger.info("Successfully authenticated with YouTube API.")
        return build("youtube", "v3", http=credentials.authorize(httplib2.Http()))
    except Exception as e:
        logger.critical(f"YouTube authentication failed: {e}")
        return None


def get_param(param_name):
    """Fetch a parameter value from AWS Systems Manager Parameter Store"""
    client = boto3.client("ssm")
    try:
        logger.info(f"Fetching parameter: {param_name}")
        response = client.get_parameter(Name=param_name, WithDecryption=True)
        return response["Parameter"]["Value"]
    except Exception as e:
        logger.error(f"Failed to retrieve parameter {param_name}: {e}")
        return None


def file_setup():
    """Download required OAuth files from S3"""
    s3 = boto3.resource("s3")
    bucket = "youtube-uploader-bucket"
    keys = ["tweet_youtube_video.py-oauth2.json", "client_secrets.json"]
    for key in keys:
        try:
            path = f"/tmp/{key}"
            s3.Bucket(bucket).download_file(key, path)
            logger.info(f"Downloaded {key} to {path}")
        except Exception as e:
            logger.warning(f"Failed to download {key} from S3: {e}")


def lambda_handler(event, context):
    """AWS Lambda entrypoint to authenticate and tweet latest YouTube video"""
    try:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Local testing only

        file_setup()

        youtube = get_authenticated_service()
        if not youtube:
            logger.error("YouTube service unavailable.")
            return

        twitter_client = tweepy.Client(
            consumer_key=get_param("twitter_api_key"),
            consumer_secret=get_param("twitter_api_key_secret"),
            access_token=get_param("twitter_access_token"),
            access_token_secret=get_param("twitter_access_token_secret"),
        )

        request = youtube.search().list(
            forMine=True, type="video", part="snippet", maxResults=1
        )
        response = request.execute()
        item = response["items"][0]
        video_id = item["id"]["videoId"]
        channel_id = item["snippet"]["channelId"]
        video_title = item["snippet"]["title"]
        video_description = item["snippet"].get("description", "")
        timestamp = datetime.now(gettz("US/Central"))

        hashtags = extract_keywords_from_text(f"{video_title} {video_description}")
        if not hashtags:
            hashtags = ["#quotes", "#quoteoftheday", "#subscribe"]

        tweet_text = (
            f'Today\'s video is live! Title: "{video_title}"\n'
            f"Watch here -> https://www.youtube.com/watch?v={video_id}\n"
            f"Please support the channel and subscribe! -> https://www.youtube.com/channel/{channel_id}\n"
            f"Posted at: {timestamp.strftime('%Y-%m-%d %H:%M %Z')}\n"
            f"{' '.join(hashtags)}"
        )

        logger.info(f"Tweeting: {tweet_text}")
        twitter_client.create_tweet(text=tweet_text)
        logger.info("Tweet successfully posted.")

    except Exception as e:
        logger.critical(f"Unhandled exception in lambda_handler: {e}")
