import os
import asyncio
from playwright.async_api import async_playwright

SEPARATOR = "\n### NEXT ITEM ###\n"

CSS = """
<style>
    body { font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 40px; color: #333; font-size: 18px; }
    article { margin-bottom: 50px; border-bottom: none; padding-bottom: 0px; page-break-after: always; }
    h1 { font-size: 28px; margin-bottom: 15px; color: #111; }
    p { margin-bottom: 20px; text-align: justify; }
    .meta { font-size: 14px; color: #666; margin-bottom: 25px; font-style: italic; }
</style>
"""

def text_to_html(text_file, html_file):
    with open(text_file, "r") as f:
        content = f.read()
    
    items = content.split(SEPARATOR)
    
    html_content = [f"<!DOCTYPE html><html lang='ru'><head><meta charset='utf-8'>{CSS}</head><body>"]
    
    for item in items:
        item = item.strip()
        if not item: continue
        
        # Optimize text for reading
        item = item.replace("**", "")
        
        blocks = item.split("\n\n")
        if not blocks: continue
        
        html_content.append("<article>")
        
        header_block = blocks[0].strip()
        
        if header_block.startswith("Telegram Post ["):
            clean_header = header_block.replace("[", "").replace("]", "")
            html_content.append(f"<p class='meta'>{clean_header}</p>")
            
            for block in blocks[1:]:
                html_content.append(f"<p>{block.replace(chr(10), '<br>')}</p>")
                
        else:
            html_content.append(f"<h1>{header_block}</h1>")
            for block in blocks[1:]:
                html_content.append(f"<p>{block.replace(chr(10), '<br>')}</p>")
                
        html_content.append("</article>")
        
    html_content.append("</body></html>")
    
    with open(html_file, "w") as f:
        f.write("\n".join(html_content))
    print(f"Generated {html_file}")

async def html_to_pdf(html_file, pdf_file):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        # Need absolute path for local file
        abs_path = os.path.abspath(html_file)
        await page.goto(f"file://{abs_path}")
        await page.pdf(path=pdf_file, format="A4", margin={"top": "2cm", "bottom": "2cm", "left": "2cm", "right": "2cm"})
        await browser.close()
    print(f"Generated {pdf_file}")

async def main():
    # Find all Part txt files
    # Only process Part_1 to Part_40
    # Or just scan dir
    files = [f for f in os.listdir(".") if f.startswith("Spot_News_Part_") and f.endswith(".txt")]
    
    # Sort numerically
    def get_num(s):
        try:
            return int(s.split("_")[-1].replace(".txt", ""))
        except:
            return 0
    files.sort(key=get_num)
    
    for txt_file in files:
        base_name = txt_file.replace(".txt", "")
        html_file = f"{base_name}.html"
        pdf_file = f"{base_name}.pdf"
        
        print(f"Processing {txt_file}...")
        text_to_html(txt_file, html_file)
        await html_to_pdf(html_file, pdf_file)

if __name__ == "__main__":
    asyncio.run(main())
