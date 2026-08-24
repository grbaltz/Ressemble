import pymupdf
import re
import json
import hashlib
import shutil
from collections import Counter
from pathlib import Path
from src.pdf_reader import PDFReader
from src.office_import import prepare_emx_source
from src.paths import PAGES_CONFIG_PATH, TEMPLATE_CONFIG_PATH, BASE_DATA_PATH, ADVISORS_PATH
from rapidfuzz import fuzz

MINIMUM_MATCH_SCORE = 95
IMAGE_MATCH_SCORE = 90   # slightly looser than text match, since avg-hash is coarser
IMAGE_HASH_SIZE = 16     # render to a 16x16 grayscale grid -> 256-bit hash

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
    split_dir = doc.split_pages()
    
    new_template = refresh or is_new_template(pdf)

    # match pages in template to existing (basically check if new template)
    matched_pages, new_page_ids = match_pages(pdf, split_dir, log, progress)
    
    if new_template or len(new_page_ids) > 0:
        request_labels(
            matched_pages,
            new_page_ids,
            log,
            request_label,
        )

    sources = request_source_files(
        log,
        request_sources,
    )

    save_template(pdf, matched_pages, sources)

    get_emx_order()
    get_bd_order()
    
    return matched_pages, sources

# scan imported template pages, match to existing configs
def match_pages(pdf, match_dir, log=None, progress=None):
    matched_pages = []
    new_page_ids = []

    files = sorted(match_dir.iterdir(), key=lambda x: numeric_key(x.name))
    total = len(files)

    for i, f in enumerate(files):
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
            new_page_ids.append(id)

        # id will be same as existing id if matched
        matched_pages.append({
            "id": id,
            "filename": f.name,
            "page": page,
        })

        if progress:
            progress(i + 1, total)

    return matched_pages, new_page_ids
        
