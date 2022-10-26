"""Praw is used to scrape reddit"""
import praw
import os
import subprocess
import shlex
import shutil
import random
from datetime import datetime
from gtts import gTTS
import requests
from mutagen.mp3 import MP3
import boto3
from upload_video import UploadVideo


def get_image_urls(query):
    """Retrieves image urls based on text file"""
    url = f"https://www.google.be/search?q={query}&tbm=isch"

    headers = {}
    data = {}

    response = requests.get(url, headers=headers, data=data, timeout=60)

    return response.text


def download_image(urls):
    """Downloads the image context for the video file"""
    url = f"{urls}"

    headers = {}
    data = {}

    response = requests.get(url, headers=headers, data=data, timeout=60)

    return response.content


def get_param(param):
    """Retrieves parameter from parameter store in AWS"""
    client = boto3.client("ssm")
    response = client.get_parameter(Name=param, WithDecryption=True)
    return response["Parameter"]["Value"]


def file_setup():
    """Downloads files from S3 and moves them to lambda tmp/ directory"""
    s3_client = boto3.resource("s3")
    bucket_name = "youtube-uploader-bucket"
    keys = [
        "youtube_video_generator.py-oauth2.json",
        "story.txt",
        "story.mp3",
        "output.mp4",
        "client_secrets.json"
    ]
    for key in keys:
        try:
            local_file_name = f"/tmp/{key}"
            s3_client.Bucket(bucket_name).download_file(key, local_file_name)
        except Exception as err:
            print(f"Error ocurred while downloading files from S3: {err}")
        print(f"File copied from S3 to lambda: {local_file_name}")

    # shutil.copy(f"{os.getcwd()}/youtube_video_generator.py-oauth2.json", "/tmp/youtube_video_generator.py-oauth2.json")
    # shutil.copy(f"{os.getcwd()}/story.txt", "/tmp/story.txt")
    # shutil.copy(f"{os.getcwd()}/story.mp3", "/tmp/story.mp3")
    # shutil.copy(f"{os.getcwd()}/output.mp4", "/tmp/output.mp4")
    os.mkdir("/tmp/images")

    print("Done setting up files...")


def lambda_handler(event, context):
    """Main function for lambda"""

    file_setup()

    client_id_param = get_param("reddit_client_id")
    client_secret_param = get_param("reddit_client_secret")
    user_agent_param = get_param("reddit_user_agent")
    username_param = get_param("reddit_username")
    password_param = get_param("reddit_password")

    # Sets Reddit session
    try:
        reddit = praw.Reddit(
            client_id=client_id_param,
            client_secret=client_secret_param,
            user_agent=user_agent_param,
            username=username_param,
            password=password_param,
        )
    except Exception as err:
        print(f"Exception establishing reddit session: {err}")
    print(f"Establised reddit session: {reddit}")

    # Grabs newest submission from r/quotes.
    # Also grabs author and url for credit
    with open("/tmp/story.txt", "w+", encoding="utf-8") as story_file:
        for submission in reddit.subreddit("quotes").new(limit=1):
            if not submission.over_18:
                story_file.write(submission.title)
                story_file.write(submission.selftext)
                author = submission.author
                url = submission.url

    story_file.close()

    # Cretes mp3 file from text file
    with open("/tmp/story.txt", "r", encoding="utf-8") as story:
        text_file = story.read()
        print(f"Story file contents: {text_file}")
        tts = gTTS(text_file)
        tts.save("/tmp/story.mp3")
        audio_file_path = "/tmp/story.mp3"

    # Get length of audio and sets number of images needed
    audio = MP3("/tmp/story.mp3")
    audio_length = audio.info.length
    number_of_images = str(audio_length)
    number_of_images = number_of_images.split(".")
    number_of_images = number_of_images[0]

    # Retrieves images urls
    response = get_image_urls(f"{text_file}")
    response = response.split('"')
    urls = []
    for i in response:
        response = i.split(";s")
        if "https://encrypted-" in i:
            urls.append(response[0])

    if int(number_of_images) > len(urls):
        response = get_image_urls("coding with python")
        response = response.split('"')
        for i in response:
            response = i.split(";s")
            if "https://encrypted-" in i:
                urls.append(response[0])

    # Creates directory for images file
    images_dir = "/tmp/images"
    if not os.path.isdir(images_dir):
        images_dir = os.mkdir(images_dir)
    images_path = f"{images_dir}/*.jpg"

    # Downloads images based on the lenth of the audio file
    for count, i in enumerate(range(int(number_of_images))):
        image = download_image(urls[count])
        with open(f"{images_dir}/image{count}.jpg", "wb") as handler:
            handler.write(image)
            handler.close()

    # Get frame rate for video
    frame_rate = audio_length / int(number_of_images)

    video_file_path = "/tmp/output.mp4"

    # Create Video File!
    command_line = f"{os.getcwd()}/ffmpeg -y -hide_banner -framerate 1/{str(frame_rate)} -pix_fmt yuvj420p  -pattern_type glob -i {str(images_path)} -i {str(audio_file_path)} -c:v libx264 -vf scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2 -c:a aac -shortest {str(video_file_path)}"

    args = shlex.split(command_line)
    print(f"Running ffmpeg to create video file with argument: {args}")
    subprocess.call(args)

    titles = [
        f"Daily Quote {datetime.today().strftime('%Y-%m-%d')}",
        "Quotes Daily",
        f"{datetime.today().strftime('%Y-%m-%d')} Quote",
        "Quotes",
        "Daily Quote",
        "Quote",
    ]

    description = f"""Please enjoy this daily quote from u/{author}!
    These quotes are from r/quotes on Reddit.
    Link to post: {url}. \n
    This video was created and uploaded via Python!"""
    keywords = "quote", "quotes", "daily quote, python, reddit"

    # Instanciate upload video class
    upload = UploadVideo()

    # Calls method to upload video
    # print(video_file_path, random.choice(titles), description, 22, keywords, 'private')
    upload.execute(
        video_file_path, random.choice(titles), description, 22, keywords, "private"
    )

    # Clean up files
    shutil.rmtree("/tmp/images/")
    os.mkdir(images_dir)
    os.remove("/tmp/story.txt")
    os.remove("/tmp/story.mp3")
    os.remove("/tmp/output.mp4")
    os.remove("/tmp/client_secrets.json")
    print("Done deleting files")
