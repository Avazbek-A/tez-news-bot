import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

URL = "https://www.spot.uz/ru/2025/11/12/frame/"

# Proposed New Selectors
BODY_SELECTORS = [
    {"name": "div", "class": "articleContent"}, # CamelCase correct
    {"name": "div", "class": "article-content"},
    {"name": "div", "class": "article_text"},
    {"name": "div", "class": "contentBox"} 
]

STRIP_TAGS = [
    "script", "style", "iframe", "noscript", 
    "header", "footer", "nav", "aside", "table"
]
STRIP_CLASSES = [
    "read-also", "read_also", "also-read", "relap", "relap-wrapper",
    "social-share", "share-buttons", "author-block", "meta", "tags",
    "comments", "reply", "related", "banner", "advertisement",
    "itemData", "itemTitle", "itemImage", "itemColImage", "floating_banner",
    "push_subscribe", "login_modal", "modal", "floating_news"
]

def clean_html(html_content):
    soup = BeautifulSoup(html_content, "lxml")
    
    headline = ""
    h1 = soup.find("h1")
    if h1:
        headline = h1.get_text().strip()
    
    body_elem = None
    used_selector = ""
    for selector in BODY_SELECTORS:
        if selector.get("class"):
            found = soup.find_all(selector["name"], class_=selector["class"])
        else:
             found = soup.find_all(selector["name"])

        for f in found:
            body_elem = f
            used_selector = f"{selector['name']}.{selector['class']}"
            break
        if body_elem:
            break
            
    if not body_elem:
        return headline, "NO BODY FOUND", ""

    # Cleaning
    for tag in STRIP_TAGS:
        for s in body_elem.find_all(tag):
            s.decompose()
            
    for cls in STRIP_CLASSES:
        for s in body_elem.find_all(class_=re.compile(cls)):
            s.decompose()
            
    for s in body_elem.find_all(id=re.compile("adfox|banner")):
        s.decompose()
    
    for p in body_elem.find_all("p"):
        if "Читайте также" in p.get_text() or "Also read" in p.get_text():
            p.decompose()

    text = body_elem.get_text(separator="\n").strip()
    
    # Text level
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line: continue
        if line in ["«Spot»", "Реклама", "Поделиться", "Facebook", "X", "Telegram", "Instagram", "YouTube"]: continue
        if line.startswith("Фото:"): continue
        if line.startswith("Реклама на"): continue
        if line.isdigit(): continue
        if headline and line == headline: continue
        lines.append(line)
        
    return headline, "\n\n".join(lines), used_selector

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL, wait_until="domcontentloaded")
        
        # Wait for content
        try:
            await page.wait_for_selector(".articleContent", timeout=5000)
        except:
            print("articleContent not found in time")
            
        content = await page.content()
        await browser.close()
        
        h, t, sel = clean_html(content)
        print(f"HEADLINE: {h}")
        print(f"SELECTOR USED: {sel}")
        print("-" * 20)
        print(t[:500]) # First 500 chars
        print("-" * 20)
        print(f"TOTAL LENGTH: {len(t)}")

if __name__ == "__main__":
    asyncio.run(main())
