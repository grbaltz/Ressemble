# import pandas as pd
from os import path
from pathlib import Path
from glob import glob
import shutil
import json
import re
import tempfile
import pymupdf
from datetime import date, timedelta

REPO_ROOT = Path(__file__).resolve().parent.parent

PAGES_CONFIG_PATH = REPO_ROOT / "src" / "pages.json"
TEMPLATE_CONFIG_PATH = REPO_ROOT / "src" / "template.json"
BASE_DATA_PATH = REPO_ROOT / "src" / "import" / "split_pages"
ADVISORS_PATH = REPO_ROOT / "src" / "import" / "advisors"
TEAR_SHEETS_PATH = REPO_ROOT / "src" / "import" / "tear_sheets"
EXPORT_PATH = REPO_ROOT / "src" / "export"

AVENIR_BLACK_FONT_FILE = str(REPO_ROOT / "src" / "fonts" / "Avenir Black.ttf")
TIMES_NEW_ROMAN_FONT_FILE = str(REPO_ROOT / "src" / "fonts" / "Times New Roman.ttf")

MODEL_PATTERN = re.compile(r"Model:\s*(.+)")

# Page-number footer style: reuses the bundled Times New Roman (already
# needed for the cover date) and the same muted gray used for the cover
# page's body copy, at a 0.5in margin matching Acrobat's own footer default.
PAGE_NUMBER_FONT_FILE = TIMES_NEW_ROMAN_FONT_FILE
PAGE_NUMBER_COLOR = 7698041
PAGE_NUMBER_SIZE = 10
PAGE_NUMBER_MARGIN = 36

def assemble_report(log, progress, advisors_filename, client_name, enrolled, target_date=None, include_page_numbers=True):
    # select_advisor_file(log, request_advisors)
    print("assemble")

    bd_slot = 1
    view360_slot = 1

    # assemble array of files in order, then combine them
    report_pages = []
    temp_files = []
    
    ###
    # loop across all files in template.pages
    # check if page is placeholder
    #   if yes -> check if emx/bd -> insert emx/bd1/bd2
    #   if no -> insert page
    ###
    
    with open(TEMPLATE_CONFIG_PATH, "r") as t:
        template = json.load(t)

    # Number of accounts is however many pages ended up in bd2 -- the same
    # sorted, one-page-per-account set the tear-sheet model lookup reads.
    bd_account_count = 0
    blackdiamond_dir = template["sources"].get("blackdiamond_dir")
    if blackdiamond_dir:
        bd2_dir = Path(blackdiamond_dir) / "bd2"
        if bd2_dir.exists():
            bd_account_count = len(list(bd2_dir.glob("*.pdf")))

    total_pages = len(template["pages"])

    for i, page in enumerate(template["pages"]):
        print(f"page: {page}")

        if progress:
            progress(i + 1, total_pages)

        doc = pymupdf.open(page.get("filename"))
        pdf = doc[0]

        # check if placeholder
        if not page.get("placeholder") and not page.get("slot"):
            report_pages.append(page["filename"])
            continue
        
        match page["slot"]:
            case "cover":
                print("Cover slot")

                # Work on a throwaway copy so the source template page
                # (page["filename"]) stays pristine and reusable next run.
                cover_page = make_working_copy(page["filename"])
                temp_files.append(cover_page)

                old_text = "The ### Household"
                new_text = "The " + client_name + " Household"
                replace_text_with_formatting(cover_page, old_text, new_text, AVENIR_BLACK_FONT_FILE)

                date_text = format_report_date(target_date or next_monday())
                replace_text_with_formatting(cover_page, "Date, Year", date_text, TIMES_NEW_ROMAN_FONT_FILE)

                report_pages.append(cover_page)
            case "portfolioAllAccounts" | "portfolioIndividualAccount":
                print(f"{page['slot']} slot")

                # These two only appear when there's more than one BD
                # account -- a single account uses the generic title page
                # instead (portfolioGeneric case below).
                if bd_account_count == 1:
                    print(f"skipping {page['slot']} title page (single account)")
                else:
                    report_pages.append(page["filename"])
            case "portfolioGeneric":
                print("portfolioGeneric slot")

                if bd_account_count == 1:
                    report_pages.append(page["filename"])
                else:
                    print("skipping portfolioGeneric title page (multiple accounts)")
            case "advisors":
                print("Advisors slot")

                path = template.get("advisors_filename")

                if not path:
                    print("no advisors source provided")
                    report_pages.append(page["filename"])
                    continue

                # page = Path(path)
                print(f"adv path: {path}")
                report_pages.append(path)
            case "emx":
                print("EMX slot")
                # get emx source from template.json
                # get pages from import/split_pages/{emx_source}
                path = template["sources"]["emx_dir"]

                if not path:
                    print("no emx source provided")
                    report_pages.append(page["filename"])
                    continue

                pages = Path(path)
                print(f"pages: {pages}")
                for p in sorted(pages.glob("*.pdf"), key=lambda x: numeric_key(x.name)):
                    print(f"page {str(p)}")
                    report_pages.append(str(p))
            case "bd":
                print("Black Diamond slot")
                # get bd source from template.json
                # get pages from import/split_pages/{bd_source}
                path = template["sources"]["blackdiamond_dir"]

                if not path:
                    print("no bd source provided")
                    report_pages.append(page["filename"])
                    continue

                pages = Path(f"{path}/bd{bd_slot}")
                print(f"pages: {pages}")
                sorted_pages = sorted(pages.glob("*.pdf"), key=lambda x: numeric_key(x.name))

                if bd_slot == 2 and sorted_pages:
                    tear_sheet = find_tear_sheet_for_model(sorted_pages[0])
                    if tear_sheet:
                        report_pages.append(str(tear_sheet))

                for p in sorted_pages:
                    print(f"page {str(p)}")
                    report_pages.append(str(p))
                bd_slot += 1
            case "view360":
                print("View360 slot")

                # Two variant pages, in template order: 1st = not enrolled
                # pitch, 2nd = enrolled confirmation. Only the one matching
                # the client's actual enrollment status gets included.
                is_enrolled_page = view360_slot == 2

                if is_enrolled_page == bool(enrolled):
                    report_pages.append(page["filename"])
                else:
                    print(f"skipping view360 page {view360_slot} (enrolled={enrolled})")

                view360_slot += 1
            case _:
                print("no slot saved")
                report_pages.append(page["filename"])
                continue

    print(f"Report pages: {report_pages}")
    try:
        report_path = merge_pdfs(report_pages, f"{EXPORT_PATH}/report_{date.today()}.pdf")
        if include_page_numbers:
            add_page_numbers(report_path, skip_pages=1)
    finally:
        for temp_file in temp_files:
            Path(temp_file).unlink(missing_ok=True)
    print(f"report_page: {report_path}")
    return report_path

