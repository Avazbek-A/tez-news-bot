import os

from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Source channel
CHANNEL_URL = "https://t.me/s/spotuz"

# Article body CSS selectors (tried in order)
BODY_SELECTORS = [
    {"name": "div", "class": "articleContent"},
    {"name": "div", "class": "article-content"},
    {"name": "div", "class": "article_text"},
    {"name": "div", "class": "contentBox"},
]

# HTML tags to strip from articles
STRIP_TAGS = [
    "script", "style", "iframe", "noscript",
    "header", "footer", "nav", "aside", "table",
]

# CSS classes to strip from articles
STRIP_CLASSES = [
    "read-also", "read_also", "also-read", "relap", "relap-wrapper",
    "social-share", "share-buttons", "author-block", "meta", "tags",
    "comments", "reply", "related", "banner", "advertisement",
    "itemData", "itemTitle", "itemImage", "itemColImage", "floating_banner",
    "push_subscribe", "login_modal", "modal", "floating_news",
]

# Block-level HTML tags (for text extraction)
BLOCK_TAGS = {
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "ul", "ol", "li", "section", "article",
    "figure", "figcaption", "pre",
}

# TTS settings
DEFAULT_VOICE = "ru-RU-DmitryNeural"
AVAILABLE_VOICES = {
    # Russian
    "dmitry": "ru-RU-DmitryNeural",
    "svetlana": "ru-RU-SvetlanaNeural",
    # English
    "andrew": "en-US-AndrewNeural",
    "ava": "en-US-AvaNeural",
    "emma": "en-US-EmmaNeural",
    "brian": "en-US-BrianNeural",
    # Uzbek
    "madina": "uz-UZ-MadinaNeural",
    "sardor": "uz-UZ-SardorNeural",
}
VOICE_LANGUAGES = {
    "ru": ["dmitry", "svetlana"],
    "en": ["andrew", "ava", "emma", "brian"],
    "uz": ["madina", "sardor"],
}

# Language settings
DEFAULT_LANGUAGE = "en"
AVAILABLE_LANGUAGES = {"en", "ru", "uz"}
TTS_RATE = "+0%"
AVAILABLE_SPEEDS = {
    "slow": "-30%",
    "normal": "+0%",
    "fast": "+25%",
    "faster": "+50%",
    "fastest": "+80%",
}

# Scraping
MAX_CONCURRENT_FETCHES = 6
MAX_CONCURRENT_TTS = 4
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Timeouts (all in milliseconds unless noted)
PLAYWRIGHT_NAV_TIMEOUT_MS = 30_000          # spot.uz article navigation
PLAYWRIGHT_SELECTOR_TIMEOUT_MS = 5_000      # wait for .contentBox etc.
PLAYWRIGHT_CHANNEL_TIMEOUT_MS = 10_000      # wait for Telegram messages to load
SCROLL_WAIT_MS = 2_000                      # pause between scrolls during pagination
SCROLL_BACK_PX = 500                        # pixels to scroll back when stalled

# Retry / stall behaviour
STALL_THRESHOLD = 3                         # scroll rounds with no new posts before giving up
RETRY_MAX_ATTEMPTS = 3
RETRY_INITIAL_BACKOFF_S = 1.0               # exponential: 1s, 2s, 4s

# TTS timeouts (seconds). generate_audio uses adaptive = base + per-char factor.
TTS_BASE_TIMEOUT_S = 30
TTS_PER_1000_CHARS_S = 10
TTS_MAX_TIMEOUT_S = 180

# Delivery rate limits (seconds between sends)
DELIVERY_TEXT_DELAY_S = 0.3
DELIVERY_IMAGE_DELAY_S = 0.3
DELIVERY_AUDIO_DELAY_S = 0.5

# Telegram limits
TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_AUDIO_LIMIT_MB = 50

# Default scrape count
DEFAULT_SCRAPE_COUNT = 20
MAX_SCRAPE_COUNT = 200
MAX_OFFSET = 5000

# Auto-scrape limits
MIN_AUTO_INTERVAL_DAYS = 1
MAX_AUTO_INTERVAL_DAYS = 30
DEFAULT_AUTO_SCRAPE_COUNT = 50
