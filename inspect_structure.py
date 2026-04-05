from bs4 import BeautifulSoup

def inspect():
    try:
        with open("sample_article.html", "r") as f:
            html = f.read()
        soup = BeautifulSoup(html, "lxml")
        
        print("H1:", soup.find("h1"))
        
        # Find divs with 'content' in class
        divs = soup.find_all("div", class_=lambda c: c and "content" in c)
        if divs:
             d = divs[0]
             print(f"FIRST ContentBox Text: {d.get_text(separator='|', strip=True)}")
            
        # Find divs with 'txt' in class
        divs_txt = soup.find_all("div", class_="txt")
        for d in divs_txt:
             print(f"Class: txt, Text Len: {len(d.get_text(strip=True))}, First 50: {d.get_text(strip=True)[:50]}")

    except Exception as e:
        print(e)

if __name__ == "__main__":
    inspect()