def add_page_numbers(pdf_path, skip_pages=1):
    doc = pymupdf.open(pdf_path)

    fontname = Path(PAGE_NUMBER_FONT_FILE).stem.replace(" ", "-")
    color = int_to_rgb(PAGE_NUMBER_COLOR)
    font = pymupdf.Font(fontfile=PAGE_NUMBER_FONT_FILE)

    for page_num in range(skip_pages, len(doc)):
        page = doc[page_num]
        page.insert_font(fontname=fontname, fontfile=PAGE_NUMBER_FONT_FILE)

        # The cover (page_num 0) counts as page "1" even though it's
        # unlabeled, so labels are just the 1-indexed page number.
        label = str(page_num + 1)
        text_width = font.text_length(label, fontsize=PAGE_NUMBER_SIZE)

        x = page.rect.width - PAGE_NUMBER_MARGIN - text_width
        y = page.rect.height - PAGE_NUMBER_MARGIN

        page.insert_text((x, y), label, fontname=fontname, fontsize=PAGE_NUMBER_SIZE, color=color)

    doc.save(pdf_path, incremental=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
    doc.close()

def make_working_copy(source_path):
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", prefix="cover_", delete=False)
    tmp.close()
    shutil.copy2(source_path, tmp.name)
    return tmp.name

def next_monday(today=None):
    today = today or date.today()
    days_ahead = (7 - today.weekday()) % 7
    return today + timedelta(days=days_ahead)

def format_report_date(d):
    return f"{d.strftime('%B')} {d.day}, {d.year}"

def numeric_key(filename):
    parts = re.split(r'(\d+)', filename)
    return [int(p) if p.isdigit() else p for p in parts]

def extract_account_model(pdf_path):
    doc = pymupdf.open(pdf_path)
    text = doc[0].get_text()
    doc.close()

    match = MODEL_PATTERN.search(text)
    return match.group(1).strip() if match else None

def find_tear_sheet_for_model(pdf_path):
    model = extract_account_model(pdf_path)

    if not model:
        print(f"no model found on {pdf_path}")
        return None

    slug = model.lower().replace(" ", "_")
    tear_sheet = TEAR_SHEETS_PATH / f"{slug}.pdf"

    if not tear_sheet.exists():
        print(f"no tear sheet found for model '{model}' (expected {tear_sheet})")
        return None

    return tear_sheet

def merge_pdfs(pdf_list, output_path):
    merged_pdf = pymupdf.open()

    for pdf_path in pdf_list:
        pdf_document = pymupdf.open(pdf_path)
        merged_pdf.insert_pdf(pdf_document)
        pdf_document.close()    

    # saved_path = merged_pdf.name

    merged_pdf.save(output_path)
    merged_pdf.close()

    return output_path

def int_to_rgb(color_int):
    r = ((color_int >> 16) & 0xFF) / 255
    g = ((color_int >> 8) & 0xFF) / 255
    b = (color_int & 0xFF) / 255
    return (r, g, b)


def replace_text_with_formatting(pdf_path, search_text, replace_text, font_file=None):
    doc = pymupdf.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")

        for block in blocks["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if search_text in span["text"]:

                            print(
                                span["text"],
                                span["font"],
                                span["size"],
                                span["color"],
                            )

                            size = span["size"]
                            color = int_to_rgb(span["color"])
                            bbox = span["bbox"]
                            origin = span["origin"]

                            # Some fonts (e.g. Avenir-Black here) declare an
                            # ascender/descender far taller than any glyph
                            # actually needs, so span["bbox"] can bleed into
                            # neighboring lines. Redact a generic type-body
                            # envelope around the baseline instead of the
                            # full font-metrics bbox.
                            ascent = size * 0.75
                            descent = size * 0.25
                            redact_rect = pymupdf.Rect(bbox[0], origin[1] - ascent, bbox[2], origin[1] + descent)

                            page.add_redact_annot(redact_rect)
                            page.apply_redactions()

                            if font_file:
                                fontname = Path(font_file).stem.replace(" ", "-")
                                page.insert_font(fontname=fontname, fontfile=font_file)
                            else:
                                fontname = span["font"]

                            page.insert_text(
                                origin,
                                replace_text,
                                fontname=fontname,
                                fontsize=size,
                                color=color
                            )

    doc.save(pdf_path, incremental=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
    doc.close()