"""
Checks how the cover's household name is laid out: one line when it fits,
wrapped (balanced) when it doesn't, smaller only as a last resort.

Usage:
    pymupdf-venv/bin/python3 test/test_cover_name.py
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pymupdf
from src.assembler import (
    layout_cover_name,
    AVENIR_BLACK_FONT_FILE,
    COVER_NAME_MAX_LINES,
    COVER_NAME_MIN_SIZE,
)

FONT = pymupdf.Font(fontfile=AVENIR_BLACK_FONT_FILE)
SIZE = 47.3
WIDTH = 792 - 2 * 36


def measure_at_size(size):
    return lambda text: FONT.text_length(text, fontsize=size)


def layout(name):
    return layout_cover_name(f"The {name} Household", measure_at_size, SIZE, WIDTH)


class CoverNameTests(unittest.TestCase):
    def test_short_name_stays_on_one_line_at_full_size(self):
        lines, size = layout("Johnson")
        self.assertEqual(lines, ["The Johnson Household"])
        self.assertEqual(size, SIZE)

    def test_long_name_wraps_at_full_size(self):
        lines, size = layout("Fitzgerald-Montgomery")
        self.assertEqual(len(lines), 2)
        self.assertEqual(size, SIZE)
        self.assertTrue(all(FONT.text_length(line, fontsize=size) <= WIDTH for line in lines))

    def test_wrapped_lines_are_balanced_not_a_lone_word(self):
        lines, _ = layout("Rosenbaum and Delacroix-Whitmore")
        self.assertNotEqual(lines[-1], "Household")

    def test_never_more_than_the_maximum_lines(self):
        lines, _ = layout("Rosenbaum-Vanderbilt and Delacroix-Whitmore and Montgomery-Fitzgerald")
        self.assertLessEqual(len(lines), COVER_NAME_MAX_LINES)

    def test_shrinks_only_when_wrapping_is_not_enough(self):
        lines, size = layout("Rosenbaum-Vanderbilt and Delacroix-Whitmore and Montgomery-Fitzgerald")
        self.assertLess(size, SIZE)
        self.assertGreaterEqual(size, COVER_NAME_MIN_SIZE)

    def test_one_unbreakable_word_shrinks_but_stays_legible(self):
        lines, size = layout("Wolfeschlegelsteinhausenbergerdorff")
        self.assertGreaterEqual(size, COVER_NAME_MIN_SIZE)

    def test_single_line_mode_never_wraps(self):
        lines, size = layout_cover_name("The Fitzgerald-Montgomery Household", measure_at_size, SIZE, WIDTH, max_lines=1)
        self.assertEqual(len(lines), 1)
        self.assertLess(size, SIZE)


if __name__ == "__main__":
    unittest.main()
