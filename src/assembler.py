# import pandas as pd
from os import path
from pathlib import Path
from glob import glob
import shutil
import json
import re
import sys
import tempfile
import pymupdf
from datetime import date, timedelta
from src.paths import (
    PAGES_CONFIG_PATH,
    TEMPLATE_CONFIG_PATH,
    BASE_DATA_PATH,
    TEAR_SHEETS_PATH,
    EXPORT_PATH,
    FONTS_DIR,
)
from src.advisors import advisor_combo_file

AVENIR_BLACK_FONT_FILE = str(FONTS_DIR / "Avenir Black.ttf")

# Windows and macOS both ship the genuine, fully-glyphed Microsoft Times
# New Roman that a real Word/Office-produced report template was actually
# set in. The bundled copy (src/fonts/Times New Roman.ttf) is a
# metric-compatible substitute -- it exists so a system with no real Times
# New Roman (Linux, mainly) still has something to render the cover date
# with, but its letterforms don't actually match: verified by comparing a
# generated cover date against the same text in a real report side by
# side, same size/position -- the digits and comma are visibly different
# shapes despite both fonts reporting identical name/metrics. Preferring
# the genuine system font when it's present avoids that mismatch entirely.
_SYSTEM_TIMES_NEW_ROMAN_CANDIDATES = {
    "win32": [r"C:\Windows\Fonts\times.ttf"],
    "darwin": [
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/Library/Fonts/Times New Roman.ttf",
    ],
}.get(sys.platform, [])


def _resolve_times_new_roman():
    for candidate in _SYSTEM_TIMES_NEW_ROMAN_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return str(FONTS_DIR / "Times New Roman.ttf")


TIMES_NEW_ROMAN_FONT_FILE = _resolve_times_new_roman()

# Same reasoning as Times New Roman above -- prefer the genuine system
# Arial a real report's page numbers were actually set in, falling back to
# the bundled Arial-metric-compatible substitute only where no genuine
# copy exists.
_SYSTEM_ARIAL_CANDIDATES = {
    "win32": [r"C:\Windows\Fonts\arial.ttf"],
    "darwin": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ],
}.get(sys.platform, [])


def _resolve_arial():
    for candidate in _SYSTEM_ARIAL_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return str(FONTS_DIR / "LiberationSans-Regular.ttf")


MODEL_PATTERN = re.compile(r"Model:\s*(.+)")

# Which template slots belong to each optional section of the report.
# Neither source is required: a meeting with no financial plan update has
# no EMX file, one with no performance review has no Black Diamond file,
# and a report can be run without either.
#
# A section is more than its substitution placeholders -- it also owns the
# title/divider pages that announce it ("Plan 360" ahead of the EMX pages,
# the three "Portfolio & Allocation" pages ahead of the BD ones). Dropping
# the placeholder but keeping those would leave the report announcing a
# section that never arrives, so an absent source drops every slot listed
# here and the report reads as a complete one without it.
SECTION_SLOTS = {
    "emx": {"emx", "plan360Title"},
    "bd": {"bd", "portfolioAllAccounts", "portfolioIndividualAccount", "portfolioGeneric"},
}

# Page-number footer style verified against a real report (Arial, 8pt,
# solid black) -- rather than the muted-gray Times New Roman previously
# used here, which didn't match.
PAGE_NUMBER_FONT_FILE = _resolve_arial()
PAGE_NUMBER_COLOR = 0
PAGE_NUMBER_SIZE = 8
PAGE_NUMBER_MARGIN = 36

