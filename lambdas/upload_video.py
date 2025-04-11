"""Handles YouTube video uploads via Google API"""

import http.client
import httplib2
import os
import sys
import random
import time
import logging

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

logger = logging.getLogger()
logger.setLevel("INFO")


class UploadVideo:
    def get_authenticated_service(self, args):
        httplib2.RETRIES = 1
        client_secrets_file = "/tmp/client_secrets.json"
        logger.info("Authenticating YouTube API client.")
        flow = flow_from_clientsecrets(
            client_secrets_file,
            scope="https://www.googleapis.com/auth/youtube.upload",
            message=(
                f"Missing OAuth configuration in {client_secrets_file}. "
                "Populate this file with your credentials from the Google API Console."
            ),
        )

        storage = Storage("/tmp/youtube_video_generator.py-oauth2.json")
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            logger.info("OAuth credentials missing or invalid. Running auth flow.")
            credentials = run_flow(flow, storage, args)

        logger.info("Successfully authenticated with YouTube API.")
        return build("youtube", "v3", http=credentials.authorize(httplib2.Http()))

    def initialize_upload(self, youtube, options):
        tags = options.keywords.split(",") if options.keywords else None

        body = {
            "snippet": {
                "title": options.title,
                "description": options.description,
                "tags": tags,
                "categoryId": options.category,
            },
            "status": {"privacyStatus": options.privacyStatus},
        }

        logger.info(f"Initializing upload: {body['snippet']['title']}")
        insert_request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True),
        )

        self.resumable_upload(insert_request)

    def resumable_upload(self, insert_request):
        retriable_exceptions = (
            httplib2.HttpLib2Error,
            IOError,
            http.client.NotConnected,
            http.client.IncompleteRead,
            http.client.ImproperConnectionState,
            http.client.CannotSendRequest,
            http.client.CannotSendHeader,
            http.client.ResponseNotReady,
            http.client.BadStatusLine,
        )
        retriable_status_codes = [500, 502, 503, 504]
        max_retries = 10
        response = None
        error = None
        retry = 0

        while response is None:
            try:
                logger.info("Uploading file...")
                status, response = insert_request.next_chunk()
                if response and "id" in response:
                    logger.info(f"Video id '{response['id']}' uploaded successfully.")
                elif response:
                    logger.critical(f"Upload failed: {response}")
                    sys.exit(f"Upload failed: {response}")
            except HttpError as err:
                if err.resp.status in retriable_status_codes:
                    error = f"Retriable HTTP error {err.resp.status}: {err.content}"
                else:
                    raise
            except retriable_exceptions as err:
                error = f"Retriable error: {err}"

            if error:
                logger.warning(error)
                retry += 1
                if retry > max_retries:
                    logger.critical("Max retries exceeded.")
                    sys.exit("Max retries exceeded.")
                sleep_time = random.uniform(1, 2**retry)
                logger.info(f"Sleeping {sleep_time:.2f}s before retry...")
                time.sleep(sleep_time)

    def execute(self, file, title, description, category, keywords, privacy_status):
        logger.info("Preparing video upload parameters...")

        if isinstance(keywords, (list, tuple)):
            keywords = ",".join(keywords)

        argparser.add_argument("--file", default=file, help="Video file to upload")
        argparser.add_argument("--title", default=title, help="Video title")
        argparser.add_argument(
            "--description", default=description, help="Video description"
        )
        argparser.add_argument(
            "--category", default=category, help="YouTube video category ID"
        )
        argparser.add_argument(
            "--keywords", default=keywords, help="Comma-separated keywords/tags"
        )
        argparser.add_argument(
            "--privacyStatus",
            choices=("public", "private", "unlisted"),
            default=privacy_status,
            help="Privacy status of the video",
        )

        args = argparser.parse_args()
        logger.info(
            f"Upload arguments: file={args.file}, title={args.title}, privacy={args.privacyStatus}"
        )

        if not os.path.exists(args.file):
            logger.critical("Invalid file path specified.")
            sys.exit("Invalid file path specified.")

        youtube = self.get_authenticated_service(args)
        try:
            self.initialize_upload(youtube, args)
        except HttpError as err:
            logger.error(f"HTTP error {err.resp.status}: {err.content}")