def request_labels(
    matched_pages,
    new_page_ids,
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

        if id not in new_page_ids:
            continue

        label = request_label(
            page_info["filename"],
            get_page_pixmap(page)
        )

        pages[id]["label"] = label
        pages[id]["id"] = normalize(label)
        # pages[id]["slot"] = slot

    with open(PAGES_CONFIG_PATH, "w") as f:
        json.dump(pages, f)
        
def request_source_files(log, request_sources):
    log("Selecting EMX and BlackDiamond PDFs...")

    emx_pdf, blackdiamond_pdf = request_sources()

    if Path(emx_pdf).suffix.lower() in (".doc", ".docx"):
        log("Converting EMX Word document to PDF and removing bold styling from page 1…")
        emx_pdf = prepare_emx_source(emx_pdf)

    with Path(emx_pdf) as emx_dir, Path(blackdiamond_pdf) as blackdiamond_dir:
        print(f"emx_dir: {emx_dir.stem}, bd_dir: {blackdiamond_dir.stem}")
        return {
            "emx_pdf": emx_pdf,
            "emx_dir": str(Path(BASE_DATA_PATH / emx_dir.stem)),
            "blackdiamond_pdf": blackdiamond_pdf,
            "blackdiamond_dir": str(Path(BASE_DATA_PATH / blackdiamond_dir.stem)),
        }
    
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
    slot = ""

    # is image only page: no text
    is_image_page = len(text.strip()) == 0
    
    # get keywords
    keywords = parse_keywords(stabilized)
    
    # get headings
    headings = parse_headings(page)
    
    # check for specific page criteria
    # cover
    if re.search(r'household presentation for date', stabilized, re.IGNORECASE):
        slot = "cover"

    # advisors
    if re.search(r'your rebalance team', stabilized, re.IGNORECASE):
        slot = "advisors"

    # emx automatic
    if re.search(r"EMX financial plan", stabilized, re.IGNORECASE) and re.search(r"Cash Flow Report and Net Worth Statement", stabilized, re.IGNORECASE):
        slot = "emx"

    if re.search(r"insert black diamond performance report", stabilized, re.IGNORECASE):
        slot = "bd"

    # bd automatic

    # portfolio title pages: three template pages share the "Portfolio &
    # Allocation" heading, distinguished by subtitle. assemble_report() keeps
    # either the generic page alone (single account) or both split pages
    # together and drops the generic one (multiple accounts) -- see the
    # portfolioAllAccounts/portfolioIndividualAccount/portfolioGeneric
    # handling in assembler.py.
    if re.search(r"all accounts.*combined", stabilized, re.IGNORECASE):
        slot = "portfolioAllAccounts"

    if re.search(r"by individual account", stabilized, re.IGNORECASE):
        slot = "portfolioIndividualAccount"

    if re.search(r"portfolio\s*&?\s*allocation", stabilized, re.IGNORECASE) and not re.search(r"all accounts|individual account", stabilized, re.IGNORECASE):
        slot = "portfolioGeneric"

    # enroll/enrolled plan360: two variant pages sharing one slot value --
    # assemble_report() tells them apart by template order (1st = pitch,
    # 2nd = enrolled confirmation), not by slot name, so both map here.
    if re.search(r"introducing rebalance 360.s newest service|enrollment required", stabilized, re.IGNORECASE):
        slot = "view360"

    if re.search(r"congratulations on enrolling", stabilized, re.IGNORECASE):
        slot = "view360"

    # bd header page

    #

    image_hash = None

    # score and compare against previous pages
    if is_image_page:
        image_hash = get_image_hash(page)
        score, matching_id = score_page_visual(image_hash, filename)
        match_threshold = IMAGE_MATCH_SCORE
        # get id from image hash, not empty text
        page_hash = hashlib.sha1(image_hash.encode()).hexdigest()[:12]
    else:
        score, matching_id = score_page(page, filename)
        match_threshold = MINIMUM_MATCH_SCORE
        page_hash = hashlib.sha1(normalized.encode()).hexdigest()[:12]
    
    with open(PAGES_CONFIG_PATH) as pages_file:
        pages = json.load(pages_file)      
    
    print(f"Page hash: {page_hash}, matching_id: {matching_id}, match? {page_hash == matching_id}")
    
    # if new, store as new 
    if (score < match_threshold and page_hash != matching_id):            
        fingerprint = {
            "id": "",
            "label": "",
            "clean_text": stabilized,
            "keywords": keywords,
            "headings": headings,
            "slot": slot,
            "page_width": page.rect.width,
            "page_height": page.rect.height,
            "filename": filename,
            "image_hash": image_hash,
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
        pages[matching_id]["filename"] = filename
        pages[matching_id]["image_hash"] = image_hash
        pages[matching_id]["slot"] = slot if not pages[matching_id].get("slot") else pages[matching_id].get("slot")
        
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

def get_image_hash(page, hash_size=IMAGE_HASH_SIZE):
    rect = page.rect
    matrix = pymupdf.Matrix(hash_size / rect.width, hash_size / rect.height)
    pix = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csGRAY, alpha=False)
    pixels = list(pix.samples)
    avg = sum(pixels) / len(pixels)
    return "".join("1" if p > avg else "0" for p in pixels)

def hamming_distance(hash_a, hash_b):
    if len(hash_a) != len(hash_b):
        # mismatched hash sizes (old data from before this change)
        return max(len(hash_a), len(hash_b))
    return sum(a != b for a, b in zip(hash_a, hash_b))

def score_page_visual(image_hash, filename):
    with open(PAGES_CONFIG_PATH) as pages_file:
        pages = json.load(pages_file) 

    highest_score = 0
    matching_id = 0

    for old_id, data in pages.items():
        old_hash = data.get("image_hash")
        if not old_hash:
            continue

        distance = hamming_distance(old_hash, image_hash)
        score = 100 * (1 - distance / len(image_hash))

        if score > highest_score:
            highest_score = score
            matching_id = old_id

    print(f"Highest visual score for page {filename}: {highest_score, matching_id}")
    return highest_score, matching_id

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

def save_template(pdf, matched_pages, sources):
    with open(PAGES_CONFIG_PATH) as f:
        pages = json.load(f)
        
    template = { "filename": pdf, "pages": [], "sources": sources}
    
    for page_info in matched_pages:
        id = page_info["id"]
        
        template["pages"].append({
            "id": id, 
            "label": pages[id].get("label"),  
            "filename": pages[id].get("filename"), 
            "placeholder": pages[id].get("placeholder"), 
            "slot": pages[id].get("slot")
        })
        
    with open(TEMPLATE_CONFIG_PATH, "w") as f:
        json.dump(template, f, indent=2)

def get_emx_order():
    with open(TEMPLATE_CONFIG_PATH, "r") as t:
        template = json.load(t)
    
    if not template["sources"]["emx_pdf"]:
        print("No emx file saved")
        return
    
    doc = PDFReader(template["sources"]["emx_pdf"])
    split_dir = doc.split_pages()

    for page in sorted(split_dir.glob("*.pdf"), key=lambda x: numeric_key(x.name)):
        shutil.move(page, split_dir / page.name)

def get_bd_order():
    with open(TEMPLATE_CONFIG_PATH, "r") as t:
        template = json.load(t)
    
    if not template["sources"]["blackdiamond_pdf"]:
        print("No blackdiamond file saved")
        return
    
    doc = PDFReader(template["sources"]["blackdiamond_pdf"])
    split_dir = doc.split_pages()
    
    bd1_dir = split_dir / "bd1"
    bd2_dir = split_dir / "bd2"

    bd1_dir.mkdir(exist_ok=True)
    bd2_dir.mkdir(exist_ok=True)

    unsorted = []
    
    for page_info in sorted(split_dir.glob("*.pdf"), key=lambda x: numeric_key(x.name)):
        print(f"page_info: {numeric_key(page_info.name)[1]}")
        
        doc = pymupdf.open(page_info)
        page = doc[0]
        
        text = page.get_text()

        if "Allocation and Return" not in text:
            shutil.move(page_info, bd1_dir / page_info.name)
            continue            

        matches = page.search_for("Value ($)")
        if not matches:
            shutil.move(page_info, bd1_dir / page_info.name)
            continue

        header = matches[0]

        column_rect = pymupdf.Rect(
            header.x0 - 5,
            header.y1,
            header.x1 + 5,
            page.rect.height
        )

        text = page.get_text("text", clip=column_rect)
        
        numbers = re.findall(r'\d[\d,]*', text)

        total = int(numbers[-1].replace(",", ""))

        shutil.move(page_info, bd2_dir / page_info.name)
        unsorted.append({"name": Path(page_info).name, "value": total })
    
    unsorted.sort(key=lambda x: x["value"], reverse=True)

    pages = [bd2_dir / p["name"] for p in unsorted]

    temps = []

    for i, page in enumerate(pages):
        tmp = page.with_name(f"tmp_{i}.pdf")
        page.rename(tmp)
        temps.append(tmp)

    for i, tmp in enumerate(temps):
        tmp.rename(bd2_dir / f"{i}.pdf")
        
def select_advisor_file(log, request_advisors):
    log("Request Advisors")
    advisors = request_advisors()
    advisors_filename = "_".join(advisors).strip().lower().replace(" ", "") + ".pdf"
    print(f"Selected advisors: {advisors} {advisors_filename}")
    path = Path(ADVISORS_PATH / advisors_filename)
    print(f"path {path}, exists? {path.exists()}")
    
    if path.exists() and path.is_file():
        with open(TEMPLATE_CONFIG_PATH, "r") as t:
            template = json.load(t)
        
        template["advisors_filename"] = str(path)
        
        with open(TEMPLATE_CONFIG_PATH, "w") as t:
            json.dump(template, t)
        
        print("dumped")
        return path