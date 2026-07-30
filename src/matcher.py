import pymupdf
import re
import json
import hashlib
import shutil
from collections import Counter
from pathlib import Path
from src.pdf_reader import PDFReader
from rapidfuzz import fuzz

PAGES_CONFIG_PATH = Path("./src/pages.json")
TEMPLATE_CONFIG_PATH = Path("./src/template.json")
BASE_DATA_PATH = Path("./src/import/split_pages/")
MINIMUM_MATCH_SCORE = 95

log_text = ""

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

def clear_directory(directory_path):
    for item in Path(directory_path).iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

def prepare_report(pdf, log, progress, request_label, request_replacements):
    print(f"Report from GUI: {pdf}")
    
    # template = Path(find_ext(pdf, "pdf")[0])
    doc = PDFReader(pdf)
    text = doc.get_text()
    clear_directory(BASE_DATA_PATH)
    doc.split_pages()

    # match pages in template to existing (basically check if new template)
    match_pages(pdf, BASE_DATA_PATH, log, progress, request_label, request_replacements)

# scan imported template pages, match to existing configs
def match_pages(pdf, match_dir, log=None, progress=None, request_label=None, request_replacements=None):
    template_config = { "filename": pdf, "pages": []}
    
    for i, f in enumerate(sorted(match_dir.iterdir(), key=lambda x: numeric_key(x.name))):
        if f.is_file():
            print(f"File {f.name}")
        else:
            return
        
        doc = pymupdf.open(f)
        page = doc[0]
        id = fingerprint_page(page, doc.name)
        # score, matching_id = score_page(page, doc.name)
        
        with open(PAGES_CONFIG_PATH) as pages_file:
            pages = json.load(pages_file)
            
        label = pages[id].get("label")
        placeholder = pages[id].get("placeholder")
            
        if (pages[id].get("id") == "" or label == ""):
            print(f"Please label page {id} with headings: {pages[id]["headings"]}")
            if request_label:
                label, placeholder = request_label(f.name, get_page_pixmap(page))
            id_from_label = normalize(label)
            pages[id]["label"] = label
            pages[id]["id"] = id_from_label
            pages[id]["placeholder"] = placeholder
            
            log_text = f"Received label and placeholder for {f.name} as {label} / {placeholder}"
            log(log_text)
            print(log_text)                
            
        if (placeholder or pages[id].get("placeholder")) and request_replacements:
            log_text = f"Requesting replacement files for {label}"
            log(log_text)
            print(log_text)
            
            replacement_filenames = request_replacements(f.name, label, get_page_pixmap(page))
        
            if replacement_filenames:
                pages[id]["replacement_filenames"] = replacement_filenames
                log_text = f"Replacing {f.name} with {replacement_filenames}"
                log(log_text)
                print(log_text)
            
        with open(PAGES_CONFIG_PATH, "w") as pages_file:
            json.dump(pages, pages_file)
        
        if log:
            log_text = f"Found {pages[id]["label"]}, saving position as {i + 1}"
            log(log_text)
            print(log_text)

        if progress:
            progress(i+1)    

        template_config["pages"].append({ "id": id, "label": pages[id]["label"], "placeholder": pages[id]["placeholder"] }) 
    
    with open(TEMPLATE_CONFIG_PATH, "w") as template:
        json.dump(template_config, template)

# Scan pages, store them, and compare them to previously scanned
# pages in order to match prior page orders and detect
# new pages/slides
def fingerprint_page(page, filename):
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
        
        # compare to see if new
        score, matching_id = score_page(page, filename)
        
        with open(PAGES_CONFIG_PATH) as pages_file:
            pages = json.load(pages_file)      
        
        page_hash = hashlib.sha1(normalized.encode()).hexdigest()[:12]
        print(f"Page hash: {page_hash}, matching_id: {matching_id}, match? {page_hash == matching_id}")
        
        # if new, store as new 
        if (score < MINIMUM_MATCH_SCORE and page_hash != matching_id):            
            fingerprint = {
                "id": "",
                "label": "",
                "clean_text": stabilized,
                "keywords": keywords,
                "headings": headings,
                # "layout": layout,
                "page_width": page.rect.width,
                "page_height": page.rect.height,
            }
            
            pages[page_hash] = fingerprint
            # print(f"New fingerprint: {pages[page_hash]}")
            
            
            
            with open(PAGES_CONFIG_PATH, "w") as pages_file:
                json.dump(pages, pages_file)
            
            return page_hash
        else:
            # print(f"Old fingerprint: {pages[matching_id]}")
            pages[matching_id]["clean_text"] = stabilized
            pages[matching_id]["keywords"] = keywords
            pages[matching_id]["headings"] = headings
            pages[matching_id]["page_width"] = page.rect.width
            pages[matching_id]["page_height"] = page.rect.height
            # print(f"Updated fingerprint: {pages[matching_id]}")
            
            with open(PAGES_CONFIG_PATH, "w") as pages_file:
                json.dump(pages, pages_file)
            return matching_id
                 
# score page against existing pages.json pages
def score_page(page, filename):
    with open(PAGES_CONFIG_PATH) as pages_file:
        pages = json.load(pages_file)
    
    highest_score = 0
    matching_id = ""
    
    for old_page in pages:
        old_text = pages[old_page]["clean_text"]
        new_text = stabilize(normalize(page.get_text())) 
        
        score = fuzz.token_sort_ratio(
            old_text,
            new_text
        )
        if highest_score < score:
            highest_score = score
            matching_id = old_page
    # print(f"old text: {pages[matching_id]["clean_text"]}\n\nnew_text: {stabilize(normalize(page.get_text())) }")
    # print(f"Len of old_text {len(pages[matching_id]["clean_text"])}, of new_text {len(stabilize(normalize(page.get_text())) )}")
    print(f"Highest Score for page {filename}: {highest_score, matching_id}")
    
    return highest_score, matching_id 
    
# Normalize text for parsing
def normalize(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    
    # print(f"Normalized text: {text}")
    return text.strip()

# Strip misleading content
def stabilize(text):
    text = re.sub(r"\$[\d,]+\.\d{2}", "<money>", text) # remove money
    text = re.sub(r"\d+", "<number>", text) # remove numbers
    text = re.sub(r"\d{1,2}/\d{1,2}/\d{2,4}", "<date>", text) # remove dates
    
    # print(f"Stabilized text: {text}")
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
    
    # print(f"Keywords: {keywords}")
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
                  
    # print(f"Headings: {headings}")  
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
                    
    # print(f"Layout: {spans}")
    return spans
        
def numeric_key(filename):
    parts = re.split(r'(\d+)', filename)
    return [int(p) if p.isdigit() else p for p in parts]

def get_page_pixmap(page):
    # page = pymupdf.open(Path(filename)).load_page(0)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(.5, .5))
    return pix.tobytes("png")