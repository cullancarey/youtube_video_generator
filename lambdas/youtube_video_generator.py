"""Praw is used to scrape reddit"""
import praw
import os
import subprocess
import shlex
import shutil
import random
import logging
from datetime import datetime
from gtts import gTTS
import requests
from mutagen.mp3 import MP3
import boto3
from upload_video import UploadVideo

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_image_urls(query):
    """Retrieves image URLs based on text file"""
    try:
        url = f"https://www.google.be/search?q={query}&tbm=isch"
        headers = {}
        data = {}
        response = requests.get(url, headers=headers, data=data, timeout=60)

        if response.status_code == 200:
            logger.info(f"Successfully fetched image URLs for query: {query}")
            return response.text
        else:
            logger.error(
                f"Failed to fetch image URLs. HTTP Status Code: {response.status_code}"
            )
            return None

    except requests.Timeout:
        logger.error(f"Timeout occurred while fetching image URLs for query: {query}")
        return None
    except Exception as e:
        logger.error(
            f"An error occurred while fetching image URLs for query: {query}. Error: {e}"
        )
        return None


def download_image(urls):
    """Downloads the image content for the video file"""
    try:
        url = f"{urls}"
        headers = {}
        data = {}
        response = requests.get(url, headers=headers, data=data, timeout=60)

        if response.status_code == 200:
            logger.info(f"Successfully downloaded image from URL: {url}")
            return response.content
        else:
            logger.error(
                f"Failed to download image. HTTP Status Code: {response.status_code}"
            )
            return None

    except requests.Timeout:
        logger.error(f"Timeout occurred while downloading image from URL: {url}")
        return None
    except Exception as e:
        logger.error(
            f"An error occurred while downloading image from URL: {url}. Error: {e}"
        )
        return None


def get_param(
    param_name: str,
):
    """Function to get parameter value from parameter store"""
    client = boto3.client("ssm")
    try:
        logger.info(f"Retrieving parameter {param_name}...")
        response = client.get_parameter(Name=param_name, WithDecryption=True)
    except Exception as e:
        logger.error(f"Error retrieving parameter: {param_name} with error: {e}")
    return response["Parameter"]["Value"]


def file_setup():
    """Downloads files from S3 and moves them to lambda tmp/ directory"""
    try:
        s3_client = boto3.resource("s3")
        bucket_name = "youtube-uploader-bucket"
        keys = [
            "youtube_video_generator.py-oauth2.json",
            "story.txt",
            "story.mp3",
            "output.mp4",
            "client_secrets.json",
        ]
        for key in keys:
            local_file_name = f"/tmp/{key}"
            try:
                s3_client.Bucket(bucket_name).download_file(key, local_file_name)
                logger.info(f"File copied from S3 to lambda: {local_file_name}")
            except Exception as err:
                logger.error(f"Error occurred while downloading {key} from S3: {err}")

        os.mkdir("/tmp/images")
        logger.info("Done setting up files and directories.")

    except Exception as e:
        logger.critical(f"An unrecoverable error occurred in file_setup: {e}")


def lambda_handler(event, context):
    """Main function for lambda"""
    try:
        file_setup()
        logger.info("File setup completed.")

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
            logger.info(f"Established Reddit session: {reddit}")
        except Exception as err:
            logger.error(f"Exception establishing Reddit session: {err}")
            return

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
        logger.info("Video uploaded.")

        # Clean up files
        shutil.rmtree("/tmp/images/")
        os.remove("/tmp/story.txt")
        os.remove("/tmp/story.mp3")
        os.remove("/tmp/output.mp4")
        os.remove("/tmp/client_secrets.json")
        logger.info("Done deleting files.")

    except Exception as e:
        logger.critical(f"An unrecoverable error occurred: {e}")
