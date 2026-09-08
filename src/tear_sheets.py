"""
Splits a single user-provided tear sheets PDF into individual per-model
PDFs under TEAR_SHEETS_PATH -- this app isn't shipped with any tear sheet
content of its own, so that directory now gets (re)built from whatever
the user provides, the same way src/advisors.py rebuilds ADVISORS_PATH
from a user-provided advisors PDF.

find_tear_sheet_for_model() in src/assembler.py looks a tear sheet up by
the exact model name found on a Black Diamond account page, slugified the
same way here -- so each page here needs to end up named to match. Most
tear sheet pages are titled "<Name> Portfolio" (-> slug "<name>"); the six
laddered-income variants are titled across two separate text runs
("Laddered Income" + "N-Year Corporate"/"N-Year Treasury" -> slug
"laddered_income_Ny_corporate"/"..._treasury"); anything else (a shared
reference/comparison page with no single model of its own) falls back to
its page number, matching how the original pre-shipped set handled the
same kind of page.
"""
import json
import re
import pymupdf
from src.paths import TEAR_SHEETS_PATH, TEMPLATE_CONFIG_PATH

_PORTFOLIO_TITLE = re.compile(r"^(.+?)\s+Portfolio$")
_LADDERED_YEAR_TYPE = re.compile(r"^(\d+)-Year (Corporate|Treasury)$")


def _slug_for_page(page, page_num):
    text = page.get_text().strip()
    first_line = text.split("\n")[0].strip() if text else ""

    match = _PORTFOLIO_TITLE.match(first_line)
    if match:
        return match.group(1).strip().lower().replace(" ", "_")

    is_laddered = False
    year_type = None
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                span_text = span["text"].strip()
                if span_text == "Laddered Income":
                    is_laddered = True
                year_match = _LADDERED_YEAR_TYPE.match(span_text)
                if year_match:
                    year_type = year_match.groups()

    if is_laddered and year_type:
        years, kind = year_type
        return f"laddered_income_{years}y_{kind.lower()}"

    # No recognizable per-model title -- a shared reference/comparison
    # page rather than one specific tear sheet. Named by page number so
    # it's still preserved, just not looked up by any model.
    return str(page_num)


def split_tear_sheets_pdf(pdf_path):
    """Splits pdf_path into one PDF per page under TEAR_SHEETS_PATH,
    replacing whatever was there before -- it always reflects only the
    most recently provided tear sheets file. Returns the list of model
    slugs actually identified (excludes pages that fell back to a bare
    page number, since those aren't looked up by any model)."""
    doc = pymupdf.open(pdf_path)

    for existing in TEAR_SHEETS_PATH.glob("*.pdf"):
        existing.unlink()

    identified = []
    for page_num in range(len(doc)):
        slug = _slug_for_page(doc[page_num], page_num)

        single_page = pymupdf.open()
        single_page.insert_pdf(doc, from_page=page_num, to_page=page_num)
        single_page.save(str(TEAR_SHEETS_PATH / f"{slug}.pdf"))
        single_page.close()

        if not slug.isdigit():
            identified.append(slug)

    doc.close()
    return identified


def load_cached_tear_sheets():
    """Returns (source_path, slugs) from the last successful split, or
    (None, []) if none has ever run."""
    try:
        with open(TEMPLATE_CONFIG_PATH) as f:
            template = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None, []
    return template.get("tear_sheets_source"), template.get("tear_sheet_models", [])


def _save_cached_tear_sheets(source_path, slugs):
    try:
        with open(TEMPLATE_CONFIG_PATH) as f:
            template = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        template = {}

    template["tear_sheets_source"] = source_path
    template["tear_sheet_models"] = slugs

    with open(TEMPLATE_CONFIG_PATH, "w") as f:
        json.dump(template, f)


def ensure_tear_sheets_split(pdf_path):
    """Splits pdf_path into TEAR_SHEETS_PATH unless it's the same file
    that was split last time (a plain path comparison, same as the main
    report template's own new-vs-unchanged check) -- returns the
    resulting list of identified model slugs either way."""
    pdf_path = str(pdf_path)
    cached_source, cached_slugs = load_cached_tear_sheets()
    if cached_source == pdf_path and cached_slugs:
        return cached_slugs

    slugs = split_tear_sheets_pdf(pdf_path)
    _save_cached_tear_sheets(pdf_path, slugs)
    return slugs