def assemble_report(log, progress, advisors_filename, client_name, enrolled, target_date=None, include_page_numbers=True, include_plan_360=True):
    print("assemble")

    # Set by whichever portfolio-title slot was just processed, consumed
    # by the very next "bd" placeholder -- see the case "bd" handler
    # below for why a raw incrementing slot counter isn't enough here.
    bd_pending_dir = None
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

    sources = template.get("sources") or {}
    emx_dir = sources.get("emx_dir")
    blackdiamond_dir = sources.get("blackdiamond_dir")

    # A source counts as present only if it actually split into pages --
    # a path recorded for a file that produced nothing would otherwise
    # leave the section's placeholders in the report with no content to
    # replace them.
    emx_pages = sorted_pdfs(emx_dir)
    has_emx = bool(emx_pages)
    has_bd = bool(blackdiamond_dir) and any(
        sorted_pdfs(Path(blackdiamond_dir) / f"bd{slot}") for slot in (1, 2)
    )

    omitted_slots = set()
    if not has_emx:
        log("No EMX pages provided -- omitting the EMX section.")
        omitted_slots |= SECTION_SLOTS["emx"]
    if not has_bd:
        log("No Black Diamond pages provided -- omitting the Black Diamond section.")
        omitted_slots |= SECTION_SLOTS["bd"]
    if not include_plan_360:
        # Independent of (and on top of) the EMX-driven omission above --
        # plan360Title is already dropped whenever there's no EMX source;
        # this drops it (and the Plan 360 disclaimer, which isn't tied to
        # EMX at all) even when EMX pages ARE present, per this checkbox.
        # The agenda's "Plan 360" bullet is a partial edit to a page kept
        # in the report either way, so it's handled in case "agenda"
        # below rather than here.
        log("Plan 360 excluded -- omitting its title and disclaimer pages.")
        omitted_slots |= {"plan360Title", "plan360Disclaimer"}

    # Number of accounts is however many pages ended up in bd2 -- the same
    # sorted, one-page-per-account set the tear-sheet model lookup reads.
    bd_account_count = len(sorted_pdfs(Path(blackdiamond_dir) / "bd2")) if has_bd else 0

    total_pages = len(template["pages"])

    for i, page in enumerate(template["pages"]):
        print(f"page: {page}")

        if progress:
            progress(i + 1, total_pages)

        # Every page of an omitted section goes -- its placeholders and
        # the title pages that label it alike.
        if page.get("slot") in omitted_slots:
            print(f"skipping {page['slot']} page (section omitted)")
            continue

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
            case "agenda":
                print("Agenda slot")

                if include_plan_360:
                    report_pages.append(page["filename"])
                else:
                    # Same working-copy pattern as the cover page above --
                    # the source split-page file stays untouched/reusable.
                    agenda_page = make_working_copy(page["filename"])
                    temp_files.append(agenda_page)
                    remove_agenda_plan360_line(agenda_page)
                    report_pages.append(agenda_page)
            case "portfolioAllAccounts" | "portfolioIndividualAccount":
                print(f"{page['slot']} slot")

                # These two only appear when there's more than one BD
                # account -- a single account uses the generic title page
                # instead (portfolioGeneric case below). Each pairs with
                # its own bd-folder (bd1 for the combined view, bd2 for
                # individual accounts) via bd_pending_dir -- see the
                # comment on case "bd" below for why that pairing has to
                # happen here rather than by position.
                if bd_account_count == 1:
                    print(f"skipping {page['slot']} title page (single account)")
                    bd_pending_dir = None
                else:
                    report_pages.append(page["filename"])
                    bd_folder = "bd1" if page["slot"] == "portfolioAllAccounts" else "bd2"
                    bd_pending_dir = Path(blackdiamond_dir) / bd_folder
            case "portfolioGeneric":
                print("portfolioGeneric slot")

                # The single-account alternative to portfolioIndividualAccount
                # above -- same bd2 pages, just introduced with wording that
                # doesn't imply multiple accounts.
                if bd_account_count == 1:
                    report_pages.append(page["filename"])
                    bd_pending_dir = Path(blackdiamond_dir) / "bd2"
                else:
                    print("skipping portfolioGeneric title page (multiple accounts)")
                    bd_pending_dir = None
            case "advisors":
                print("Advisors slot")

                # The user-provided advisors PDF (see src/advisors.py) is
                # split one page per pre-designed team combination, not one
                # page per person -- so only an exact combination match has
                # a real page to insert here.
                selected_advisors = template.get("selected_advisors") or []
                advisor_pdf = advisor_combo_file(selected_advisors)

                if not advisor_pdf:
                    print(f"no advisors page found for combination {selected_advisors}")
                    report_pages.append(page["filename"])
                    continue

                report_pages.append(str(advisor_pdf))
            case "emx":
                print("EMX slot")
                # The no-source case never reaches here -- the whole EMX
                # section is dropped up front when there's nothing to
                # substitute in (see omitted_slots).
                for p in emx_pages:
                    print(f"page {str(p)}")
                    report_pages.append(str(p))
            case "bd":
                print("Black Diamond slot")
                # As with EMX above, a missing source has already dropped
                # this page along with the rest of its section as a whole.
                #
                # Within the section, though, this placeholder isn't tied
                # to a fixed bd-folder number -- the template repeats it
                # once after portfolioAllAccounts, once after
                # portfolioIndividualAccount, and once after
                # portfolioGeneric (the latter two are the *same*
                # placeholder page, reused, since only one of that pair is
                # ever shown). Whichever of those title cases ran just
                # before this one decided whether it belongs in the
                # report at all, and which bd-folder it pairs with, via
                # bd_pending_dir -- so a skipped title's own placeholder
                # correctly contributes nothing here, instead of falling
                # back to inserting the wrong (or a nonexistent) folder.
                pages = bd_pending_dir
                bd_pending_dir = None

                if pages is None:
                    print("skipping bd placeholder (preceding title page was omitted)")
                    continue

                print(f"pages: {pages}")
                sorted_pages = sorted_pdfs(pages)

                if pages.name == "bd2":
                    # One tear sheet per distinct model, inserted right
                    # before that model's first account page here -- not
                    # one per account. Accounts are sorted by portfolio
                    # value (see get_bd_order() in scanner.py), not by
                    # model, so a repeat of the same model is rarely
                    # adjacent to its first occurrence; it still only
                    # gets a tear sheet that first time, however many
                    # accounts later the repeat turns up.
                    seen_models = set()
                    for p in sorted_pages:
                        model = extract_account_model(p)

                        if not model:
                            print(f"no model found on {p}")
                        elif model not in seen_models:
                            seen_models.add(model)
                            tear_sheet = find_tear_sheet_for_model(model)
                            if tear_sheet:
                                report_pages.append(str(tear_sheet))

                        print(f"page {str(p)}")
                        report_pages.append(str(p))
                else:
                    for p in sorted_pages:
                        print(f"page {str(p)}")
                        report_pages.append(str(p))
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

