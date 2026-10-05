"""Keyword-based content safety checks for generated video content.

Blocks obviously hateful/extremist subject matter from being used as source
quotes or video titles. This is a coarse, extensible first line of defense —
not a substitute for a full moderation pipeline.
"""

import re

# Extend this list as new problem terms/figures are identified. Keep entries
# lowercase; matching is case-insensitive and word-boundary aware.
DENYLIST_TERMS = [
    "hitler",
    "adolf hitler",
    "nazi",
    "nazis",
    "nazism",
    "third reich",
    "ku klux klan",
    "kkk",
    "white supremacy",
    "white supremacist",
    "neo-nazi",
    "neo nazi",
    "genocide",
    "ethnic cleansing",
    "holocaust",
    "isis",
    "al-qaeda",
    "al qaeda",
    "white power",
    "lynching",
]

_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(term) for term in DENYLIST_TERMS) + r")\b",
    re.IGNORECASE,
)


def find_denylisted_term(text):
    """Return the first denylisted term found in text, or None if text is clean."""
    if not text:
        return None
    match = _PATTERN.search(text)
    return match.group(0) if match else None


def is_text_safe(text):
    return find_denylisted_term(text) is None
