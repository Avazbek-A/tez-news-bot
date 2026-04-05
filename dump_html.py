from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://www.spot.uz/ru/2026/01/16/move-headliners/")
        content = page.content()
        with open("sample_article.html", "w") as f:
            f.write(content)
        browser.close()

if __name__ == "__main__":
    run()
