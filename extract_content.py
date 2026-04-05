import asyncio
import json
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
import os

INPUT_FILE = "posts_index.json"
OUTPUT_FILE = "Spot_News_Unfiltered.txt"
SEPARATOR = "\n### NEXT ITEM ###\n"

# Selectors to try for article body
BODY_SELECTORS = [
    {"name": "div", "class": "articleContent"}, 
    {"name": "div", "class": "article-content"},
    {"name": "div", "class": "article_text"},
    {"name": "div", "class": "contentBox"} 
]

# Tags to strip
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
    
    # 1. Title
    headline = ""
    h1 = soup.find("h1")
    if h1:
        headline = h1.get_text().strip()
    
    # 2. Body
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
        return None, None

    # Cleaning
    for tag in STRIP_TAGS:
        for s in body_elem.find_all(tag):
            s.decompose()
            
    for cls in STRIP_CLASSES:
        for s in body_elem.find_all(class_=re.compile(cls)):
            s.decompose()
            
    # Remove elements by ID if needed (e.g. adfox)
    for s in body_elem.find_all(id=re.compile("adfox|banner")):
        s.decompose()
    
    # Remove internal links' "Also Read" text
    for p in body_elem.find_all("p"):
        if "Читайте также" in p.get_text() or "Also read" in p.get_text():
            p.decompose()

    text = body_elem.get_text(separator="\n").strip()
    
    # Text-level cleanup
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Filter garbage lines
        if line in ["«Spot»", "Реклама", "Поделиться", "Facebook", "X", "Telegram", "Instagram", "YouTube"]:
            continue
        if line.startswith("Фото:"):
            continue
        if line.startswith("Реклама на"):
            continue
        if line.isdigit(): # Views count often isolated number
            continue
        # Remove duplicate title if it appears in body
        if headline and line == headline:
            continue
            
        lines.append(line)
        
    text = "\n\n".join(lines)
    
    # Validation: Check for known garbage strings
    if "Вы не авторизованы. Войдите на сайт" in text:
        if len(text) < 500:
            return headline, None # Reject body
            
    return headline, text

def clean_telegram_text(html_text):
    if not html_text:
        return ""
    try:
        soup = BeautifulSoup(html_text, "lxml")
        return soup.get_text().strip()
    except:
        return html_text

async def process_item(context, item, semaphore):
    original_text = clean_telegram_text(item.get("text_html", ""))
    
    # Check Scenario B (No link to Spot)
    has_spot_link = item.get("has_spot_link")
    link = None
    if has_spot_link:
        for l in item.get("links", []):
            if "spot.uz" in l:
                link = l
                break
    
    if not has_spot_link or not link:
        return f"Telegram Post [{item['date']}]\n\n{original_text}"
        
    # Scenario A: Fetch with Playwright
    async with semaphore:
        page = None
        try:
            page = await context.new_page()
            # Block resources to speed up
            await page.route("**/*.{png,jpg,jpeg,svg,css,woff,woff2}", lambda route: route.abort())
            
            try:
                await page.goto(link, timeout=30000, wait_until="domcontentloaded")
                # Wait for contentBox to be sure
                try:
                    await page.wait_for_selector(".contentBox", timeout=5000)
                except:
                    pass # Proceed anyway, maybe structure is diff
                
                content = await page.content()
            except Exception as nav_e:
                print(f"Nav error for {link}: {nav_e}")
                content = None

            if not content:
                 return f"Telegram Post [{item['date']}] (Fetch Failed)\n\n{original_text}"
            
            headline, body = clean_html(content)
            
            if not body:
                title_prefix = f"Headline: {headline}\n\n" if headline else ""
                return f"{title_prefix}Telegram Post [{item['date']}] (Content unavailable/Auth wall)\n\n{original_text}"
                
            return f"{headline}\n\n{body}"

        except Exception as e:
            print(f"Error processing {item.get('id')}: {e}")
            return f"Telegram Post [{item['date']}] (Error)\n\n{original_text}"
        finally:
            if page:
                await page.close()

async def main():
    print("Loading index...")
    with open(INPUT_FILE, "r") as f:
        posts = json.load(f)
        
    # Sort OLD to NEW (Chronological)
    posts.sort(key=lambda x: (x["date"], int(x["id"].split("/")[-1]) if "/" in x["id"] else 0))
    
    print(f"Loaded and sorted {len(posts)} items.")
    
    results = []
    
    # Limit concurrency for Playwright (browser heavy)
    semaphore = asyncio.Semaphore(6) 
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Reuse context
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        tasks = [process_item(context, p_item, semaphore) for p_item in posts]
        
        # Process in chunks or full gather? Gather is fine with semaphore.
        # But for 1000 items, we might want a progress bar or chunking to see progress?
        # Let's just gather and print progress inside process_item?
        
        # Wrap to print progress
        async def tracked(task, idx, total):
            res = await task
            if idx % 10 == 0:
                print(f"Progress: {idx}/{total}")
            return res
            
        tracked_tasks = [tracked(process_item(context, posts[i], semaphore), i, len(posts)) for i in range(len(posts))]
        
        results = await asyncio.gather(*tracked_tasks)
        
        await browser.close()
        
    print("Writing output...")
    with open(OUTPUT_FILE, "w") as f:
        for content in results:
            if content:
                f.write(content)
                f.write(SEPARATOR)
                
    print(f"Done. Wrote {len(results)} items to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
