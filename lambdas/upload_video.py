"""This module defines classes that implement the client side of the HTTP and HTTPS protocols"""
import http.client
import httplib2
import os
import sys
import random
import time

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


class UploadVideo:
    """Class to upload video to youtube"""

    def get_authenticated_service(self, args):
        """Function used to authenticate to the third party platform"""
        # Explicitly tell the underlying HTTP transport library not to retry, since
        # we are handling retry logic ourselves.
        httplib2.RETRIES = 1
        client_secrets_file = f"{os.getcwd()}/client_secrets.json"
        youtube_upload_scope = "https://www.googleapis.com/auth/youtube.upload"
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

        storage = Storage("/tmp/main.py-oauth2.json")
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage, args)

        return build(
            youtube_api_service_name,
            youtube_api_version,
            http=credentials.authorize(httplib2.Http()),
        )

    def initialize_upload(self, youtube, options):
        """Starts upload of youtube video"""
        tags = None
        if options.keywords:
            tags = options.keywords.split(",")

        body = dict(
            snippet=dict(
                title=options.title,
                description=options.description,
                tags=tags,
                categoryId=options.category,
            ),
            status=dict(privacyStatus=options.privacyStatus),
        )

        # Call the API's videos.insert method to create and upload the video.
        insert_request = youtube.videos().insert(
            part=",".join(list(body.keys())),
            body=body,
            # The chunksize parameter specifies the size of each chunk of data, in
            # bytes, that will be uploaded at a time. Set a higher value for
            # reliable connections as fewer chunks lead to faster uploads. Set a lower
            # value for better recovery on less reliable connections.
            #
            # Setting "chunksize" equal to -1 in the code below means that the entire
            # file will be uploaded in a single HTTP request. (If the upload fails,
            # it will still be retried where it left off.) This is usually a best
            # practice, but if you're using Python older than 2.6 or if you're
            # running on App Engine, you should set the chunksize to something like
            # 1024 * 1024 (1 megabyte).
            media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True),
        )

        self.resumable_upload(insert_request)

    # This method implements an exponential backoff strategy to resume a
    # failed upload.
    def resumable_upload(self, insert_request):
        """This method implements an exponential backoff strategy to resume a failed upload."""
        # Always retry when these exceptions are raised.
        retriable_execptions = (
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
        # Always retry when an apiclient.errors.HttpError with one of these status
        # codes is raised.
        retriable_status_codes = [500, 502, 503, 504]
        # Maximum number of times to retry before giving up.
        max_retries = 10
        response = None
        error = None
        retry = 0
        while response is None:
            try:
                print("Uploading file...")
                status, response = insert_request.next_chunk()
                print(f"File upload status: {status}")
                if response is not None:
                    if "id" in response:
                        print(
                            (f"Video id '{response['id']}' was successfully uploaded.")
                        )
                    else:
                        sys.exit(
                            f"The upload failed with an unexpected response: {response}"
                        )
            except HttpError as err:
                if err.resp.status in retriable_status_codes:
                    error = f"A retriable HTTP error {err.resp.status} occurred:\n{err.content}"
                else:
                    raise
            except retriable_execptions as err:
                error = f"A retriable error occurred: {err}"
            if error is not None:
                print(error)
                retry += 1
                if retry > max_retries:
                    sys.exit("No longer attempting to retry.")

                max_sleep = 2**retry
                sleep_seconds = random.random() * max_sleep
                print(f"Sleeping {sleep_seconds} seconds and then retrying...")
                time.sleep(sleep_seconds)

    def execute(self, file, title, description, category, keywords, privacy_status):
        """Function to upload video to youtube"""
        valid_privacy_statuses = ("public", "private", "unlisted")
        argparser.add_argument("--file", default=file, help=f"{file}")
        argparser.add_argument("--title", help=f"{title}", default=f"{title}")
        argparser.add_argument(
            "--description", default=f"{description}", help=f"{description}"
        )
        argparser.add_argument(
            "--category",
            default="22",
            help=f"{category}"
            + "See https://developers.google.com/youtube/v3/docs/videoCategories/list",
        )
        argparser.add_argument("--keywords", default=f"{keywords}", help=f"{keywords}")
        argparser.add_argument(
            "--privacyStatus",
            choices=valid_privacy_statuses,
            default=valid_privacy_statuses[0],
            help=f"{privacy_status}",
        )
        args = argparser.parse_args()
        print(args)

        if not os.path.exists(args.file):
            sys.exit("Please specify a valid file using the --file= parameter.")

        youtube = self.get_authenticated_service(args)
        try:
            self.initialize_upload(youtube, args)
            # print(youtube, args)
        except HttpError as err:
            print((f"An HTTP error {err.resp.status} occurred:\n{err.content}"))
