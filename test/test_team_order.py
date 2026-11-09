"""
Checks that team pages keep the order of their names: two pages with the
same people in a different order stay separate, are found by that order,
and the team picker's dropdowns choose between them.

Usage:
    pymupdf-venv/bin/python3 test/test_team_order.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pymupdf
import src.advisors as advisors


def team_pdf(path, pages):
    """pages: a list of [(name, x, y), ...]. Each page gets the big title
    the real pages have, then the names in bold at the given positions
    (listed in whatever order -- that's the PDF's content order)."""
    doc = pymupdf.open()
    for names in pages:
        page = doc.new_page(width=792, height=612)
        page.insert_text((250, 80), "Your Rebalance Team", fontsize=36, fontname="hebo")
        for name, x, y in names:
            page.insert_text((x, y), name, fontsize=18, fontname="hebo")
    doc.save(str(path))
    doc.close()


DAN, CHRISTIE, MITCH, SALLY, SONJA = "Dan Mavraides", "Christie Whitney", "Mitch Tuchman", "Sally Brandon", "Sonja Breeding"

# Content order is deliberately not the visual order.
PAGES = [
    [(SALLY, 584, 354), (DAN, 83, 354), (CHRISTIE, 300, 354)],       # Dan, Christie, Sally
    [(DAN, 334, 354), (SALLY, 584, 354), (CHRISTIE, 51, 354)],       # Christie, Dan, Sally
    [(CHRISTIE, 300, 354), (MITCH, 85, 354), (SALLY, 584, 354)],     # Mitch, Christie, Sally
    [(SALLY, 566, 352), (CHRISTIE, 202, 158), (SONJA, 202, 344), (MITCH, 566, 166)],  # grid
]


class LibraryCase(unittest.TestCase):
    """Points the advisors module at a throwaway library."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "advisors").mkdir()
        self.saved = (advisors.ADVISORS_PATH, advisors.TEMPLATE_CONFIG_PATH)
        advisors.ADVISORS_PATH = root / "advisors"
        advisors.TEMPLATE_CONFIG_PATH = root / "template.json"
        self.source = root / "teams.pdf"
        team_pdf(self.source, PAGES)

    def tearDown(self):
        advisors.ADVISORS_PATH, advisors.TEMPLATE_CONFIG_PATH = self.saved
        self.tmp.cleanup()


class SplitTests(LibraryCase):
    def test_names_follow_the_layout_not_the_content_order(self):
        _, combos = advisors.split_advisors_pdf(self.source)
        self.assertIn([MITCH, CHRISTIE, SALLY], combos)

    def test_grid_page_reads_rows_then_columns(self):
        _, combos = advisors.split_advisors_pdf(self.source)
        self.assertIn([CHRISTIE, MITCH, SONJA, SALLY], combos)

    def test_same_people_in_two_orders_are_two_pages(self):
        _, combos = advisors.split_advisors_pdf(self.source)
        self.assertIn([DAN, CHRISTIE, SALLY], combos)
        self.assertIn([CHRISTIE, DAN, SALLY], combos)
        self.assertEqual(len(combos), len(PAGES))
        files = {p.name for p in advisors.ADVISORS_PATH.glob("*.pdf")}
        self.assertEqual(len(files), len(PAGES))

    def test_pages_are_sorted_by_who_is_listed_first(self):
        _, combos = advisors.split_advisors_pdf(self.source)
        trios = [combo for combo in combos if len(combo) == 3]
        self.assertEqual(trios, sorted(trios))
        self.assertEqual([combo[0] for combo in trios], [CHRISTIE, DAN, MITCH])


class LookupTests(LibraryCase):
    def setUp(self):
        super().setUp()
        names, combos = advisors.split_advisors_pdf(self.source)
        advisors._save_cached_advisors(str(self.source), names, combos)

    def page_names(self, path):
        doc = pymupdf.open(path)
        try:
            return advisors._names_on_page(doc[0])
        finally:
            doc.close()

    def test_each_order_finds_its_own_page(self):
        first = advisors.advisor_combo_file([DAN, CHRISTIE, SALLY])
        second = advisors.advisor_combo_file([CHRISTIE, DAN, SALLY])
        self.assertEqual(self.page_names(first), [DAN, CHRISTIE, SALLY])
        self.assertEqual(self.page_names(second), [CHRISTIE, DAN, SALLY])

    def test_blanks_and_repeats_are_ignored(self):
        path = advisors.advisor_combo_file(["", CHRISTIE, DAN, CHRISTIE, SALLY])
        self.assertEqual(self.page_names(path), [CHRISTIE, DAN, SALLY])

    def test_other_order_falls_back_to_the_same_people(self):
        path = advisors.advisor_combo_file([SALLY, MITCH, CHRISTIE])
        self.assertEqual(self.page_names(path), [MITCH, CHRISTIE, SALLY])

    def test_fallback_prefers_the_closest_order(self):
        # Neither page is Dan, Sally, Christie; Christie, Dan, Sally is one swap away.
        path = advisors.advisor_combo_file([DAN, SALLY, CHRISTIE])
        self.assertEqual(self.page_names(path), [DAN, CHRISTIE, SALLY])

    def test_no_page_for_these_people(self):
        self.assertIsNone(advisors.advisor_combo_file([DAN, MITCH]))
        self.assertIsNone(advisors.advisor_combo_file([]))


