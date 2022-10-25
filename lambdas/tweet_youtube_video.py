# -*- coding: utf-8 -*-

# Sample Python code for youtube.videos.list
# See instructions for running these code samples locally:
# https://developers.google.com/explorer-help/guides/code_samples#python
"""os is used to access files on the system"""
import os
from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow
import httplib2
import tweepy
from datetime import datetime
import boto3
# import shutil
from dateutil.tz import gettz

# shutil.copy(
#     f"{os.getcwd()}/tmp/tweet_video.py-oauth2.json", "/tmp/tweet_video.py-oauth2.json"
# )


def get_authenticated_service():
    """Function used to authenticate to the third party platform"""
    httplib2.RETRIES = 1
    client_secrets_file = f"{os.getcwd()}/client_secrets.json"
    youtube_upload_scope = "https://www.googleapis.com/auth/youtube.readonly"
    youtube_api_service_name = "youtube"
    youtube_api_version = "v3"
    missing_client_secrets_message = f"""
    WARNING: Please configure OAuth 2.0

    To make this sample run you will need to populate the client_secrets.json file
    found at:

       {os.path.abspath(
        os.path.join(os.path.dirname(__file__), client_secrets_file)
    )}

    with information from the API Console
    https://console.developers.google.com/

    For more information about the client_secrets.json file format, please visit:
    https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
    """

    flow = flow_from_clientsecrets(
        client_secrets_file,
        scope=youtube_upload_scope,
        message=missing_client_secrets_message,
    )

    storage = Storage("/tmp/tweet_video.py-oauth2.json")
    credentials = storage.get()
    print(credentials)

    if credentials is None or credentials.invalid:
        credentials = run_flow(
            flow, storage, argparser.parse_args(args=["--noauth_local_webserver"])
        )

    return build(
        youtube_api_service_name,
        youtube_api_version,
        http=credentials.authorize(httplib2.Http()),
    )


def get_param(param):
    """Retrieves parameter from parameter store in AWS"""
    client = boto3.client("ssm")
    response = client.get_parameter(Name=param, WithDecryption=True)
    return response["Parameter"]["Value"]


def file_setup():
    '''Downloads files from S3 and moves them to lambda tmp/ directory'''
    s3_client = boto3.resource("s3")
    bucket_name = "youtube-uploader-bucket"
    key = "tweet_video.py-oauth2.json"
    try:
        local_file_name = f"/tmp/{key}"
        s3_client.Bucket(bucket_name).download_file(key, local_file_name)
    except Exception as err:
        print(f"Error ocurred while downloading files from S3: {err}")


def lambda_handler(event, context):
    """Main function for lambda to invoke"""
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    file_setup()

    youtube = get_authenticated_service()

    client_id = get_param("twitter_api_key")
    access_token = get_param("twitter_access_token")
    access_token_secret = get_param("twitter_access_token_secret")
    client_secret = get_param("twitter_api_key_secret")

    # Authenticate to Twitter
    auth = tweepy.OAuthHandler(client_id, client_secret)
    auth.set_access_token(access_token, access_token_secret)

    print(auth)

    # Create API object
    twitter_client = tweepy.API(auth)
    print(twitter_client)

    request = youtube.search().list(
        forMine=True, type="video", part="snippet", maxResults=1
    )
    response = request.execute()
    video_id = response["items"][0]["id"]["videoId"]
    channel_id = response["items"][0]["snippet"]["channelId"]
    video_title = response["items"][0]["snippet"]["title"]

    now = datetime.now(gettz("US/Central"))

    print(
        f'Today\'s video is live! Title: "{video_title}" \nWatch here -> https://www.youtube.com/watch?v={video_id} \nPlease support the channel and subscribe! -> https://www.youtube.com/channel/{channel_id} \nDatetime: {now} \n#youtube #python #dailyquote'
    )
    twitter_client.update_status(
        f'Today\'s video is live! Title: "{video_title}" \nWatch here -> https://www.youtube.com/watch?v={video_id} \nPlease support the channel and subscribe! -> https://www.youtube.com/channel/{channel_id} \nDatetime: {now} \n#youtube #python #dailyquote'
    )
