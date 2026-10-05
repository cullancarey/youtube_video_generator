import logging
import sys
import os
import pytest
from unittest import mock
from lambdas.youtube import youtube_video_generator

# Configure root logger to print everything to stdout immediately
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
    stream=sys.stdout,
    force=True,
)


def test_build_image_urls_count_and_shape():
    urls = youtube_video_generator.build_image_urls("python quote", 3)
    assert len(urls) == 3
    assert all(u.startswith("https://picsum.photos/seed/") for u in urls)


def test_build_image_urls_deterministic_for_same_text():
    urls_one = youtube_video_generator.build_image_urls("same text", 2)
    urls_two = youtube_video_generator.build_image_urls("same text", 2)
    assert urls_one == urls_two


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


def _make_post(post_id, title, selftext="", over_18=False):
    post = mock.Mock()
    post.id = post_id
    post.title = title
    post.selftext = selftext
    post.over_18 = over_18
    return post


@mock.patch("boto3.resource")
def test_load_post_history_missing_file_returns_empty(mock_resource):
    from botocore.exceptions import ClientError

    mock_resource.return_value.Bucket.return_value.download_file.side_effect = (
        ClientError({"Error": {"Code": "404"}}, "download_file")
    )
    assert youtube_video_generator.load_post_history() == {}


@mock.patch("boto3.resource")
def test_save_post_history_prunes_old_entries(mock_resource, tmp_path):
    import json
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    history = {
        "recent": (now - timedelta(days=1)).isoformat(),
        "ancient": (now - timedelta(days=400)).isoformat(),
    }

    youtube_video_generator.save_post_history(history)

    with open(youtube_video_generator.POST_HISTORY_PATH, encoding="utf-8") as f:
        saved = json.load(f)
    assert "recent" in saved
    assert "ancient" not in saved
    mock_resource.return_value.Bucket.return_value.upload_file.assert_called_once()


def test_select_safe_post_prefers_top_tier_over_new():
    top_post = _make_post("top1", "Believe in yourself")
    new_post = _make_post("new1", "Another quote")

    reddit = mock.Mock()
    reddit.subreddit.return_value.top.return_value = [top_post]
    reddit.subreddit.return_value.new.return_value = [new_post]

    selected = youtube_video_generator.select_safe_post(reddit, used_post_ids=set())
    assert selected is top_post


def test_select_safe_post_skips_used_posts():
    used_post = _make_post("used1", "Already posted this one")
    fresh_post = _make_post("fresh1", "A brand new quote")

    reddit = mock.Mock()
    reddit.subreddit.return_value.top.return_value = [used_post, fresh_post]
    reddit.subreddit.return_value.new.return_value = []

    selected = youtube_video_generator.select_safe_post(reddit, used_post_ids={"used1"})
    assert selected is fresh_post


def test_select_safe_post_falls_back_to_new_when_top_tiers_empty():
    new_post = _make_post("new1", "Fallback quote")

    reddit = mock.Mock()
    reddit.subreddit.return_value.top.return_value = []
    reddit.subreddit.return_value.new.return_value = [new_post]

    selected = youtube_video_generator.select_safe_post(reddit, used_post_ids=set())
    assert selected is new_post


def test_select_safe_post_returns_none_when_all_filtered_out():
    nsfw_post = _make_post("nsfw1", "Not safe", over_18=True)
    flagged_post = _make_post("flagged1", "Mentions Adolf Hitler")

    reddit = mock.Mock()
    reddit.subreddit.return_value.top.return_value = [nsfw_post, flagged_post]
    reddit.subreddit.return_value.new.return_value = []

    selected = youtube_video_generator.select_safe_post(reddit, used_post_ids=set())
    assert selected is None


