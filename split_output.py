import math
import os

INPUT_FILE = "Spot_News_Cleaned.txt"
SEPARATOR = "\n### NEXT ITEM ###\n"
NUM_PARTS = 40

def split_file():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r") as f:
        content = f.read()
    
    items = content.split(SEPARATOR)
    if items and items[-1].strip() == "":
        items.pop()
        
    total_items = len(items)
    chunk_size = math.ceil(total_items / NUM_PARTS)
    
    print(f"Total items: {total_items}")
    print(f"Goal Parts: {NUM_PARTS}")
    print(f"Chunk size: {chunk_size}")
    
    for i in range(NUM_PARTS):
        start = i * chunk_size
        end = start + chunk_size
        chunk_items = items[start:end]
        
        if not chunk_items:
            continue
            
        filename = f"Spot_News_Part_{i+1}.txt"
        with open(filename, "w") as f:
            text = SEPARATOR.join(chunk_items)
            f.write(text)
            f.write(SEPARATOR)
            
        print(f"Wrote {len(chunk_items)} items to {filename}")

if __name__ == "__main__":
    split_file()
