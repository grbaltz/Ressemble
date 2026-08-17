"""
Prep step equivalent to the GUI's Scan screen, run without Qt: splits the
EMX and Black Diamond source PDFs referenced in template.json into
per-page/per-account files under src/import/split_pages/, so
generate_report.py has real data to assemble against. Only needs to be run
once per set of source PDFs -- re-run after replacing them in template.json.

Usage:
    pymupdf-venv/bin/python3 test/prepare_sources.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.scanner import get_emx_order, get_bd_order


def main():
    print("Splitting EMX pages...")
    get_emx_order()

    print("Splitting Black Diamond pages...")
    get_bd_order()


if __name__ == "__main__":
    main()
