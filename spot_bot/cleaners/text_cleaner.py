import re


# Patterns for lines that are pure noise
_DIGIT_LINE = re.compile(r"^\d[\s\d]*$")
_HASHTAG_LINE = re.compile(r"^#\S")
_URL_PATTERN = re.compile(r"https?://\S+")

# Social-media / promotional footer markers
_FOOTER_MARKERS = {
    "Сайт:", "Instagram:", "Telegram:", "Facebook:", "YouTube:",
    "Телефон:", "Тел:", "Email:", "E-mail:",
}
_FOOTER_PREFIX = re.compile(
    r"^(Сайт|Instagram|Telegram|Facebook|YouTube|Телефон|Тел|Email|E-mail)\s*:",
    re.IGNORECASE,
)

# Cross-reference patterns (references to other Spot articles)
_CROSS_REF = re.compile(
    r"Ранее\s+Spot\s+(писал|сообщал|рассказывал|информировал)",
    re.IGNORECASE,
)

# "Advertising" / promo markers
_PROMO_PATTERNS = [
    re.compile(r"^реклама$", re.IGNORECASE),
    re.compile(r"^Реклама на Spot", re.IGNORECASE),
    re.compile(r"^На правах рекламы", re.IGNORECASE),
    re.compile(r"^Партнерский материал", re.IGNORECASE),
]

# Sentence-ending punctuation (for paragraph break heuristics)
_SENTENCE_ENDERS = frozenset(".!?")


def clean_article(text, include_ads=False):
    """Clean a single article's text for reading and TTS consumption.

    Removes noise, promotional footers, cross-references, URLs, and
    normalizes paragraph structure for smooth reading flow.

    When include_ads=True, ad markers ("Реклама", "На правах рекламы"),
    contact-info footer lines (Сайт/Instagram/Телефон/etc.), and the
    trailing-footer-block strip are all DISABLED, so ad-only articles
    survive intact.
    """
    if not text:
        return ""

    paragraphs = text.split("\n\n")
    cleaned = []

    for para in paragraphs:
        para = _clean_paragraph(para, include_ads=include_ads)
        if para:
            cleaned.append(para)

    # Remove trailing footer block (social links often cluster at the end)
    if not include_ads:
        while cleaned and _is_footer_line(cleaned[-1]):
            cleaned.pop()

    return "\n\n".join(cleaned)


def _clean_paragraph(text, include_ads=False):
    """Clean a single paragraph. Returns empty string if it should be removed."""
    text = text.strip()
    if not text:
        return ""

    # Remove pure digit lines (view counts like "1 786")
    if _DIGIT_LINE.match(text):
        return ""

    # Remove hashtag lines
    if _HASHTAG_LINE.match(text):
        return ""

    # Remove "Comments" markers
    if text == "Комментарии" or text.startswith("Комментарии:"):
        return ""

    # Remove "Also read" lines
    if "Читайте также" in text or "Also read" in text:
        return ""

    # Remove cross-references to other Spot articles
    if _CROSS_REF.search(text):
        return ""

    # Ad / promo / contact-footer suppression — disabled when include_ads
    if not include_ads:
        for pattern in _PROMO_PATTERNS:
            if pattern.match(text):
                return ""
        if _is_footer_line(text):
            return ""

    # Strip URLs (they sound terrible when read aloud)
    text = _URL_PATTERN.sub("", text)

    # Normalize whitespace after URL removal
    text = re.sub(r"  +", " ", text).strip()

    # Normalize dashes for consistent TTS pausing
    text = text.replace("—", " — ")
    text = text.replace("–", " — ")
    text = re.sub(r"\s+—\s+", " — ", text)

    # Remove orphaned punctuation that might remain
    if text in {".", ",", ";", ":", "-", "—"}:
        return ""

    # If after all cleaning, nothing meaningful remains
    if len(text) < 3:
        return ""

    return text


def _is_footer_line(text):
    """Check if a line looks like a promotional/social footer."""
    text = text.strip()
    if _FOOTER_PREFIX.match(text):
        return True
    # Pure URL line
    if _URL_PATTERN.match(text) and len(text.split()) <= 3:
        return True
    return False


def clean_batch(articles, include_ads=False):
    """Clean a list of article dicts in place. Each dict should have 'body' key.

    Returns the same list with cleaned body text. When include_ads=True, ad
    markers and contact-footer noise are preserved.
    """
    for article in articles:
        if article.get("body"):
            article["body"] = clean_article(
                article["body"], include_ads=include_ads,
            )
    return articles
