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

def prepare_report(pdf, refresh, log, progress, request_label, request_sources):
    print(f"Report from GUI: {pdf}")
    
    doc = PDFReader(pdf)
    clear_directory(BASE_DATA_PATH)
    doc.split_pages()
    
    new_template = refresh or is_new_template(pdf)

    # match pages in template to existing (basically check if new template)
    matched_pages = match_pages(pdf, BASE_DATA_PATH, log, progress)
    
    if new_template:
        request_labels(
            matched_pages,
            log,
            request_label,
        )

    sources = request_source_files(
        log,
        request_sources,
    )

    save_template(pdf, matched_pages, sources)
    
    return matched_pages, sources

# scan imported template pages, match to existing configs
def match_pages(pdf, match_dir, log=None, progress=None):    
    matched_pages = []
    
    for i, f in enumerate(sorted(match_dir.iterdir(), key=lambda x: numeric_key(x.name))):
        if f.is_file():
            print(f"File {f.name}")
        else:
            return
        
        doc = pymupdf.open(f)
        page = doc[0]
        id, matched = fingerprint_page(page, doc.name)
        
        if matched:
            log(f"Found file {f.name}")
        else:
            log(f"New file {f.name}")
        
        # id will be same as existing id if matched
        matched_pages.append({
            "id": id,
            "filename": f.name,
            "page": page,
        }) 
            
    return matched_pages 
        
def request_labels(
    matched_pages,
    log,
    request_label
):
    # Refresh and reset the template
    log("Refreshing")
    with open(TEMPLATE_CONFIG_PATH, "w") as template:
        json.dump({}, template)
            
    with open(PAGES_CONFIG_PATH) as f:
        pages = json.load(f)

    for page_info in matched_pages:
        id = page_info["id"]
        page = page_info["page"]

        label, slot = request_label(
            page_info["filename"],
            get_page_pixmap(page)
        )

        pages[id]["label"] = label
        pages[id]["id"] = normalize(label)
        pages[id]["slot"] = slot

    with open(PAGES_CONFIG_PATH, "w") as f:
        json.dump(pages, f)
        
def request_source_files(log, request_sources):
    log("Selecting EMX and BlackDiamond PDFs...")

    emx_pdf, blackdiamond_pdf = request_sources()

    return {
        "emx": emx_pdf,
        "blackdiamond": blackdiamond_pdf,
    }
        
def save_template(pdf, matched_pages, sources):
    with open(PAGES_CONFIG_PATH) as f:
        pages = json.load(f)
        
    template = { "filename": pdf, "pages": [], "sources": sources}
    
    for page_info in matched_pages:
        id = page_info["id"]
        
        template["pages"].append({ "id": id, "label": pages[id]["label"], "placeholder": pages[id]["placeholder"] })
        
    with open(TEMPLATE_CONFIG_PATH, "w") as f:
        json.dump(template, f, indent=2)
    
# Scan pages, store them, and compare them to previously scanned
# pages in order to match prior page orders and detect
# new pages/slides
#
# Returns True if matched
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
                "slot": "",
                "page_width": page.rect.width,
                "page_height": page.rect.height,
            }
            
            pages[page_hash] = fingerprint
            
            with open(PAGES_CONFIG_PATH, "w") as pages_file:
                json.dump(pages, pages_file)
            
            return page_hash, False
        else:
            pages[matching_id]["clean_text"] = stabilized
            pages[matching_id]["keywords"] = keywords
            pages[matching_id]["headings"] = headings
            pages[matching_id]["page_width"] = page.rect.width
            pages[matching_id]["page_height"] = page.rect.height
            
            with open(PAGES_CONFIG_PATH, "w") as pages_file:
                json.dump(pages, pages_file)
            return matching_id, True
                 
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

def is_new_template(pdf):
    if not TEMPLATE_CONFIG_PATH.exists():
        return True

    with open(TEMPLATE_CONFIG_PATH) as f:
        template = json.load(f)

    return template.get("filename") != pdf