def sorted_pdfs(directory):
    """The PDFs directly in `directory`, in the page order their numeric
    filenames imply. Empty for a missing directory or a None path, so it
    doubles as the "is this source actually here?" test."""
    if not directory:
        return []

    directory = Path(directory)

    if not directory.is_dir():
        return []

    return sorted(directory.glob("*.pdf"), key=lambda x: numeric_key(x.name))

def numeric_key(filename):
    parts = re.split(r'(\d+)', filename)
    return [int(p) if p.isdigit() else p for p in parts]

def extract_account_model(pdf_path):
    doc = pymupdf.open(pdf_path)
    text = doc[0].get_text()
    doc.close()

    match = MODEL_PATTERN.search(text)
    return match.group(1).strip() if match else None

def find_tear_sheet_for_model(model):
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


def remove_agenda_plan360_line(pdf_path):
    """Removes the "» Plan 360" bullet from the Agenda page's list and
    shifts every bullet below it up to close the gap -- used when the
    "Include Plan 360" checkbox on Details is unchecked.

    The list is a vertical stack of (chevron, label) span pairs, each pair
    sharing a y-origin -- found by grouping spans into rows keyed on that
    origin, rather than hardcoding positions, so this still works if the
    agenda's wording/count of other bullets changes. The one assumption
    that IS hardcoded-by-omission: row-to-row spacing is uniform, which
    holds for this template's list -- the shift used to close the gap is
    measured off the row immediately below the removed one and applied to
    every row below that, rather than measured independently per row.
    """
    doc = pymupdf.open(pdf_path)
    page = doc[0]

    spans = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                spans.append(span)

    rows = []
    for span in spans:
        y = round(span["origin"][1], 1)
        if rows and rows[-1]["y"] == y:
            rows[-1]["spans"].append(span)
        else:
            rows.append({"y": y, "spans": [span]})

    # A bullet row is one with a "»" chevron in it -- distinguishes the
    # list from the "Agenda" heading itself, which has no chevron.
    bullet_rows = [r for r in rows if any(s["text"].strip() == "»" for s in r["spans"])]

    target_index = next(
        (
            i for i, r in enumerate(bullet_rows)
            if "plan 360" in "".join(s["text"] for s in r["spans"]).lower()
        ),
        None,
    )

    if target_index is None:
        print(f"no 'Plan 360' bullet found on {pdf_path} -- leaving agenda unchanged")
        doc.close()
        return

    target_row = bullet_rows[target_index]
    rows_below = bullet_rows[target_index + 1:]
    shift = (rows_below[0]["y"] - target_row["y"]) if rows_below else 0

    # insert_text() below needs each font actually registered on this page
    # under that name -- giving it just the name string the span already
    # reports (as replace_text_with_formatting() does when it's passed an
    # explicit font_file) isn't enough on its own, unless that name happens
    # to be a builtin base-14 font, which these custom template fonts
    # aren't. Pulling the font program directly out of the document (by
    # matching each span's reported name against the page's own font
    # list) means this doesn't depend on having a font *file* available --
    # unlike AVENIR_BLACK_FONT_FILE/TIMES_NEW_ROMAN_FONT_FILE elsewhere in
    # this module, there's no bundled copy of AGaramondPro to fall back on.
    fonts_needed = {span["font"] for row in rows_below for span in row["spans"]}
    font_buffers = {}
    for xref, ext, subtype, basefont, name, encoding, *_ in page.get_fonts(full=True):
        stripped = basefont.split("+")[-1]
        if stripped in fonts_needed and stripped not in font_buffers:
            _, _, _, buffer = doc.extract_font(xref)
            font_buffers[stripped] = buffer

    missing = fonts_needed - font_buffers.keys()
    if missing:
        print(f"couldn't find font(s) {missing} on {pdf_path} -- leaving agenda unchanged")
        doc.close()
        return

    for row in [target_row] + rows_below:
        for span in row["spans"]:
            size = span["size"]
            bbox = span["bbox"]
            origin = span["origin"]
            # Same generic type-body envelope as replace_text_with_formatting()
            # below -- a redact rect built from full font-metrics bbox can
            # bleed into the row above/below it (see that function's own
            # comment on this).
            ascent = size * 0.75
            descent = size * 0.25
            redact_rect = pymupdf.Rect(bbox[0], origin[1] - ascent, bbox[2], origin[1] + descent)
            page.add_redact_annot(redact_rect)

    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)

    for fontname, buffer in font_buffers.items():
        page.insert_font(fontname=fontname, fontbuffer=buffer)

    for row in rows_below:
        for span in row["spans"]:
            new_origin = (span["origin"][0], span["origin"][1] - shift)
            page.insert_text(
                new_origin,
                span["text"],
                fontname=span["font"],
                fontsize=span["size"],
                color=int_to_rgb(span["color"]),
            )

    doc.save(pdf_path, incremental=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
    doc.close()


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
                            # images=0 (PDF_REDACT_IMAGE_NONE): leave every
                            # image untouched, regardless of overlap -- we
                            # only ever intend to redact text here. The
                            # default instead blanks out overlapping image
                            # *pixels*, which requires MuPDF to decode/mask/
                            # re-encode the image and can end up blanking the
                            # whole thing (e.g. the cover page's background
                            # art near the household name/date text).
                            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)

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