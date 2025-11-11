import re
import random
import textwrap
from datetime import datetime


def extract_keywords_from_text(text: str, max_keywords: int = 8):
    """Extract meaningful words for YouTube tags."""
    stopwords = {
        "the",
        "a",
        "and",
        "in",
        "to",
        "of",
        "for",
        "is",
        "on",
        "it",
        "that",
        "with",
    }
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    keywords = [w for w in words if w not in stopwords]
    unique = list(dict.fromkeys(keywords))[:max_keywords]
    base_tags = ["quotes", "motivation", "inspiration", "reddit", "python"]
    return base_tags + unique


def generate_title_and_description(text: str, author: str, url: str):
    """Create SEO-optimized title and description."""
    matches = re.findall(r"[A-Z][a-z]+\s[A-Z][a-z]+", text)
    key_phrase = random.choice(matches) if matches else "Daily Inspiration"
    date_str = datetime.now().strftime("%B %d, %Y")

    title = f"{key_phrase} — {date_str} | Quote of the Day"
    description = textwrap.dedent(
        f"""
    ✨ {key_phrase} ✨
    Daily inspiration from r/quotes — shared by u/{author}

    🗓️ Date: {date_str}
    🔗 Original Reddit Post: {url}
    💬 Comment below your thoughts — and subscribe for more daily quotes!

    #quotes #motivation #inspiration #reddit #dailyquote #python
    """
    ).strip()

    return title, description


# def create_thumbnail(text: str, output_path: str = "/tmp/thumbnail.jpg"):
#     """Generate a simple thumbnail with the quote text."""
#     width, height = 1280, 720
#     img = Image.new("RGB", (width, height), color=(20, 20, 20))
#     draw = ImageDraw.Draw(img)

#     font = ImageFont.truetype(
#         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48
#     )
#     lines = textwrap.wrap(text, width=25)[:3]
#     y_text = height // 3

#     for line in lines:
#         text_w, text_h = draw.textsize(line, font=font)
#         draw.text(((width - text_w) / 2, y_text), line, font=font, fill=(255, 255, 255))
#         y_text += text_h + 10

#     img.save(output_path)
#     return output_path


def optimize_metadata(text, author, url):
    """Full metadata generation routine."""
    title, description = generate_title_and_description(text, author, url)
    keywords = extract_keywords_from_text(text)
    # thumbnail = create_thumbnail(text)
    thumbnail = None
    return title, description, keywords, thumbnail
