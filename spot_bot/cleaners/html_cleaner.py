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


def _largest_from_srcset(srcset: str) -> str:
    """Return the highest-resolution URL from a srcset attribute, or ''.

    Handles both width descriptors (e.g. `... 800w`) and pixel-density
    descriptors (`... 2x`). Largest wins; descriptor-less entries are
    treated as 0.
    """
    if not srcset:
        return ""
    candidates: list[tuple[float, str]] = []
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        url = bits[0]
        size = 0.0
        if len(bits) >= 2:
            desc = bits[1]
            try:
                if desc.endswith("w"):
                    size = float(desc[:-1])
                elif desc.endswith("x"):
                    # Treat density descriptor as much larger than width
                    # so 1x doesn't win against an 800w plain entry.
                    size = float(desc[:-1]) * 1000.0
            except ValueError:
                pass
        candidates.append((size, url))
    if not candidates:
        return ""
    candidates.sort()
    return candidates[-1][1]


def _img_best_url(img) -> str:
    """Pick the best URL for an <img> tag, trying multiple lazy-load
    conventions. Returns '' if nothing usable is present."""
    # Lazy-load attributes in order of typical preference
    for attr in ("data-src", "data-original", "data-lazy-src",
                 "data-full-src", "data-large", "data-lazy"):
        val = img.get(attr)
        if val:
            return val
    # srcset: pick the largest variant
    srcset = img.get("srcset") or img.get("data-srcset")
    if srcset:
        best = _largest_from_srcset(srcset)
        if best:
            return best
    # Fallback to plain src
    return img.get("src") or ""


def extract_images(body_elem, base_url=""):
    """Extract article images from an HTML element.

    For spot.uz the highest-resolution URL is on the parent
    <a class="lightbox-img" href="..._l.webp">, not the inner thumbnail
    <img>. We detect that pattern and prefer the parent href.

    Falls through to <img> with srcset / data-* / src for sites that
    don't use the lightbox pattern.

    Returns list of {"url": ..., "alt": ...} dicts. Order preserved
    (cover image first, body images in DOM order).
    """
    images = []
    seen_urls: set[str] = set()
    handled_imgs = set()

    def _add(url: str, alt: str = ""):
        if not url:
            return
        if base_url and not url.startswith(("http://", "https://")):
            url = urljoin(base_url, url)
        if not url.startswith(("http://", "https://")):
            return
        if _TRACKER_PATTERN.search(url):
            return
        if url in seen_urls:
            return
        seen_urls.add(url)
        images.append({"url": url, "alt": (alt or "").strip()})

    # First pass: <a class="lightbox-img" href="..."> wraps the
    # full-resolution version. Capture the href and mark the inner
    # <img> as handled so we don't double-add a thumbnail later.
    for a in body_elem.find_all("a", class_="lightbox-img"):
        href = a.get("href") or ""
        inner = a.find("img")
        alt = ""
        if inner is not None:
            alt = inner.get("alt", "")
            handled_imgs.add(id(inner))
        _add(href, alt)

    # Second pass: <picture><source srcset="..."> for modern responsive
    # markup (less common on spot.uz but useful for RSS / other sources).
    for source in body_elem.find_all("source"):
        if source.parent and source.parent.name == "picture":
            best = _largest_from_srcset(source.get("srcset") or "")
            _add(best)

    # Third pass: standalone <img> tags not inside a lightbox link.
    for img in body_elem.find_all("img"):
        if id(img) in handled_imgs:
            continue
        src = _img_best_url(img)
        if not src:
            continue

        # Tiny-image filter (decorative dividers, tracking pixels).
        try:
            width = img.get("width") or ""
            height = img.get("height") or ""
            if width and int(width) < 50:
                continue
            if height and int(height) < 50:
                continue
        except (ValueError, TypeError):
            pass

        _add(src, img.get("alt", ""))

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
