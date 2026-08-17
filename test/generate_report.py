"""
Runs assemble_report() directly, without the GUI -- the same call the
Assemble screen's worker thread makes, for quickly generating a report to
inspect. Run test/prepare_sources.py first if src/import/split_pages/ isn't
populated yet (EMX/BD pages need to be split before a report can include
them).

Usage:
    pymupdf-venv/bin/python3 test/generate_report.py
    pymupdf-venv/bin/python3 test/generate_report.py --client-name Smith --enrolled
"""
import argparse
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.assembler import assemble_report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--client-name", default="Fullan", help="Household name for the cover page (default: Fullan)")
    parser.add_argument("--enrolled", action="store_true", help="Use the View360 'enrolled' page instead of the enrollment pitch page")
    parser.add_argument("--target-date", default=None, help="YYYY-MM-DD to print on the cover instead of next Monday")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.target_date) if args.target_date else None

    report_path = assemble_report(
        log=print,
        progress=lambda current, total: None,
        advisors_filename=None,
        client_name=args.client_name,
        enrolled=args.enrolled,
        target_date=target_date,
    )

    print(f"\nReport generated: {report_path}")


if __name__ == "__main__":
    main()