@mock.patch("lambdas.youtube.youtube_video_generator.save_post_history")
@mock.patch(
    "lambdas.youtube.youtube_video_generator.load_post_history", return_value={}
)
@mock.patch("lambdas.youtube.youtube_video_generator.UploadVideo")
@mock.patch("lambdas.youtube.youtube_video_generator.get_param", return_value="val")
@mock.patch("lambdas.youtube.youtube_video_generator.praw.Reddit")
@mock.patch(
    "lambdas.youtube.youtube_video_generator.build_image_urls",
    return_value=["https://picsum.photos/seed/1/1280/720"],
)
@mock.patch(
    "lambdas.youtube.youtube_video_generator.download_image",
    return_value=b"\xff\xd8\xff\xe0mockjpg",
)
@mock.patch("lambdas.youtube.youtube_video_generator.gTTS")
@mock.patch("lambdas.youtube.youtube_video_generator.MP3")
@mock.patch("lambdas.youtube.youtube_video_generator.subprocess.run")
@mock.patch("lambdas.youtube.youtube_video_generator.os.path.exists", return_value=True)
@mock.patch(
    "lambdas.youtube.youtube_video_generator.os.path.getsize", return_value=2048
)
@mock.patch("lambdas.youtube.youtube_video_generator.file_setup")
def test_lambda_handler_minimal_path(
    mock_file_setup,
    mock_getsize,
    mock_exists,
    mock_subproc,
    mock_mp3,
    mock_gtts,
    mock_download,
    mock_build_urls,
    mock_reddit,
    mock_param,
    mock_uploader,
    mock_load_history,
    mock_save_history,
):
    mock_subproc.return_value.returncode = 0
    mock_mp3.return_value.info.length = 1
    mock_gtts.return_value.save.return_value = None
    mock_gtts.return_value.lang_check.return_value = True

    mock_post = mock.Mock()
    mock_post.id = "post1"
    mock_post.over_18 = False
    mock_post.title = "Title"
    mock_post.selftext = "Text"
    mock_post.author = "author"
    mock_post.url = "url"
    mock_post.permalink = "/r/quotes/comments/abc123/test"
    mock_reddit.return_value.subreddit.return_value.new.return_value = [mock_post]

    youtube_video_generator.lambda_handler({}, {})
    assert mock_param.call_count >= 5
    assert mock_gtts.called
    assert mock_uploader.return_value.execute.called
    assert mock_save_history.called


@mock.patch("lambdas.youtube.youtube_video_generator.save_post_history")
@mock.patch(
    "lambdas.youtube.youtube_video_generator.load_post_history", return_value={}
)
@mock.patch("lambdas.youtube.youtube_video_generator.UploadVideo")
@mock.patch("lambdas.youtube.youtube_video_generator.get_param", return_value="val")
@mock.patch("lambdas.youtube.youtube_video_generator.praw.Reddit")
@mock.patch(
    "lambdas.youtube.youtube_video_generator.build_image_urls",
    return_value=["https://picsum.photos/seed/1/1280/720"],
)
@mock.patch(
    "lambdas.youtube.youtube_video_generator.download_image",
    return_value=b"\xff\xd8\xff\xe0mockjpg",
)
@mock.patch("lambdas.youtube.youtube_video_generator.gTTS")
@mock.patch("lambdas.youtube.youtube_video_generator.MP3")
@mock.patch("lambdas.youtube.youtube_video_generator.subprocess.run")
@mock.patch("lambdas.youtube.youtube_video_generator.os.path.exists", return_value=True)
@mock.patch(
    "lambdas.youtube.youtube_video_generator.os.path.getsize", return_value=2048
)
@mock.patch("lambdas.youtube.youtube_video_generator.file_setup")
def test_lambda_handler_skips_denylisted_post_for_next_candidate(
    mock_file_setup,
    mock_getsize,
    mock_exists,
    mock_subproc,
    mock_mp3,
    mock_gtts,
    mock_download,
    mock_build_urls,
    mock_reddit,
    mock_param,
    mock_uploader,
    mock_load_history,
    mock_save_history,
):
    mock_subproc.return_value.returncode = 0
    mock_mp3.return_value.info.length = 1
    mock_gtts.return_value.save.return_value = None
    os.makedirs("/tmp/images", exist_ok=True)

    flagged_post = mock.Mock()
    flagged_post.id = "flagged"
    flagged_post.over_18 = False
    flagged_post.title = "A quote from Adolf Hitler"
    flagged_post.selftext = ""
    flagged_post.author = "baduser"
    flagged_post.permalink = "/r/quotes/comments/flagged/test"

    clean_post = mock.Mock()
    clean_post.id = "clean"
    clean_post.over_18 = False
    clean_post.title = "Believe in yourself"
    clean_post.selftext = "You can do it"
    clean_post.author = "gooduser"
    clean_post.permalink = "/r/quotes/comments/clean/test"

    mock_reddit.return_value.subreddit.return_value.new.return_value = [
        flagged_post,
        clean_post,
    ]

    youtube_video_generator.lambda_handler({}, {})

    execute_args = mock_uploader.return_value.execute.call_args.args
    uploaded_description = execute_args[2]
    assert "Hitler" not in uploaded_description
    assert "gooduser" in uploaded_description


