import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup, NavigableString
from spot_bot.config import BODY_SELECTORS, STRIP_TAGS, STRIP_CLASSES, BLOCK_TAGS


# Single-word garbage lines to always discard
GARBAGE_EXACT = {
    "«Spot»", "Реклама", "Поделиться", "Facebook", "X",
    "Telegram", "Instagram", "YouTube", "Spot",
}


def clean_html(html_content, base_url=""):
    """Extract headline, body text, and images from a spot.uz article HTML page.

    Returns (headline, body_text, images) where:
    - body_text has proper paragraph flow (no orphaned inline-element words)
    - images is a list of {"url": ..., "alt": ...} dicts
    """
    soup = BeautifulSoup(html_content, "lxml")

    # 1. Headline
    headline = ""
    h1 = soup.find("h1")
    if h1:
        headline = h1.get_text(separator=" ").strip()

    # 2. Find article body container
    body_elem = None
    for selector in BODY_SELECTORS:
        if selector.get("class"):
            found = soup.find_all(selector["name"], class_=selector["class"])
        elif selector.get("id"):
            found = soup.find_all(selector["name"], id=selector["id"])
        else:
            found = soup.find_all(selector["name"])
        for f in found:
            body_elem = f
            break
        if body_elem:
            break

    if not body_elem:
        return None, None, []

    # 2b. Extract images BEFORE stripping (so we don't lose them)
    images = extract_images(body_elem, base_url)

    # 3. Strip unwanted tags
    for tag in STRIP_TAGS:
        for s in body_elem.find_all(tag):
            s.decompose()

    # 4. Strip unwanted classes
    for cls in STRIP_CLASSES:
        for s in body_elem.find_all(class_=re.compile(cls)):
            s.decompose()

    # 5. Strip ad-related IDs
    for s in body_elem.find_all(id=re.compile(r"adfox|banner")):
        s.decompose()

    # 6. Remove "Also read" paragraphs
    for p in body_elem.find_all("p"):
        text = p.get_text()
        if "Читайте также" in text or "Also read" in text:
            p.decompose()

    # 7. Extract text with proper paragraph flow
    # KEY FIX: Instead of get_text(separator="\n") which breaks inline
    # elements (<a>, <b>, <span>) onto separate lines, we process
    # block-level elements individually and join inline content with spaces.
    paragraphs = []
    _extract_blocks(body_elem, paragraphs)

    # 8. Filter garbage lines
    cleaned = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if para in GARBAGE_EXACT:
            continue
        if para.startswith("Фото:"):
            continue
        if para.startswith("Реклама на"):
            continue
        if para.isdigit():
            continue
        # Remove duplicate headline in body
        if headline and para == headline:
            continue
        cleaned.append(para)

    text = "\n\n".join(cleaned)

    # 9. Reject only genuine auth-wall stubs.
    # Earlier the threshold was <500 chars, which dropped long interview
    # articles where boilerplate auth-wall text appears alongside real
    # content that cleans down to under 500 chars. Strip the auth-wall
    # sentence first, then reject only when nothing meaningful remains.
    auth_wall_phrase = "Вы не авторизованы. Войдите на сайт"
    if auth_wall_phrase in text:
        text_without_authwall = text.replace(auth_wall_phrase, "").strip()
        has_paragraphs = bool(body_elem.find("p"))
        if len(text_without_authwall) < 50 and not has_paragraphs:
            return headline, None, images

    return headline, text, images


# Patterns for tracking pixel / tiny image URLs to skip
_TRACKER_PATTERN = re.compile(r"pixel|tracker|beacon|1x1|spacer|blank", re.IGNORECASE)


def extract_images(body_elem, base_url=""):
    """Extract article images from an HTML element.

    Finds all <img> tags, resolves relative URLs, and filters out
    tracking pixels and tiny decorative images.

    Returns list of {"url": ..., "alt": ...} dicts.
    """
    images = []
    seen_urls = set()

    for img in body_elem.find_all("img"):
        src = img.get("src", "") or img.get("data-src", "")
        if not src:
            continue

        # Resolve relative URLs
        if base_url and not src.startswith(("http://", "https://")):
            src = urljoin(base_url, src)

        # Skip if not a proper URL
        if not src.startswith(("http://", "https://")):
            continue

        # Skip tracking pixels
        if _TRACKER_PATTERN.search(src):
            continue

        # Skip tiny images (width/height attrs indicate decorative)
        width = img.get("width", "")
        height = img.get("height", "")
        try:
            if width and int(width) < 50:
                continue
            if height and int(height) < 50:
                continue
        except (ValueError, TypeError):
            pass

        # Deduplicate
        if src in seen_urls:
            continue
        seen_urls.add(src)

        alt = img.get("alt", "").strip()
        images.append({"url": src, "alt": alt})

    return images


def _extract_blocks(element, paragraphs):
    """Recursively extract text from an element, respecting block vs inline.

    Block-level children become separate paragraphs.
    Inline children and NavigableStrings are joined with spaces into the
    current paragraph.
    """
    inline_parts = []

    for child in element.children:
        if isinstance(child, NavigableString):
            text = child.strip()
            if text:
                inline_parts.append(text)
        elif child.name in BLOCK_TAGS:
            # Flush any accumulated inline text first
            if inline_parts:
                merged = " ".join(inline_parts)
                if merged.strip():
                    paragraphs.append(merged.strip())
                inline_parts = []
            # Recurse into the block element
            _extract_blocks(child, paragraphs)
        else:
            # Inline element (<a>, <b>, <i>, <span>, <em>, <strong>, etc.)
            # Join its text content with surrounding text
            text = child.get_text(separator=" ").strip()
            if text:
                inline_parts.append(text)

    # Flush remaining inline text
    if inline_parts:
        merged = " ".join(inline_parts)
        if merged.strip():
            paragraphs.append(merged.strip())


def clean_telegram_text(html_text):
    """Extract plain text from a Telegram post's HTML content."""
    if not html_text:
        return ""
    try:
        soup = BeautifulSoup(html_text, "lxml")
        return soup.get_text(separator=" ").strip()
    except Exception:
        return html_text
