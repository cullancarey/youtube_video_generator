import pytest
from unittest import mock
from lambdas.tweet import tweet_youtube_video


def test_extract_keywords_from_text_basic():
    text = "This is a video about Python development and automation tools"
    keywords = tweet_youtube_video.extract_keywords_from_text(text)
    assert "#video" in keywords
    assert "#python" in keywords
    assert len(keywords) <= 5


def test_extract_keywords_handles_empty_text():
    assert tweet_youtube_video.extract_keywords_from_text("") == []


def test_extract_keywords_ignores_stopwords_only():
    text = "the a of in on and to for is with this that your"
    assert tweet_youtube_video.extract_keywords_from_text(text) == []


def test_extract_keywords_limits_to_max():
    text = "Python automation development deployment APIs Lambda serverless cloud AWS"
    keywords = tweet_youtube_video.extract_keywords_from_text(text, max_keywords=3)
    assert len(keywords) == 3


@mock.patch("boto3.client")
def test_get_param_returns_value(mock_boto_client):
    mock_ssm = mock.Mock()
    mock_boto_client.return_value = mock_ssm
    mock_ssm.get_parameter.return_value = {"Parameter": {"Value": "mocked_value"}}

    value = tweet_youtube_video.get_param("some-param")
    assert value == "mocked_value"
    mock_ssm.get_parameter.assert_called_with(Name="some-param", WithDecryption=True)


@mock.patch("boto3.client")
def test_get_param_handles_exception(mock_boto_client):
    mock_ssm = mock.Mock()
    mock_boto_client.return_value = mock_ssm
    mock_ssm.get_parameter.side_effect = Exception("Simulated failure")
    value = tweet_youtube_video.get_param("fail-param")
    assert value is None


@mock.patch("boto3.resource")
def test_file_setup_handles_s3_download_failure(mock_boto_resource):
    mock_s3 = mock.Mock()
    mock_bucket = mock.Mock()
    mock_bucket.download_file.side_effect = Exception("Download fail")
    mock_s3.Bucket.return_value = mock_bucket
    mock_boto_resource.return_value = mock_s3
    tweet_youtube_video.file_setup()
    assert mock_bucket.download_file.call_count == 2


@mock.patch("boto3.resource")
def test_file_setup_downloads_files(mock_boto_resource):
    mock_s3 = mock.Mock()
    mock_bucket = mock.Mock()
    mock_s3.Bucket.return_value = mock_bucket
    mock_boto_resource.return_value = mock_s3

    tweet_youtube_video.file_setup()
    assert mock_bucket.download_file.call_count == 2


@mock.patch("tweepy.Client")
@mock.patch("lambdas.tweet.tweet_youtube_video.get_param")
@mock.patch("lambdas.tweet.tweet_youtube_video.get_authenticated_service")
@mock.patch("lambdas.tweet.tweet_youtube_video.file_setup")
def test_lambda_handler_gracefully_handles_no_youtube_results(
    mock_file_setup, mock_get_auth, mock_get_param, mock_tweepy_client
):
    mock_get_param.return_value = "fake_value"
    mock_file_setup.return_value = None

    mock_youtube = mock.Mock()
    mock_request = mock.Mock()
    mock_youtube.search.return_value.list.return_value = mock_request
    mock_request.execute.return_value = {"items": []}
    mock_get_auth.return_value = mock_youtube

    tweet_youtube_video.lambda_handler({}, {})
    # If this runs without error, test passes since no tweet should be attempted
    mock_tweepy_client.return_value.create_tweet.assert_not_called()


@mock.patch("tweepy.Client")
@mock.patch("lambdas.tweet.tweet_youtube_video.get_param")
@mock.patch("lambdas.tweet.tweet_youtube_video.get_authenticated_service")
@mock.patch("lambdas.tweet.tweet_youtube_video.file_setup")
def test_lambda_handler_posts_tweet(
    mock_file_setup, mock_get_auth, mock_get_param, mock_tweepy_client
):
    mock_get_param.return_value = "fake_value"
    mock_file_setup.return_value = None

    mock_youtube = mock.Mock()
    mock_request = mock.Mock()
    mock_youtube.search.return_value.list.return_value = mock_request
    mock_request.execute.return_value = {
        "items": [
            {
                "id": {"videoId": "abc123"},
                "snippet": {
                    "channelId": "chan456",
                    "title": "Test Video",
                    "description": "Testing API keywords",
                },
            }
        ]
    }
    mock_get_auth.return_value = mock_youtube

    mock_client_instance = mock.Mock()
    mock_tweepy_client.return_value = mock_client_instance

    tweet_youtube_video.lambda_handler({}, {})

    mock_client_instance.create_tweet.assert_called_once()
    _, kwargs = mock_client_instance.create_tweet.call_args
    assert "Test Video" in kwargs["text"]
    assert "https://www.youtube.com/watch?v=abc123" in kwargs["text"]
