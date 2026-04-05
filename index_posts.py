import asyncio
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

TARGET_DATE = datetime(2025, 11, 12).date()
CHANNEL_URL = "https://t.me/s/spotuz"
OUTPUT_FILE = "posts_index.json"

def parse_date(date_str):
    """
    Parses Telegram date string.
    Examples: "Nov 12, 2025", "16:40", "today at 16:40", "yesterday at 16:40", "Jan 15" (implies current year if close?)
    Actually t.me/s/ dates are usually "Mmm D, YYYY" or "Mmm D" or "HH:MM".
    If it's just time, it's today.
    """
    today = datetime.now().date()
    try:
        # relative dates might not appear in /s/ view (usually absolute or "today"), but let's handle usual cases
        date_str = date_str.lower().strip()
        
        if "today" in date_str:
            return today
        if "yesterday" in date_str:
            return today - timedelta(days=1)
        
        # Format: "Jan 17, 2026"
        # Format: "Jan 17" (current year usually, but safety check needed when crossing years)
        
        # Remove " at HH:MM" if present (though /s/ view usually has date link which is text)
        # In /s/ view, the timestamp link usually has text like "Jan 17, 2025" or "14:30"
        
        # Clean up
        date_text = date_str.split(" at ")[0]
        
        try:
            return datetime.strptime(date_text, "%b %d, %Y").date()
        except ValueError:
            pass
            
        try:
            # "Jan 17" -> assume current year first, if future, subtract 1 year (unlikely for history scrape)
            # But wait, if we are in 2026 and see "Nov 12", it's 2025.
            dt = datetime.strptime(date_text, "%b %d").date()
            dt = dt.replace(year=today.year)
            if dt > today:
                dt = dt.replace(year=today.year - 1)
            return dt
        except ValueError:
            pass

        # If it's just time "14:30" -> Today
        if ":" in date_text and len(date_text) < 6:
             return today

    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
    return None

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Navigating to {CHANNEL_URL}...")
        await page.goto(CHANNEL_URL)
        await page.wait_for_selector(".tgme_widget_message", state="visible")

        captured_posts = []
        keep_scrolling = True
        
        # We need to scroll UP to get older messages.
        # But wait, t.me/s/ opens at the BOTTOM?
        # Usually yes.
        # Strategy:
        # 1. Grab all visible messages.
        # 2. Check oldest message date.
        # 3. If oldest > target, scroll up (evaluate window.scrollTo(0, 0) or similar?).
        #    Actually, standard scroll behavior is scroll up.
        #    Wait for new messages to load.
        
        processed_ids = set()

        while keep_scrolling:
            # Get all message elements currently in DOM
            # We re-query every time
            messages = await page.locator(".tgme_widget_message").all()
            
            # If no messages, break
            if not messages:
                print("No messages found!")
                break
                
            print(f"Visible messages in DOM: {len(messages)}")
            
            # Process messages from NEWEST (bottom) to OLDEST (top) 
            # to efficiently detect when to stop.
            # But we want to capture ALL valid ones.
            # The DOM order is Oldest -> Newest.
            
            newly_added = 0
            
            # We iterate simply all of them to update our list
            # Optimisation: Only process those we haven't seen? 
            # `data-post` attribute holds ID like "spotuz/12345"
            
            # Let's collect data first
            current_batch_data = []
            
            for msg in messages:
                try:
                    # ID
                    post_id = await msg.get_attribute("data-post")
                    if not post_id:
                        continue
                        
                    if post_id in processed_ids:
                        continue # Already processed
                    
                    # Date
                    date_elem = msg.locator(".tgme_widget_message_date time")
                    if await date_elem.count() > 0:
                         datetime_attr = await date_elem.get_attribute("datetime")
                         # datetime is usually ISO "2025-11-20T10:00:00+00:00"
                         # This is MUCH easier than text parsing if available
                         if datetime_attr:
                             date_obj = datetime.fromisoformat(datetime_attr).date()
                         else:
                             # Fallback to text
                             date_text = await msg.locator(".tgme_widget_message_date").text_content()
                             date_obj = parse_date(date_text)
                    else:
                        # Fallback
                        date_text = await msg.locator(".tgme_widget_message_info").text_content() # rough check
                        date_obj = today # Assign today if fail is safest? Or ignore?
                        # better try to find .tgme_widget_message_date
                        if await msg.locator(".tgme_widget_message_date").count() > 0:
                            date_text = await msg.locator(".tgme_widget_message_date").text_content()
                            date_obj = parse_date(date_text)
                        
                    if not date_obj:
                        print(f"Could not parse date for {post_id}")
                        continue

                    # Content
                    text_content = ""
                    # Target only the main message text, avoiding reply previews (js-message_reply_text)
                    text_locator = msg.locator(".tgme_widget_message_text.js-message_text")
                    if await text_locator.count() > 0:
                        text_content = await text_locator.inner_html()
                    
                    # Check for links
                    # We can fetch all 'a' tags inside the message
                    links = []
                    # Use the text locator to find links only within the main message
                    if await text_locator.count() > 0:
                        a_tags = text_locator.locator("a")
                        count_a = await a_tags.count()
                        for i in range(count_a):
                            href = await a_tags.nth(i).get_attribute("href")
                            if href:
                                links.append(href)
                            
                    has_spot_link = any("spot.uz" in l for l in links)
                    
                    post_data = {
                        "id": post_id,
                        "date": date_obj.isoformat(),
                        "text_html": text_content,
                        "links": links,
                        "has_spot_link": has_spot_link
                    }
                    
                    current_batch_data.append((date_obj, post_id, post_data))

                except Exception as e:
                    print(f"Error processing a message: {e}")
            
            # Now we decide what to do
            # We want to add these to our master list
            # And check if we should stop
            
            if not current_batch_data:
                # No new messages found in this pass?
                # Maybe we didn't scroll enough?
                pass
            
            # Add to master list
            # We need to insert them. Since we scroll UP, we find OLDER messages.
            # But the DOM might contain a mix.
            # Let's just Add all new valid ids to a global list and sort later?
            # User wants "Scroll backward... Continue until you reach the first post of November 12, 2025"
            
            found_older_than_target = False
            
            for d_obj, p_id, p_data in current_batch_data:
                processed_ids.add(p_id)
                captured_posts.append(p_data)
                if d_obj < TARGET_DATE:
                    print(f"Found post from {d_obj} (older than {TARGET_DATE}). Stop condition met (eventually).")
                    found_older_than_target = True
            
            newly_added = len(current_batch_data)
            print(f"Added {newly_added} posts this batch.")

            # Stop Condition Check
            # Check the OLDEST message in the DOM / processed
            # If we have found messages older than target, AND we have covered the gap?
            # Actually, if we see a message < TARGET_DATE, we can stop *scrolling further back*.
            # But we should ensure we captured everything up to that point.
            # Since we are processing the DOM, if the oldest visible message is < TARGET_DATE, we are good.
            
            # Find oldest date in current batch (or visible messages)
            # DOM order 0 is oldest.
            if messages:
                oldest_msg = messages[0]
                # Extract date from oldest visible
                # ... reusing logic ...
                # Simply, if found_older_than_target is True, we effectively reached the past.
                # However, ensure we don't have gaps? 
                # Telegram loads contiguously. So if we hit < Nov 12, we are safe.
            
            if found_older_than_target:
                print("Reached target date. Stopping.")
                break
                
            # Scroll UP
            # How to trigger loading older messages?
            # Usually scrolling to top: window.scrollTo(0, 0)
            await page.evaluate("window.scrollTo(0, 0)")
            print("Scrolled up, waiting for load...")
            
            # Wait for meaningful change or timeout?
            # We can capture the ID of the top message before scroll, and wait until top message ID changes?
            try:
                # Wait for a "loading" spinner to disappear if it exists?
                # Or wait for new items.
                await page.wait_for_timeout(2000) # Simple wait
            except:
                pass
                
            # Safety break if no new items for a while?
            if newly_added == 0:
                print("No new items added after scroll. Retrying or stuck.")
                # Maybe force scroll again?
                await page.evaluate("window.scrollTo(0, -500)")
                await page.wait_for_timeout(2000)
                if newly_added == 0:
                    # Maybe we reached the very beginning of the channel (unlikely for 2025, but possible)
                    # OR we are not triggering the load.
                    pass

    # SAVE
    # Filter: >= Nov 12, 2025
    final_posts = []
    for p in captured_posts:
        if p['date'] >= TARGET_DATE.isoformat():
            final_posts.append(p)
            
    # Sort date desc (newest first) or asc? 
    # User said "Output ... chronologically (or reverse-chronological, whichever is default)"
    # We'll just sort Newest First for consistency with Telegram UI, or Oldest First for TTS reading flow?
    # "Chronologically" usually means Oldest -> Newest. "Reverse-chronological" is Newest -> Oldest.
    # Text-to-speech usually reads top to bottom. If user listens to "news feed", maybe newest is better?
    # User said "content of EVERY post ... between Nov 12 and today".
    # I will sort Chronologically (Oldest -> Newest) so the story unfolds? 
    # Or Newest -> Oldest?
    # Let's save Raw, and sort in Phase 2.
    # Actually, user Phase 2 says "Write the content chronologically ...".
    # I'll save raw data now.
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(final_posts, f, indent=2, ensure_ascii=False)
        
    print(f"DONE. Scanned back to {TARGET_DATE}. Found {len(final_posts)} items.")
    
    # Analyze validation
    full_articles = sum(1 for p in final_posts if p['has_spot_link'])
    text_only = len(final_posts) - full_articles
    print(f"Breakdown: {full_articles} full articles (links), {text_only} text-only.")

if __name__ == "__main__":
    asyncio.run(main())
