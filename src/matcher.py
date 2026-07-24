import pymupdf
import re
import json
import hashlib
from collections import Counter
from pathlib import Path
from pdf_reader import PDFReader

PAGES_CONFIG_PATH = Path("./src/pages.json")

STOPWORDS = {
    "the",
    "and",
    "to",
    "of",
    "in",
    "for",
    "is",
    "on",
    "with",
    "a",
    "an"
}

# Scan pages, store them, and compare them to previously scanned
# pages in order to match prior page orders and detect
# new pages/slides
def match_pages(match_dir):
    for f in match_dir.iterdir():
        if f.is_file():
            print(f"File {f.name}")
        else:
            return
        
        doc = pymupdf.open(f)
        page = doc[0]
        
        # get normalized and stabilized text
        text = page.get_text()
        normalized = normalize(text)
        stabilized = stabilize(normalized)
        
        # get keywords
        keywords = parse_keywords(stabilized)
        
        # get headings
        headings = parse_headings(page)
        
        # get layout
        # layout = parse_layout(page)
        
        # store   
        with open(PAGES_CONFIG_PATH) as pages_file:
            pages = json.load(pages_file)
            
        fingerprint = {
            "clean_text": stabilized,
            "keywords": keywords,
            "headings": headings,
            # "layout": layout,
            "page_width": page.rect.width,
            "page_height": page.rect.height,
        }
        
        # label, id = get_label_id(fingerprint)
        
        # print(f"Page label/id: {label}/{id}")
        # fingerprint["id"] = id
        
        page_hash = hashlib.sha1(normalized.encode()).hexdigest()[:12]
        pages[page_hash] = fingerprint
                 
        with open(PAGES_CONFIG_PATH, "w") as pages_file:
            json.dump(pages, pages_file)
        
        # compare to pages.py
        
# Normalize text for parsing
def normalize(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    
    print(f"Normalized text: {text}")
    return text.strip()

# Strip misleading content
def stabilize(text):
    text = re.sub(r"\$[\d,]+\.\d{2}", "<money>", text) # remove money
    text = re.sub(r"\d+", "<number>", text) # remove numbers
    text = re.sub(r"\d{1,2}/\d{1,2}/\d{2,4}", "<date>", text) # remove dates
    
    print(f"Stabilized text: {text}")
    return text

# Get most common keywords for indentification
def parse_keywords(text):
    words = re.findall("[a-z]{3,}", text)
    
    counts = Counter(
        w for w in words
        if w not in STOPWORDS
    )
    
    keywords = [
        word
        for word, _
        in counts.most_common(20)
    ]
    
    print(f"Keywords: {keywords}")
    return keywords

# Get headings for powerful bits
def parse_headings(page):
    headings = []
    
    blocks = page.get_text("dict")["blocks"]
    
    for block in blocks:
        if block["type"] != 0:
            continue
        
        for line in block["lines"]:
            for span in line["spans"]:
                if span["size"] > 16:
                    headings.append(span["text"])
                  
    print(f"Headings: {headings}")  
    return headings

def parse_layout(page):
    spans = []
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
            if block["type"] != 0:
                continue
            
            for line in block["lines"]:
                for span in line["spans"]:
                    spans.append(span["text"])
                    
    print(f"Layout: {spans}")
    return spans

# def get_label_id(fingerprint):
#     label = ""
#     id = ""
#     if len(fingerprint["headings"]) > 0 and len(fingerprint["headings"][0]):
#         label = fingerprint["headings"][0]
#     elif len(fingerprint["layout"]) > 0:
#         label = fingerprint["layout"][0]
#     elif len(fingerprint["keywords"]) > 0:
#         label = fingerprint["keywords"][0]
        
#     id = label.replace(" ", "")
#     id = id[0].lower() + id[1:]
    
#     return label, id
        