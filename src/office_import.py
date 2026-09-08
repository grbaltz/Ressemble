"""
Handles non-PDF EMX sources: converts a .doc/.docx file to PDF via a
headless LibreOffice, then removes bold styling throughout the document
(EMX reports often arrive bolded and need to match the rest of the
report). The rest of the app only ever works with PDFs -- this is the one
place a Word document enters the pipeline, and it leaves as a PDF.
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import pymupdf
from src.paths import FONTS_DIR

OFFICE_EXTENSIONS = {".doc", ".docx"}

# LibreOffice's CLI binary name differs by platform, and on Windows it's
# often not on PATH even when installed -- check the usual install
# locations too before giving up.
_SOFFICE_CANDIDATES = {
    "win32": [
        "soffice.exe",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ],
    "darwin": [
        "soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ],
}.get(sys.platform, ["soffice"])

# Used whenever a page's bold text has no font family that can otherwise
# be resolved to a real regular-weight font on this system -- bundled with
# the app (see packaging/ressemble.spec) rather than pointed at some
# assumed OS install path, since none of those are reliable: e.g. macOS
# only *activates* some of its bundled fonts (Arial included) on demand --
# the .ttf may not exist on disk as a plain file until something actually
# requests it through CoreText, which we don't. Metric-compatible with
# Arial, so substituted text still lines up the same as the original.
FALLBACK_REGULAR_FONT_FILE = str(FONTS_DIR / "LiberationSans-Regular.ttf")

# fc-match (used below) needs fontconfig, which Linux distros ship with but
# macOS doesn't -- this is the "platform equivalent" for macOS: a plain
# filename search over the directories macOS actually keeps real font
# files in, matching by normalized family name instead of shelling out to
# a tool that's very unlikely to be installed.
_MACOS_FONT_DIRS = [
    Path("/System/Library/Fonts/Supplemental"),
    Path("/Library/Fonts"),
    Path.home() / "Library" / "Fonts",
    Path("/System/Library/Fonts"),
]


def _normalize_font_name(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _find_macos_family_file(family):
    target = _normalize_font_name(family)
    best = None
    for directory in _MACOS_FONT_DIRS:
        if not directory.is_dir():
            continue
        for font_file in directory.glob("*"):
            if font_file.suffix.lower() not in (".ttf", ".otf"):
                continue
            stem = _normalize_font_name(font_file.stem)
            if stem in (target, target + "regular"):
                return str(font_file)
            if best is None and stem.startswith(target) and not any(
                weight in stem for weight in ("bold", "italic", "oblique")
            ):
                best = str(font_file)
    return best


def _find_soffice():
    for candidate in _SOFFICE_CANDIDATES:
        if shutil.which(candidate):
            return candidate
        if Path(candidate).is_file():
            return candidate
    return None


def is_office_document(path):
    return Path(path).suffix.lower() in OFFICE_EXTENSIONS


def convert_to_pdf(source_path, out_dir=None):
    source_path = Path(source_path)
    out_dir = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="office_convert_"))
    out_dir.mkdir(parents=True, exist_ok=True)

    soffice = _find_soffice()
    if not soffice:
        raise RuntimeError(
            "LibreOffice (soffice) is required to import a .doc/.docx EMX file but "
            "wasn't found. Install LibreOffice, or provide the EMX source as a PDF instead."
        )

    result = subprocess.run(
        [
            soffice, "--headless", "--norestore",
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
    # Resolving against a real, fully-glyphed system font file (rather than
    # the fonts embedded in the PDF itself, which LibreOffice subsets down
    # to only the glyphs each specific run actually used) matters because
    # we're inserting new text through it -- text the subsetted embedded
    # font is very likely missing glyphs for.
    if sys.platform == "darwin":
        found = _find_macos_family_file(family)
        if found:
            return found

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


def debold_document(pdf_path):
    """Rewrites every bold text run across every page of pdf_path as
    non-bold, in place. Returns True if any bold text had to fall back to
    the generic substitute font (its family couldn't be resolved to a real
    regular-weight font on the system)."""
    doc = pymupdf.open(pdf_path)

    resolved_fonts = {}  # family key -> font file path

    def font_file_for(family):
        if family not in resolved_fonts:
            resolved_fonts[family] = _resolve_regular_font_file(family)
        return resolved_fonts[family]

    used_fallback = False

    for page in doc:
        spans = [
            span
            for block in page.get_text("dict")["blocks"] if "lines" in block
            for line in block["lines"]
            for span in line["spans"]
            if span["flags"] & pymupdf.TEXT_FONT_BOLD and span["text"].strip()
        ]

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
            # images=0 (PDF_REDACT_IMAGE_NONE): leave every image untouched,
            # regardless of overlap. We only ever intend to redact text --
            # the default (blank out overlapping image *pixels*) requires
            # MuPDF to decode/mask/re-encode any image the rect touches,
            # which on some pages was blanking the whole image instead of
            # just the intersecting sliver (e.g. a bold chart title or
            # label sitting right next to/on a chart image).
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)

            page.insert_font(fontname=fontname, fontfile=font_file)
            page.insert_text(origin, span["text"], fontname=fontname, fontsize=size, color=color)

    doc.save(pdf_path, incremental=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
    doc.close()

    return used_fallback


def prepare_emx_source(source_path):
    """Given whatever the user picked as the EMX source, return a plain
    PDF path ready for the rest of the pipeline. .doc/.docx sources are
    converted and fully debolded; a .pdf source is returned as-is."""
    if not is_office_document(source_path):
        return source_path

    pdf_path = convert_to_pdf(source_path)
    debold_document(pdf_path)
    return pdf_path