class OutdatedSplitTests(LibraryCase):
    def test_old_alphabetical_split_is_rebuilt_in_page_order(self):
        names, combos = advisors.split_advisors_pdf(self.source)
        advisors._save_cached_advisors(str(self.source), names, [sorted(c) for c in combos])
        with open(advisors.TEMPLATE_CONFIG_PATH) as f:
            config = json.load(f)
        del config["advisors_layout"]
        with open(advisors.TEMPLATE_CONFIG_PATH, "w") as f:
            json.dump(config, f)

        self.assertTrue(advisors.refresh_outdated_split())
        self.assertIn([DAN, CHRISTIE, SALLY], advisors.load_cached_advisor_combos())
        self.assertFalse(advisors.refresh_outdated_split())

    def test_missing_source_is_left_alone(self):
        names, combos = advisors.split_advisors_pdf(self.source)
        advisors._save_cached_advisors(str(self.source), names, combos)
        with open(advisors.TEMPLATE_CONFIG_PATH) as f:
            config = json.load(f)
        config["advisors_layout"] = 1
        with open(advisors.TEMPLATE_CONFIG_PATH, "w") as f:
            json.dump(config, f)
        self.source.unlink()
        self.assertFalse(advisors.refresh_outdated_split())


class TeamPickerTests(LibraryCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        super().setUp()
        from gui.widgets.team_picker import TeamPicker
        names, combos = advisors.split_advisors_pdf(self.source)
        advisors._save_cached_advisors(str(self.source), names, combos)
        advisors.save_advisor_roles({
            DAN: advisors.ROLE_ADVISOR, CHRISTIE: advisors.ROLE_ADVISOR,
            MITCH: advisors.ROLE_ADVISOR, SONJA: advisors.ROLE_ADVISOR,
            SALLY: advisors.ROLE_SERVICE,
        })
        self.picker = TeamPicker()
        self.picker.refresh(preserve_selection=False)

    def pick(self, combo, name):
        combo.setCurrentIndex(combo.findData(name))

    def set_roles(self, one, two, service):
        a1, a2, _, svc = self.picker.advisor_combos
        self.pick(a1, one)
        self.pick(a2, two)
        self.pick(svc, service)

    def test_both_orders_are_listed(self):
        entries = [self.picker.quick_select_combo.itemText(i) for i in range(1, self.picker.quick_select_combo.count())]
        self.assertIn(f"{DAN}, {CHRISTIE}, {SALLY}", entries)
        self.assertIn(f"{CHRISTIE}, {DAN}, {SALLY}", entries)

    def test_dropdown_order_picks_the_matching_page(self):
        self.set_roles(DAN, CHRISTIE, SALLY)
        self.assertEqual(self.picker.selected_advisors(), [DAN, CHRISTIE, SALLY])
        self.assertEqual(self.picker.quick_select_combo.currentText(), f"{DAN}, {CHRISTIE}, {SALLY}")

        self.set_roles(CHRISTIE, DAN, SALLY)
        self.assertEqual(self.picker.selected_advisors(), [CHRISTIE, DAN, SALLY])
        self.assertEqual(self.picker.quick_select_combo.currentText(), f"{CHRISTIE}, {DAN}, {SALLY}")
        self.assertFalse(self.picker.has_unmatched_combination())

    def test_team_page_fills_the_slots_in_its_order(self):
        combo = self.picker.quick_select_combo
        combo.setCurrentIndex(combo.findText(f"{CHRISTIE}, {DAN}, {SALLY}"))
        a1, a2, a3, svc = (c.currentData() for c in self.picker.advisor_combos)
        self.assertEqual((a1, a2, a3, svc), (CHRISTIE, DAN, "", SALLY))

    def test_unlisted_order_still_finds_a_page(self):
        # Slots can't put Sally between the advisors, so this is the
        # nearest listed order, not a placeholder.
        self.set_roles(MITCH, CHRISTIE, SALLY)
        self.assertEqual(self.picker.selected_advisors(), [MITCH, CHRISTIE, SALLY])
        self.assertFalse(self.picker.has_unmatched_combination())


if __name__ == "__main__":
    unittest.main()
