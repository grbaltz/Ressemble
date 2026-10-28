"""
Checks the Builder's "Report contents" rules against the assembler's own
section slots.

Usage:
    pymupdf-venv/bin/python3 test/test_report_contents.py
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gui.report_contents import describe_contents


def rows_by_key(**overrides):
    args = dict(
        client_name="Johnson",
        date_text="November 2, 2026",
        has_emx=True,
        has_bd=True,
        include_plan_360=True,
        team_names=["Dana Smith"],
    )
    args.update(overrides)
    return {row.key: row for row in describe_contents(**args)}


class DescribeContentsTests(unittest.TestCase):
    def test_everything_present(self):
        rows = rows_by_key()
        self.assertTrue(all(row.included for row in rows.values()))
        self.assertEqual(rows["plan360"].detail, "Title page and disclaimer")

    def test_missing_emx_drops_financial_plan_and_plan_360_title(self):
        rows = rows_by_key(has_emx=False)
        self.assertFalse(rows["emx"].included)
        # The disclaimer doesn't depend on EMX, so Plan 360 stays in.
        self.assertTrue(rows["plan360"].included)
        self.assertIn("Disclaimer only", rows["plan360"].detail)

    def test_missing_bd_drops_portfolio(self):
        rows = rows_by_key(has_bd=False)
        self.assertFalse(rows["portfolio"].included)
        self.assertTrue(rows["emx"].included)

    def test_plan_360_off_drops_it_even_with_emx(self):
        rows = rows_by_key(include_plan_360=False)
        self.assertFalse(rows["plan360"].included)
        self.assertTrue(rows["emx"].included)

    def test_plan_360_off_and_no_emx(self):
        rows = rows_by_key(include_plan_360=False, has_emx=False)
        self.assertFalse(rows["plan360"].included)
        self.assertFalse(rows["emx"].included)

    def test_no_sources_at_all(self):
        rows = rows_by_key(has_emx=False, has_bd=False)
        self.assertFalse(rows["emx"].included)
        self.assertFalse(rows["portfolio"].included)
        self.assertTrue(rows["cover"].included)

    def test_team_and_client_prompts(self):
        rows = rows_by_key(team_names=["", ""], client_name="  ")
        self.assertFalse(rows["team"].included)
        self.assertIn("Client name needed", rows["cover"].detail)

    def test_source_details_are_used_when_given(self):
        rows = rows_by_key(emx_detail="14 pages · Johnson.pdf", bd_detail="9 pages · BD.pdf")
        self.assertEqual(rows["emx"].detail, "14 pages · Johnson.pdf")
        self.assertEqual(rows["portfolio"].detail, "9 pages · BD.pdf")


class PreviewTests(unittest.TestCase):
    def test_single_page_emx_has_a_preview(self):
        rows = rows_by_key(emx_pdf="/x/emx.pdf", emx_pages=1)
        self.assertEqual(rows["emx"].preview.pdf_path, "/x/emx.pdf")

    def test_multi_page_emx_has_none(self):
        self.assertIsNone(rows_by_key(emx_pdf="/x/emx.pdf", emx_pages=3)["emx"].preview)

    def test_emx_with_unknown_page_count_has_none(self):
        self.assertIsNone(rows_by_key(emx_pdf="/x/emx.pdf", emx_pages=None)["emx"].preview)

    def test_plan_360_previews_only_the_lone_disclaimer(self):
        # With EMX the section is title + disclaimer, two pages: no preview.
        self.assertIsNone(rows_by_key(disclaimer_pdf="/x/d.pdf")["plan360"].preview)
        # Without EMX only the disclaimer is left.
        rows = rows_by_key(has_emx=False, disclaimer_pdf="/x/d.pdf")
        self.assertEqual(rows["plan360"].preview.pdf_path, "/x/d.pdf")
        # Turned off, nothing to show.
        self.assertIsNone(rows_by_key(has_emx=False, include_plan_360=False, disclaimer_pdf="/x/d.pdf")["plan360"].preview)

    def test_team_preview_needs_a_team(self):
        self.assertEqual(rows_by_key(team_pdf="/x/t.pdf")["team"].preview.pdf_path, "/x/t.pdf")
        self.assertIsNone(rows_by_key(team_names=[], team_pdf="/x/t.pdf")["team"].preview)

    def test_multi_page_sections_never_preview(self):
        rows = rows_by_key(emx_pdf="/x/e.pdf", emx_pages=2)
        self.assertIsNone(rows["cover"].preview)
        self.assertIsNone(rows["portfolio"].preview)


if __name__ == "__main__":
    unittest.main()
