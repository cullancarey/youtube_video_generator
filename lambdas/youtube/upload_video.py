"""Handles YouTube video uploads via Google API"""

import argparse
import http.client
import httplib2
import os
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

REQUIRED_YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class UploadVideo:
    def validate_video_file(self, file_path):
        if not os.path.exists(file_path):
            raise ValueError(f"Invalid file path specified: {file_path}")

        size = os.path.getsize(file_path)
        # Guard against truncated/empty uploads that YouTube later abandons.
        if size < 1024:
            raise ValueError(
                f"Video file is too small to be valid ({size} bytes): {file_path}"
            )

    def get_authenticated_service(self, args):
        httplib2.RETRIES = 1
        client_secrets_file = "/tmp/client_secrets.json"
        logger.info("Authenticating YouTube API client.")
        flow = flow_from_clientsecrets(
            client_secrets_file,
            scope=REQUIRED_YOUTUBE_SCOPES,
            message=(
                f"Missing OAuth configuration in {client_secrets_file}. "
                "Populate this file with your credentials from the Google API Console."
            ),
        )

        storage = Storage("/tmp/youtube_video_generator.py-oauth2.json")
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            logger.info("OAuth credentials missing or invalid. Running auth flow.")
            oauth_args = argparser.parse_args(args=["--noauth_local_webserver"])
            credentials = run_flow(flow, storage, oauth_args)

        # Existing token files can be valid but missing newly required scopes.
        creds_scopes = getattr(credentials, "scopes", None)
        if isinstance(creds_scopes, str):
            creds_scopes = creds_scopes.split()
        elif isinstance(creds_scopes, (list, tuple, set, frozenset)):
            creds_scopes = list(creds_scopes)
        else:
            creds_scopes = []
        creds_scopes = set(creds_scopes)
        missing_scopes = [
            scope for scope in REQUIRED_YOUTUBE_SCOPES if scope not in creds_scopes
        ]
        if missing_scopes:
            raise PermissionError(
                "OAuth token is missing required YouTube scopes. "
                f"Missing: {missing_scopes}. Re-authorize and upload a refreshed "
                "youtube_video_generator.py-oauth2.json to S3."
            )

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
            media_body=MediaFileUpload(
                options.file,
                mimetype="video/mp4",
                chunksize=-1,
                resumable=True,
            ),
        )

        return self.resumable_upload(insert_request)

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
                    return response["id"]
                elif response:
                    logger.critical(f"Upload failed: {response}")
                    raise RuntimeError(f"Upload failed: {response}")
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
                    raise RuntimeError("Max retries exceeded.")
                sleep_time = random.uniform(1, 2**retry)
                logger.info(f"Sleeping {sleep_time:.2f}s before retry...")
                time.sleep(sleep_time)

    def wait_for_processing(
        self,
        youtube,
        video_id,
        timeout_seconds=600,
        poll_interval_seconds=10,
        max_empty_polls=3,
    ):
        start_time = time.time()
        empty_polls = 0
        last_processing_status = None
        last_upload_status = None

        while True:
            try:
                response = (
                    youtube.videos()
                    .list(part="processingDetails,status", id=video_id)
                    .execute()
                )
            except HttpError as err:
                if err.resp.status == 403 and b"insufficientPermissions" in getattr(
                    err, "content", b""
                ):
                    raise PermissionError(
                        "YouTube processing check needs readonly scope. Re-authorize "
                        "youtube_video_generator.py-oauth2.json with both youtube.upload "
                        "and youtube.readonly scopes, then upload it to S3."
                    ) from err
                raise
            items = response.get("items", [])
            if not items:
                empty_polls += 1
                logger.warning(
                    "YouTube status check returned no items for %s (attempt %d/%d).",
                    video_id,
                    empty_polls,
                    max_empty_polls,
                )
                if empty_polls >= max_empty_polls:
                    raise RuntimeError(
                        f"Uploaded video was not found by YouTube API after {max_empty_polls} checks: {video_id}. "
                        f"last_processing_status={last_processing_status}, last_upload_status={last_upload_status}"
                    )

                if time.time() - start_time > timeout_seconds:
                    raise TimeoutError(
                        f"Timed out waiting for YouTube processing for video {video_id}. "
                        f"last_processing_status={last_processing_status}, last_upload_status={last_upload_status}"
                    )

                time.sleep(poll_interval_seconds)
                continue

            empty_polls = 0

            item = items[0]
            processing_details = item.get("processingDetails", {})
            status_details = item.get("status", {})

            processing_status = processing_details.get("processingStatus")
            failure_reason = processing_details.get("processingFailureReason")
            upload_status = status_details.get("uploadStatus")
            last_processing_status = processing_status
            last_upload_status = upload_status

            logger.info(
                "YouTube processing status for %s: processing=%s upload=%s",
                video_id,
                processing_status,
                upload_status,
            )

            if processing_status == "succeeded" and upload_status in (
                None,
                "processed",
            ):
                return

            if processing_status in ("failed", "terminated"):
                raise RuntimeError(
                    f"YouTube processing failed for {video_id}. "
                    f"status={processing_status}, reason={failure_reason}, upload_status={upload_status}"
                )

            if upload_status in ("rejected", "failed", "deleted"):
                raise RuntimeError(
                    f"YouTube upload rejected for {video_id}. upload_status={upload_status}"
                )

            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(
                    f"Timed out waiting for YouTube processing for video {video_id}. "
                    f"last_processing_status={processing_status}, upload_status={upload_status}"
                )

            time.sleep(poll_interval_seconds)

    def execute(self, file, title, description, category, keywords, privacy_status):
        logger.info("Preparing video upload parameters...")

        if isinstance(keywords, (list, tuple)):
            keywords = ",".join(keywords)

        args = argparse.Namespace(
            file=file,
            title=title,
            description=description,
            category=category,
            keywords=keywords,
            privacyStatus=privacy_status,
        )
        logger.info(
            f"Upload arguments: file={args.file}, title={args.title}, privacy={args.privacyStatus}"
        )

        self.validate_video_file(args.file)

        youtube = self.get_authenticated_service(args)
        try:
            video_id = self.initialize_upload(youtube, args)
            self.wait_for_processing(youtube, video_id)
            return video_id
        except HttpError as err:
            logger.error(f"HTTP error {err.resp.status}: {err.content}")
            raise
