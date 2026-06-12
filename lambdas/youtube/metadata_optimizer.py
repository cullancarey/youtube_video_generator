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
    text = text or ""
    # Handle None or empty text safely
    matches = re.findall(r"[A-Z][a-z]+\s[A-Z][a-z]+", text)
    key_phrase = random.choice(matches) if matches else "Daily Inspiration"
    date_str = datetime.now().strftime("%B %d, %Y")

    title = f"{key_phrase} — {date_str} | Quote of the Day"
    description = textwrap.dedent(f"""
    ✨ {key_phrase} ✨
    Daily inspiration from r/quotes — shared by u/{author}

    🗓️ Date: {date_str}
    🔗 Original Reddit Post: {url}
    💬 Comment below your thoughts — and subscribe for more daily quotes!

    #quotes #motivation #inspiration #reddit #dailyquote #python
    """).strip()

    return title, description


def optimize_metadata(text, author, url):
    """Full metadata generation routine."""
    title, description = generate_title_and_description(text, author, url)
    keywords = extract_keywords_from_text(text)
    return title, description, keywords, None
