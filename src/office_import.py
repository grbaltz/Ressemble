"""
Handles non-PDF EMX sources: converts a .doc/.docx file to PDF via a
headless LibreOffice, then removes bold styling from its first page (the
EMX cover sheet often arrives bolded and needs to match the rest of the
report). The rest of the app only ever works with PDFs -- this is the one
place a Word document enters the pipeline, and it leaves as a PDF.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import pymupdf

OFFICE_EXTENSIONS = {".doc", ".docx"}

# Metric-compatible with Arial/Helvetica and present on essentially every
# Linux desktop -- used only when a page's bold text has no embedded
# regular-weight sibling to fall back on.
FALLBACK_REGULAR_FONT_FILE = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def is_office_document(path):
    return Path(path).suffix.lower() in OFFICE_EXTENSIONS


def convert_to_pdf(source_path, out_dir=None):
    source_path = Path(source_path)
    out_dir = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="office_convert_"))
    out_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            "soffice", "--headless", "--norestore",
            "--convert-to", "pdf", "--outdir", str(out_dir), str(source_path),
        ],
        capture_output=True, text=True, timeout=120,
    )

    converted = out_dir / f"{source_path.stem}.pdf"
    if result.returncode != 0 or not converted.exists():
        raise RuntimeError(
            f"LibreOffice conversion failed for {source_path}: {result.stderr.strip() or result.stdout.strip()}"
        )
    return str(converted)


def _font_family_key(basefont):
    # Strip a subset prefix (e.g. "BAAAAA+") and any trailing weight/style
    # tags so "BAAAAA+NotoSans-Bold" and "NotoSans-Regular" compare equal.
    name = re.sub(r"^[A-Z]{6}\+", "", basefont)
    while True:
        stripped = re.sub(r"[-, ]?(Bold|Italic|Oblique|Regular|MT|PS)$", "", name, flags=re.IGNORECASE)
        if stripped == name:
            break
        name = stripped
    return name.lower()


def _int_to_rgb(color_int):
    r = ((color_int >> 16) & 0xFF) / 255
    g = ((color_int >> 8) & 0xFF) / 255
    b = (color_int & 0xFF) / 255
    return (r, g, b)


def _resolve_regular_font_file(family):
    # fc-match resolves against real, fully-glyphed system font files --
    # unlike the fonts embedded in the PDF itself, which LibreOffice
    # subsets down to only the glyphs each specific run actually used
    # (fine for the original text, but missing glyphs for whatever new
    # text we'd reinsert through them).
    try:
        result = subprocess.run(
            ["fc-match", "--format=%{file}", f"{family}:style=Regular"],
            capture_output=True, text=True, timeout=10,
        )
        path = result.stdout.strip()
        if result.returncode == 0 and path and Path(path).is_file():
            return path
    except (subprocess.SubprocessError, OSError):
        pass
    return FALLBACK_REGULAR_FONT_FILE


def debold_first_page(pdf_path):
    """Rewrites every bold text run on page 1 of pdf_path as non-bold,
    in place. Other pages are untouched. Returns True if any bold text
    had to fall back to the generic substitute font (its family couldn't
    be resolved to a real regular-weight font on the system)."""
    doc = pymupdf.open(pdf_path)
    page = doc[0]

    resolved_fonts = {}  # family key -> font file path

    def font_file_for(family):
        if family not in resolved_fonts:
            resolved_fonts[family] = _resolve_regular_font_file(family)
        return resolved_fonts[family]

    spans = [
        span
        for block in page.get_text("dict")["blocks"] if "lines" in block
        for line in block["lines"]
        for span in line["spans"]
        if span["flags"] & pymupdf.TEXT_FONT_BOLD and span["text"].strip()
    ]

    used_fallback = False

    for span in spans:
        size = span["size"]
        color = _int_to_rgb(span["color"])
        origin = span["origin"]
        bbox = span["bbox"]

        family = _font_family_key(span["font"])
        font_file = font_file_for(family)
        fontname = f"debold-{family}"[:63]
        if font_file == FALLBACK_REGULAR_FONT_FILE:
            used_fallback = True

        # Same tight, baseline-relative redaction envelope used for the
        # cover-page substitutions -- the raw span bbox is font-metric
        # based and can bleed into neighboring lines.
        ascent = size * 0.75
        descent = size * 0.25
        redact_rect = pymupdf.Rect(bbox[0], origin[1] - ascent, bbox[2], origin[1] + descent)

        page.add_redact_annot(redact_rect)
        page.apply_redactions()

        page.insert_font(fontname=fontname, fontfile=font_file)
        page.insert_text(origin, span["text"], fontname=fontname, fontsize=size, color=color)

    doc.save(pdf_path, incremental=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
    doc.close()

    return used_fallback


def prepare_emx_source(source_path):
    """Given whatever the user picked as the EMX source, return a plain
    PDF path ready for the rest of the pipeline. .doc/.docx sources are
    converted and debolded on page 1; a .pdf source is returned as-is."""
    if not is_office_document(source_path):
        return source_path

    pdf_path = convert_to_pdf(source_path)
    debold_first_page(pdf_path)
    return pdf_path
