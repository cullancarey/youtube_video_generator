import pytest
from unittest import mock
from lambdas.youtube.upload_video import UploadVideo
from oauth2client.client import OAuth2Credentials


@mock.patch("lambdas.youtube.upload_video.Storage")
@mock.patch("lambdas.youtube.upload_video.flow_from_clientsecrets")
@mock.patch("lambdas.youtube.upload_video.build")
def test_get_authenticated_service(mock_build, mock_flow, mock_storage):
    flow = mock.Mock()
    mock_flow.return_value = flow
    creds = mock.Mock(invalid=False)
    creds.scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]
    mock_storage.return_value.get.return_value = creds

    uploader = UploadVideo()
    result = uploader.get_authenticated_service(args=[])
    assert result == mock_build.return_value
    mock_build.assert_called_once()
    assert mock_flow.call_args.kwargs["scope"] == [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]


@mock.patch("lambdas.youtube.upload_video.MediaFileUpload")
@mock.patch("lambdas.youtube.upload_video.UploadVideo.resumable_upload")
def test_initialize_upload_calls_insert(mock_upload, mock_media):
    uploader = UploadVideo()
    youtube = mock.Mock()
    insert_mock = youtube.videos.return_value.insert
    options = mock.Mock(
        title="T",
        description="D",
        keywords="tag1,tag2",
        category="22",
        privacyStatus="public",
        file="f.mp4",
    )
    uploader.initialize_upload(youtube, options)
    insert_mock.assert_called_once()
    mock_upload.assert_called_once()


@mock.patch("lambdas.youtube.upload_video.UploadVideo.get_authenticated_service")
@mock.patch("lambdas.youtube.upload_video.UploadVideo.initialize_upload")
@mock.patch("lambdas.youtube.upload_video.UploadVideo.wait_for_processing")
@mock.patch("lambdas.youtube.upload_video.os.path.getsize", return_value=4096)
@mock.patch("lambdas.youtube.upload_video.os.path.exists", return_value=True)
def test_execute_calls_upload(
    mock_exists, mock_getsize, mock_wait, mock_init, mock_auth
):
    uploader = UploadVideo()
    mock_init.return_value = "video123"
    video_id = uploader.execute("file.mp4", "t", "d", "22", ["kw1", "kw2"], "public")
    assert mock_init.called
    assert mock_wait.called
    assert video_id == "video123"


@mock.patch("lambdas.youtube.upload_video.run_flow")
@mock.patch("lambdas.youtube.upload_video.Storage")
@mock.patch("lambdas.youtube.upload_video.flow_from_clientsecrets")
@mock.patch("lambdas.youtube.upload_video.build")
def test_get_authenticated_service_invalid_creds(
    mock_build, mock_flow, mock_storage, mock_run_flow
):
    uploader = UploadVideo()

    mock_creds = mock.Mock(spec=OAuth2Credentials)
    mock_creds.invalid = True
    mock_creds.scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]
    mock_storage.return_value.get.return_value = mock_creds
    mock_run_flow.return_value = mock_creds

    args = mock.Mock()
    uploader.get_authenticated_service(args)

    mock_flow.assert_called_once()
    mock_run_flow.assert_called_once()
    mock_build.assert_called_once()


@mock.patch("lambdas.youtube.upload_video.MediaFileUpload")
@mock.patch("lambdas.youtube.upload_video.build")
def test_initialize_upload_uses_correct_params(mock_build, mock_media_upload):
    uploader = UploadVideo()
    mock_youtube = mock.Mock()
    mock_build.return_value = mock_youtube

    insert_request = mock_youtube.videos.return_value.insert.return_value
    insert_request.next_chunk.return_value = (
        None,
        {"id": "mocked_video_id"},
    )

    options = mock.Mock()
    options.file = "video.mp4"
    options.title = "Test"
    options.description = "Description"
    options.keywords = "tag1,tag2"
    options.category = "22"
    options.privacyStatus = "public"

    uploader.initialize_upload(mock_youtube, options)

    mock_youtube.videos.return_value.insert.assert_called_once()
    insert_call = mock_youtube.videos.return_value.insert.call_args
    assert "snippet" in insert_call.kwargs["body"]


@mock.patch("lambdas.youtube.upload_video.os.path.exists")
def test_execute_fails_if_file_missing(mock_exists):
    mock_exists.return_value = False
    uploader = UploadVideo()

    with pytest.raises(ValueError):
        uploader.execute("missing.mp4", "Title", "Desc", "22", ["tag"], "public")


def test_wait_for_processing_succeeds():
    uploader = UploadVideo()
    youtube = mock.Mock()
    youtube.videos.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "processingDetails": {"processingStatus": "succeeded"},
                "status": {"uploadStatus": "processed"},
            }
        ]
    }

    uploader.wait_for_processing(
        youtube, "video123", timeout_seconds=1, poll_interval_seconds=0
    )


def test_wait_for_processing_fails_on_failed_status():
    uploader = UploadVideo()
    youtube = mock.Mock()
    youtube.videos.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "processingDetails": {
                    "processingStatus": "failed",
                    "processingFailureReason": "invalidFile",
                },
                "status": {"uploadStatus": "failed"},
            }
        ]
    }

    with pytest.raises(RuntimeError):
        uploader.wait_for_processing(
            youtube, "video123", timeout_seconds=1, poll_interval_seconds=0
        )


def test_wait_for_processing_tolerates_transient_empty_items():
    uploader = UploadVideo()
    youtube = mock.Mock()
    youtube.videos.return_value.list.return_value.execute.side_effect = [
        {
            "items": [
                {
                    "processingDetails": {"processingStatus": "processing"},
                    "status": {"uploadStatus": "uploaded"},
                }
            ]
        },
        {"items": []},
        {
            "items": [
                {
                    "processingDetails": {"processingStatus": "succeeded"},
                    "status": {"uploadStatus": "processed"},
                }
            ]
        },
    ]

    uploader.wait_for_processing(
        youtube,
        "video123",
        timeout_seconds=1,
        poll_interval_seconds=0,
        max_empty_polls=3,
    )


def test_wait_for_processing_fails_after_repeated_empty_items():
    uploader = UploadVideo()
    youtube = mock.Mock()
    youtube.videos.return_value.list.return_value.execute.return_value = {"items": []}

    with pytest.raises(RuntimeError):
        uploader.wait_for_processing(
            youtube,
            "video123",
            timeout_seconds=1,
            poll_interval_seconds=0,
            max_empty_polls=2,
        )
