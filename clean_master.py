import re

INPUT_FILE = "Spot_News_Unfiltered.txt"
OUTPUT_FILE = "Spot_News_Cleaned.txt"
SEPARATOR = "\n### NEXT ITEM ###\n"

def clean_block(text):
    lines = text.split("\n")
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # 1. Remove Garbage
        if line == "Комментарии": continue
        if line.startswith("Комментарии:"): continue
        if line.isdigit(): continue # View counts like "1 786" might be handled by spaces?
        # Check for "1 786" pattern (digit space digit)
        if re.match(r"^\d+[\s\d]*$", line): continue 
        
        # Remove Hashtags lines
        if line.startswith("#"): continue
        
        # Remove "Also read" if missed
        if "Читайте также" in line or "Also read" in line: continue
        
        cleaned_lines.append(line)
        
    # 2. Reflow Paragraphs
    # Attempt to merge lines that are likely part of the same paragraph
    merged_grafs = []
    current_graf = []
    
    for line in cleaned_lines:
        if not current_graf:
            current_graf.append(line)
            continue
            
        prev_line = current_graf[-1]
        
        # Heuristic: Does prev_line end with a sentence stopper?
        # If yes, start new graf. If no, merge.
        # Also check if current line starts with Uppercase? (Not always reliable in headlines)
        
        # Common sentence stoppers in Russian/English
        if prev_line[-1] in [".", "!", "?", ":", ";"]:
            # Close previous graf
            merged_grafs.append(" ".join(current_graf))
            current_graf = [line]
        else:
            # Continue graf
            current_graf.append(line)
            
    if current_graf:
        merged_grafs.append(" ".join(current_graf))
        
    return "\n\n".join(merged_grafs)
            

def main():
    with open(INPUT_FILE, "r") as f:
        content = f.read()
        
    items = content.split(SEPARATOR)
    cleaned_items = []
    
    for item in items:
        item = item.strip()
        if not item: continue
        
        # Separate Title/Header from Body?
        # My previous format:
        # Title
        # \n\n
        # Body...
        
        parts = item.split("\n\n")
        new_parts = []
        for p in parts:
            new_p = clean_block(p)
            if new_p:
                new_parts.append(new_p)
                
        cleaned_item = "\n\n".join(new_parts)
        if cleaned_item:
            cleaned_items.append(cleaned_item)
            
    print(f"Processed {len(cleaned_items)} items.")
    
    with open(OUTPUT_FILE, "w") as f:
        # Write back with separator
        # Join with double separator to be safe? No, just SEPARATOR
        # But ensure each item ends with one?
        for item in cleaned_items:
            f.write(item)
            f.write(SEPARATOR)
            
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
