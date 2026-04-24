"""Optional AI features.

`summarize.py` wraps the Anthropic Claude API to produce 2-sentence
summaries of scraped articles. Only active when ANTHROPIC_API_KEY is
set — everything gracefully degrades if the SDK or key is missing.
"""
