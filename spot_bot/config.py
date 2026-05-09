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
    # German
    "katja": "de-DE-KatjaNeural",
    "conrad": "de-DE-ConradNeural",
    "killian": "de-DE-KillianNeural",
    # Turkish
    "emel": "tr-TR-EmelNeural",
    "ahmet": "tr-TR-AhmetNeural",
}
VOICE_LANGUAGES = {
    "ru": ["dmitry", "svetlana"],
    "en": ["andrew", "ava", "emma", "brian"],
    "uz": ["madina", "sardor"],
    "de": ["katja", "conrad", "killian"],
    "tr": ["emel", "ahmet"],
}

# Default voice per detected article language. Used by the lang-aware
# voice picker when /voice_engine edge is set; user can override per
# language via /voice <lang> <name>.
DEFAULT_VOICES_BY_LANG = {
    "ru": "ru-RU-DmitryNeural",
    "en": "en-US-AndrewNeural",
    "uz": "uz-UZ-MadinaNeural",
    "de": "de-DE-ConradNeural",
    "tr": "tr-TR-AhmetNeural",
}

# Language settings — bot UI languages
DEFAULT_LANGUAGE = "en"
AVAILABLE_LANGUAGES = {"en", "ru", "uz", "de", "tr"}
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
