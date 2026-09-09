"""
Splits a user-provided advisors PDF into individual per-team-combination
PDFs under ADVISORS_PATH, mirroring the pre-shipped combo files this app
used to ship with (see src/import/advisors_old for what that looked like)
-- this app isn't bundled with any advisor content of its own, so that
directory now gets (re)built from whatever the user provides instead.

Each page of the source PDF is one specific pre-designed team combination
(e.g. a page showing "Mitch Tuchman" and "Sally Brandon" together) rather
than one page per individual advisor -- confirmed against the actual file
this was built against (src/import/Team Pages_04_2026.pdf): every page
carries 2-5 names, never exactly one. So the split keeps each page whole
and names it after everyone who appears on it (alphabetically, matching
the old combo files' naming), rather than trying to carve individual
people out of a shared page.
"""
import json
import re
import pymupdf
from src.paths import ADVISORS_PATH, TEMPLATE_CONFIG_PATH

# Name detection doesn't pin to one specific font/size -- a later revision
# of the source file (src/import/Team Pages 08 2026 v2.pdf) switched fonts
# entirely (Avenir-Black -> Anth-Bold) while keeping the same relative
# layout, which broke a prior version of this that matched one exact
# font+size. Instead: within each page's *bold* text, group by size --
# the page's own title (e.g. "Your Rebalance Team", repeated on every
# page regardless of who's shown) is reliably the single largest bold
# size, and a person's name renders one tier down from that, whatever
# that size happens to be in this particular file's styling. Confirmed
# against both the v1 and v2 files: bold size tiers are
# {36: title, 18: names, 14: bold job titles} and {36: title, 18: names}
# respectively -- "one tier below the largest" lands on 18 either way,
# where a naive "everything but the largest" would also sweep in v1's
# bold job-title line. A name-shape check on top guards against picking
# up something else entirely in a future layout.
_NAME_SHAPE = re.compile(r"^[A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){1,3}$")

# A name can render as a second line break onto its own text run (e.g. a
# credential suffix like "CFP, CCFC" wrapping), which would otherwise be
# picked up as a bogus nameless entry (just ", CCFC"). Only the part
# before the first comma is the actual name; discard anything left blank
# by that split.
_ZERO_WIDTH_SPACE = "​"


def slugify_advisor_name(name):
    return re.sub(r"\s+", "", name.strip().lower())


def _clean_name(raw_text):
    text = raw_text.replace(_ZERO_WIDTH_SPACE, "").strip()
    name = text.split(",")[0].strip()
    return name or None


def _bold_text_by_size(page):
    """{rounded font size -> [bold text on the page at that size]}."""
    sizes = {}
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                if not text or not (span["flags"] & pymupdf.TEXT_FONT_BOLD):
                    continue
                sizes.setdefault(round(span["size"], 1), []).append(text)
    return sizes


def _names_on_page(page):
    by_size = _bold_text_by_size(page)
    if not by_size:
        return []

    sizes = sorted(by_size, reverse=True)
    # Falls back to the only size present if there's just one tier (e.g. a
    # page with a single bold run) -- better to try it than find nothing.
    name_size = sizes[1] if len(sizes) > 1 else sizes[0]

    names = []
    for text in by_size[name_size]:
        name = _clean_name(text)
        if name and _NAME_SHAPE.match(name):
            names.append(name)
    return names


def split_advisors_pdf(pdf_path):
    """Splits pdf_path into one PDF per page under ADVISORS_PATH, replacing
    whatever was there before -- it always reflects only the most recently
    provided advisors file. Each page is saved whole, named after every
    advisor who appears on it (alphabetically, underscore-joined, matching
    the naming assemble_report() looks combo files up by). Returns the
    sorted list of unique advisor names found across the whole file."""
    doc = pymupdf.open(pdf_path)

    for existing in ADVISORS_PATH.glob("*.pdf"):
        existing.unlink()

    unique_names = set()
    for page_num in range(len(doc)):
        names = sorted(set(_names_on_page(doc[page_num])))
        if not names:
            continue

        unique_names.update(names)

        combo_page = pymupdf.open()
        combo_page.insert_pdf(doc, from_page=page_num, to_page=page_num)
        slug = "_".join(slugify_advisor_name(name) for name in names)
        combo_page.save(str(ADVISORS_PATH / f"{slug}.pdf"))
        combo_page.close()

    doc.close()
    return sorted(unique_names)


def load_cached_advisors():
    """Returns (source_path, names) from the last successful split, or
    (None, []) if none has ever run."""
    try:
        with open(TEMPLATE_CONFIG_PATH) as f:
            template = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None, []
    return template.get("advisors_source"), template.get("advisor_names", [])


def _save_cached_advisors(source_path, names):
    try:
        with open(TEMPLATE_CONFIG_PATH) as f:
            template = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        template = {}

    template["advisors_source"] = source_path
    template["advisor_names"] = names

    with open(TEMPLATE_CONFIG_PATH, "w") as f:
        json.dump(template, f)


def ensure_advisors_split(pdf_path):
    """Splits pdf_path into ADVISORS_PATH unless it's the same file that
    was split last time (a plain path comparison, same as the main report
    template's own new-vs-unchanged check) -- returns the resulting list
    of advisor names either way."""
    pdf_path = str(pdf_path)
    cached_source, cached_names = load_cached_advisors()
    if cached_source == pdf_path and cached_names:
        return cached_names

    names = split_advisors_pdf(pdf_path)
    _save_cached_advisors(pdf_path, names)
    return names


def advisor_combo_file(selected_names):
    """The combo file matching an exact set of selected advisor names, or
    None if this particular combination wasn't one of the pages in the
    provided advisors PDF -- picking an arbitrary subset of the roster
    isn't guaranteed to have a matching pre-designed page."""
    if not selected_names:
        return None

    slug = "_".join(slugify_advisor_name(name) for name in sorted(selected_names))
    combo_pdf = ADVISORS_PATH / f"{slug}.pdf"
    return combo_pdf if combo_pdf.exists() else None
