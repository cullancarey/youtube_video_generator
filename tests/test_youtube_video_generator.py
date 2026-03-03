import logging
import sys
import pytest
import requests
from unittest import mock
from lambdas.youtube import youtube_video_generator

# Configure root logger to print everything to stdout immediately
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
    stream=sys.stdout,
    force=True,
)


@mock.patch("requests.get")
def test_get_images_unsplash_success(mock_get):
    """Test successful image retrieval from Unsplash API."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "results": [
            {"urls": {"regular": "https://unsplash.com/photo1.jpg"}},
            {"urls": {"regular": "https://unsplash.com/photo2.jpg"}},
        ]
    }
    result = youtube_video_generator.get_images_unsplash("motivation", num_images=2)
    assert len(result) == 2
    assert result[0] == "https://unsplash.com/photo1.jpg"
    mock_get.assert_called_once()


@mock.patch("requests.get")
def test_get_images_unsplash_no_results(mock_get):
    """Test Unsplash API returning empty results."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"results": []}
    result = youtube_video_generator.get_images_unsplash("xyz123xyz", num_images=5)
    assert result == []


@mock.patch("requests.get")
def test_get_images_unsplash_api_error(mock_get):
    """Test Unsplash API returning error status."""
    mock_get.return_value.status_code = 500
    result = youtube_video_generator.get_images_unsplash("python", num_images=5)
    assert result == []


@mock.patch("requests.get")
def test_get_images_unsplash_timeout(mock_get):
    """Test Unsplash API timeout handling."""
    mock_get.side_effect = requests.Timeout
    result = youtube_video_generator.get_images_unsplash("python", num_images=5)
    assert result == []


@mock.patch("requests.get")
def test_download_image_success(mock_get):
    """Test successful image download."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = b"image-bytes"
    result = youtube_video_generator.download_image("http://image.com")
    assert result == b"image-bytes"


@mock.patch("requests.get")
def test_download_image_timeout(mock_get):
    """Test image download timeout handling."""
    mock_get.side_effect = requests.Timeout
    result = youtube_video_generator.download_image("http://image.com")
    assert result is None


@mock.patch("requests.get")
def test_download_image_error(mock_get):
    """Test image download error handling."""
    mock_get.return_value.status_code = 404
    result = youtube_video_generator.download_image("http://image.com")
    assert result is None


@mock.patch("builtins.open", new_callable=mock.mock_open)
@mock.patch("boto3.client")
def test_generate_audio_with_polly_success(mock_client, mock_file):
    """Test successful audio generation with AWS Polly."""
    mock_polly = mock.Mock()
    mock_client.return_value = mock_polly
    mock_polly.synthesize_speech.return_value = {
        "AudioStream": mock.Mock(read=mock.Mock(return_value=b"mp3-bytes"))
    }

    youtube_video_generator.generate_audio_with_polly("Test quote text")

    mock_client.assert_called_once_with("polly", region_name="us-east-2")
    mock_polly.synthesize_speech.assert_called_once()
    call_kwargs = mock_polly.synthesize_speech.call_args[1]
    assert call_kwargs["Text"] == "Test quote text"
    assert call_kwargs["VoiceId"] == "Joanna"
    assert call_kwargs["Engine"] == "neural"


@mock.patch("boto3.client")
def test_generate_audio_with_polly_failure(mock_client):
    """Test Polly audio generation failure."""
    mock_polly = mock.Mock()
    mock_client.return_value = mock_polly
    mock_polly.synthesize_speech.side_effect = Exception("Polly error")

    with pytest.raises(Exception):
        youtube_video_generator.generate_audio_with_polly("Test quote")


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
    "lambdas.youtube.youtube_video_generator.get_images_unsplash",
    return_value=["https://unsplash.com/photo1.jpg"],
)
@mock.patch(
    "lambdas.youtube.youtube_video_generator.download_image", return_value=b"bytes"
)
@mock.patch("lambdas.youtube.youtube_video_generator.generate_audio_with_polly")
@mock.patch("lambdas.youtube.youtube_video_generator.MP3")
@mock.patch("lambdas.youtube.youtube_video_generator.subprocess.run")
@mock.patch("lambdas.youtube.youtube_video_generator.file_setup")
def test_lambda_handler_minimal_path(
    mock_file_setup,
    mock_subproc,
    mock_mp3,
    mock_polly,
    mock_download,
    mock_unsplash,
    mock_reddit,
    mock_param,
    mock_uploader,
):
    """Test successful lambda execution with Polly TTS and Unsplash images."""
    mock_subproc.return_value.returncode = 0
    mock_mp3.return_value.info.length = 10  # 10 second audio = 10 images
    mock_polly.return_value = None

    mock_post = mock.Mock()
    mock_post.over_18 = False
    mock_post.title = "Test Quote"
    mock_post.selftext = "This is a test"
    mock_post.author = "TestAuthor"
    mock_post.url = "https://reddit.com/test"
    mock_reddit.return_value.subreddit.return_value.new.return_value = [mock_post]

    youtube_video_generator.lambda_handler({}, {})

    # Verify Polly was called instead of gTTS
    assert mock_polly.called
    # Verify Unsplash was called instead of Google scraping
    assert mock_unsplash.called
    # Verify upload was called
    assert mock_uploader.return_value.execute.called
    # Verify param retrieval
    assert mock_param.call_count >= 5


@mock.patch("lambdas.youtube.youtube_video_generator.file_setup")
@mock.patch("lambdas.youtube.youtube_video_generator.get_param", return_value=None)
@mock.patch("lambdas.youtube.youtube_video_generator.praw.Reddit")
@mock.patch("lambdas.youtube.youtube_video_generator.generate_audio_with_polly")
@mock.patch("lambdas.youtube.youtube_video_generator.UploadVideo")
def test_lambda_handler_reddit_init_failure(
    mock_uploader, mock_polly, mock_reddit, mock_param, mock_file_setup
):
    """Test lambda handler when Reddit initialization fails."""
    # Configure Reddit mock to raise an exception
    mock_reddit.side_effect = Exception("Reddit init failed")

    youtube_video_generator.lambda_handler({}, {})

    # Verify Reddit init was attempted
    assert mock_reddit.call_count >= 1
    # Verify lambda didn't proceed to upload (should return early on Reddit failure)
    assert not mock_uploader.return_value.execute.called
