import pytest
import requests
from unittest import mock
from lambdas.youtube import youtube_video_generator


@mock.patch("requests.get")
def test_get_image_urls_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "html content"
    result = youtube_video_generator.get_image_urls("python")
    assert result == "html content"
    mock_get.assert_called_once()


@mock.patch("requests.get")
def test_get_image_urls_timeout(mock_get):
    mock_get.side_effect = requests.Timeout
    result = youtube_video_generator.get_image_urls("python")
    assert result is None


@mock.patch("requests.get")
def test_download_image_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = b"image-bytes"
    result = youtube_video_generator.download_image("http://image.com")
    assert result == b"image-bytes"


@mock.patch("boto3.client")
def test_get_param_success(mock_client):
    mock_ssm = mock.Mock()
    mock_client.return_value = mock_ssm
    mock_ssm.get_parameter.return_value = {"Parameter": {"Value": "abc"}}
    assert youtube_video_generator.get_param("reddit_client_id") == "abc"


@mock.patch("boto3.resource")
def test_file_setup_downloads(mock_resource):
    mock_s3 = mock.Mock()
    mock_bucket = mock.Mock()
    mock_resource.return_value = mock_s3
    mock_s3.Bucket.return_value = mock_bucket

    youtube_video_generator.file_setup()
    assert mock_bucket.download_file.call_count == 5


@mock.patch("lambdas.youtube.youtube_video_generator.UploadVideo")
@mock.patch("lambdas.youtube.youtube_video_generator.get_param", return_value="val")
@mock.patch("lambdas.youtube.youtube_video_generator.praw.Reddit")
@mock.patch(
    "lambdas.youtube.youtube_video_generator.get_image_urls",
    return_value="https://encrypted-image.jpg",
)
@mock.patch(
    "lambdas.youtube.youtube_video_generator.download_image", return_value=b"bytes"
)
@mock.patch("lambdas.youtube.youtube_video_generator.gTTS")
@mock.patch("lambdas.youtube.youtube_video_generator.MP3")
@mock.patch("lambdas.youtube.youtube_video_generator.subprocess.run")
@mock.patch("lambdas.youtube.youtube_video_generator.file_setup")
def test_lambda_handler_minimal_path(
    mock_file_setup,
    mock_subproc,
    mock_mp3,
    mock_gtts,
    mock_download,
    mock_img_urls,
    mock_reddit,
    mock_param,
    mock_uploader,
):
    mock_subproc.return_value.returncode = 0
    mock_mp3.return_value.info.length = 1

    mock_post = mock.Mock()
    mock_post.over_18 = False
    mock_post.title = "Title"
    mock_post.selftext = "Text"
    mock_post.author = "author"
    mock_post.url = "url"
    mock_reddit.return_value.subreddit.return_value.new.return_value = [mock_post]

    youtube_video_generator.lambda_handler({}, {})
    assert mock_param.call_count >= 5
    assert mock_gtts.called
    assert mock_uploader.return_value.execute.called
