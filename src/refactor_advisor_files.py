"""
Scan every PDF in a directory and report which names (from a known candidate
list) appear in each document.

Usage:
    python scan_names_in_pdfs.py /path/to/pdf_directory
"""
from pathlib import Path

import pymupdf

# Candidate names to search for. Add/remove as needed.
CANDIDATE_NAMES = [
    "Christie Whitney",
    "Dan Mavraides",
    "Kameron Javier",
    "Matt Jude",
    "Mitch Tuchman",
    "Sally Brandon",
    "Scott Puritz",
    "Sonja Breeding",
]


def get_pdf_text(pdf_path: Path) -> str:
    """Extract and concatenate all text from a PDF."""
    doc = pymupdf.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def find_names_in_text(text: str, candidate_names: list[str]) -> list[str]:
    """Return the subset of candidate_names found in text (case-insensitive)."""
    text_lower = text.lower()
    return [name for name in candidate_names if name.lower() in text_lower]


def scan_directory(directory: Path, candidate_names: list[str]) -> dict[str, list[str]]:
    """Scan all PDFs in a directory and return {filename: [found names]}."""
    results = {}
    for pdf_path in sorted(directory.glob("*.pdf")):
        text = get_pdf_text(pdf_path)
        found = find_names_in_text(text, candidate_names)
        results[pdf_path.name] = found
    return results


def main():
    if len(sys.argv) != 2:
        print("Usage: python scan_names_in_pdfs.py /path/to/pdf_directory")
        sys.exit(1)

    directory = Path(sys.argv[1])
    if not directory.is_dir():
        print(f"Error: {directory} is not a valid directory")
        sys.exit(1)

    results = scan_directory(directory, CANDIDATE_NAMES)
    print(f"Results: {results}")

    for filename, names in results.items():
        print(names)
        names_str = "_".join(names).lower().replace(" ", "") if names else "(no matches)"
        print(f"{filename}: {names_str}")
        f = Path(directory / filename)
        f.rename(directory / names_str)

if __name__ == "__main__":
    main()