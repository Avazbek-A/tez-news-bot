import asyncio
import aiohttp
from playwright.async_api import async_playwright
from fake_useragent import UserAgent

URL = "https://www.spot.uz/ru/2025/11/12/frame/"
ua = UserAgent()

async def test_aiohttp():
    print(f"Testing aiohttp for {URL}...")
    headers = {"User-Agent": ua.random}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(URL, headers=headers) as resp:
                print(f"Status: {resp.status}")
                text = await resp.text()
                print(f"Content length: {len(text)}")
                if "Вы не авторизованы" in text:
                    print("FAIL: 'Not authorized' found in aiohttp response.")
                elif "contentBox" in text:
                    print("SUCCESS: contentBox found.")
                else:
                    print("FAIL: contentBox NOT found.")
    except Exception as e:
        print(f"Error: {e}")

async def test_playwright():
    print(f"Testing Playwright for {URL}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL)
        content = await page.content()
        print(f"Content length: {len(content)}")
        if "Вы не авторизованы" in content:
            # It might appear in comments, so check if ONLY that appears or if content exists
            pass
            
        if "contentBox" in content:
             print("SUCCESS: contentBox found in Playwright.")
        else:
             print("FAIL: contentBox NOT found in Playwright.")
        await browser.close()

async def main():
    await test_aiohttp()
    print("-" * 20)
    await test_playwright()

if __name__ == "__main__":
    asyncio.run(main())