@mock.patch(
    "lambdas.youtube.youtube_video_generator.load_post_history", return_value={}
)
@mock.patch("lambdas.youtube.youtube_video_generator.praw.Reddit")
@mock.patch("lambdas.youtube.youtube_video_generator.get_param", return_value="val")
@mock.patch("lambdas.youtube.youtube_video_generator.file_setup")
def test_lambda_handler_raises_when_all_candidates_flagged(
    mock_file_setup, mock_param, mock_reddit, mock_load_history
):
    flagged_post = mock.Mock()
    flagged_post.id = "flagged"
    flagged_post.over_18 = False
    flagged_post.title = "Praising the Nazi regime"
    flagged_post.selftext = ""

    mock_reddit.return_value.subreddit.return_value.new.return_value = [flagged_post]

    with pytest.raises(RuntimeError, match="No safe, unused Reddit post found"):
        youtube_video_generator.lambda_handler({}, {})


@mock.patch("lambdas.youtube.youtube_video_generator.file_setup")
def test_lambda_handler_raises_when_setup_fails(mock_file_setup):
    mock_file_setup.side_effect = RuntimeError("setup-failed")

    with pytest.raises(RuntimeError, match="setup-failed"):
        youtube_video_generator.lambda_handler({}, {})


@mock.patch("lambdas.youtube.youtube_video_generator.save_post_history")
@mock.patch(
    "lambdas.youtube.youtube_video_generator.load_post_history", return_value={}
)
@mock.patch("lambdas.youtube.youtube_video_generator.UploadVideo")
@mock.patch("lambdas.youtube.youtube_video_generator.get_param", return_value="val")
@mock.patch("lambdas.youtube.youtube_video_generator.praw.Reddit")
@mock.patch(
    "lambdas.youtube.youtube_video_generator.build_image_urls",
    return_value=["https://picsum.photos/seed/1/1280/720"],
)
@mock.patch(
    "lambdas.youtube.youtube_video_generator.download_image",
    return_value=b"\xff\xd8\xff\xe0mockjpg",
)
@mock.patch("lambdas.youtube.youtube_video_generator.gTTS")
@mock.patch("lambdas.youtube.youtube_video_generator.MP3")
@mock.patch("lambdas.youtube.youtube_video_generator.subprocess.run")
@mock.patch("lambdas.youtube.youtube_video_generator.os.path.exists", return_value=True)
@mock.patch(
    "lambdas.youtube.youtube_video_generator.os.path.getsize", return_value=2048
)
@mock.patch("lambdas.youtube.youtube_video_generator.file_setup")
def test_lambda_handler_raises_when_upload_fails(
    mock_file_setup,
    mock_getsize,
    mock_exists,
    mock_subproc,
    mock_mp3,
    mock_gtts,
    mock_download,
    mock_build_urls,
    mock_reddit,
    mock_param,
    mock_uploader,
    mock_load_history,
    mock_save_history,
):
    mock_subproc.return_value.returncode = 0
    mock_mp3.return_value.info.length = 1
    mock_gtts.return_value.save.return_value = None

    mock_post = mock.Mock()
    mock_post.id = "post1"
    mock_post.over_18 = False
    mock_post.title = "Title"
    mock_post.selftext = "Text"
    mock_post.author = "author"
    mock_post.url = "url"
    mock_post.permalink = "/r/quotes/comments/abc123/test"
    mock_reddit.return_value.subreddit.return_value.new.return_value = [mock_post]

    mock_uploader.return_value.execute.side_effect = RuntimeError("upload-failed")
    os.makedirs("/tmp/images", exist_ok=True)

    with pytest.raises(RuntimeError, match="upload-failed"):
        youtube_video_generator.lambda_handler({}, {})
    assert not mock_save_history.called
