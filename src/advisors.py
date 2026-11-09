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
and names it after everyone who appears on it, rather than trying to carve
individual people out of a shared page.

The order of the names matters: the file can hold "Dan, Christie, Sally"
and "Christie, Dan, Sally" as two different pages. Names are therefore kept
in the order they're laid out on the page (left to right, top to bottom --
the PDF's own content order isn't reliable for that) and the combo file
name follows the same order.
"""
import json
import re
from pathlib import Path
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


# Bumped whenever how pages are split or named changes, so a library split
# by an older version gets rebuilt (see refresh_outdated_split()).
SPLIT_LAYOUT_VERSION = 2

# Names whose tops are within this many points of each other sit on the same
# visual row (the real pages' rows are ~180 apart; names on one row differ by
# a few points at most).
_SAME_ROW_TOLERANCE = 30


def _bold_spans_by_size(page):
    """{rounded font size -> [(bold text, x, y) on the page at that size]}."""
    sizes = {}
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                if not text or not (span["flags"] & pymupdf.TEXT_FONT_BOLD):
                    continue
                x0, y0 = span["bbox"][:2]
                sizes.setdefault(round(span["size"], 1), []).append((text, x0, y0))
    return sizes


def _reading_order(items):
    """items are (value, x, y); returns the values top row first, each row
    left to right -- the way a person reads the page."""
    rows = []
    for item in sorted(items, key=lambda item: item[2]):
        if rows and item[2] - rows[-1][0][2] <= _SAME_ROW_TOLERANCE:
            rows[-1].append(item)
        else:
            rows.append([item])
    return [item[0] for row in rows for item in sorted(row, key=lambda item: item[1])]


def _names_on_page(page):
    """The people shown on the page, in the order they're laid out on it."""
    by_size = _bold_spans_by_size(page)
    if not by_size:
        return []

    sizes = sorted(by_size, reverse=True)
    # Falls back to the only size present if there's just one tier (e.g. a
    # page with a single bold run) -- better to try it than find nothing.
    name_size = sizes[1] if len(sizes) > 1 else sizes[0]

    found = []
    for text, x, y in by_size[name_size]:
        name = _clean_name(text)
        if name and _NAME_SHAPE.match(name):
            found.append((name, x, y))
    return list(dict.fromkeys(_reading_order(found)))


def _sorted_combos(combos):
    """Smallest teams first, then by who's listed first (then second, ...),
    so the same lead's pages sit together."""
    return sorted(combos, key=lambda names: (len(names), names))


def split_advisors_pdf(pdf_path):
    """Splits pdf_path into one PDF per page under ADVISORS_PATH, replacing
    whatever was there before -- it always reflects only the most recently
    provided advisors file. Each page is saved whole, named after every
    advisor who appears on it (in the order they appear on the page,
    underscore-joined, matching the naming advisor_combo_file() looks combo
    files up by). Returns (sorted unique advisor names, per-page combos) --
    the combos are each page's own name list, in the same order/casing they
    appeared on the page, for the team picker's "Team page" list (see
    load_cached_advisor_combos()): reusing those exact per-page lists here
    means that list can never drift from what actually has a real page,
    the way reconstructing names from the combo filenames' slugs could if
    a name were ever ambiguous once slugified.
    """
    doc = pymupdf.open(pdf_path)

    for existing in ADVISORS_PATH.glob("*.pdf"):
        existing.unlink()

    unique_names = set()
    seen_combos = set()
    combos = []
    for page_num in range(len(doc)):
        names = _names_on_page(doc[page_num])
        if not names:
            continue

        unique_names.update(names)

        combo_key = tuple(names)
        if combo_key not in seen_combos:
            seen_combos.add(combo_key)
            combos.append(names)

        combo_page = pymupdf.open()
        combo_page.insert_pdf(doc, from_page=page_num, to_page=page_num)
        slug = "_".join(slugify_advisor_name(name) for name in names)
        combo_page.save(str(ADVISORS_PATH / f"{slug}.pdf"))
        combo_page.close()

    doc.close()
    return sorted(unique_names), _sorted_combos(combos)


def load_cached_advisors():
    """Returns (source_path, names) from the last successful split, or
    (None, []) if none has ever run."""
    try:
        with open(TEMPLATE_CONFIG_PATH) as f:
            template = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None, []
    return template.get("advisors_source"), template.get("advisor_names", [])


def load_cached_advisor_combos():
    """Returns the per-page name lists from the last successful split (one
    per real team page, see split_advisors_pdf()), or [] if none has ever
    run. Used to populate the Sources & Advisors screen's "quick select"
    list -- every entry here is guaranteed to have a matching combo file,
    since they came from the same split that created those files."""
    try:
        with open(TEMPLATE_CONFIG_PATH) as f:
            template = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return _sorted_combos(template.get("advisor_combos", []))


def _cached_split_layout():
    try:
        with open(TEMPLATE_CONFIG_PATH) as f:
            return json.load(f).get("advisors_layout", 1)
    except (FileNotFoundError, json.JSONDecodeError):
        return 1


def _save_cached_advisors(source_path, names, combos):
    try:
        with open(TEMPLATE_CONFIG_PATH) as f:
            template = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        template = {}

    template["advisors_source"] = source_path
    template["advisor_names"] = names
    template["advisor_combos"] = combos
    template["advisors_layout"] = SPLIT_LAYOUT_VERSION

    with open(TEMPLATE_CONFIG_PATH, "w") as f:
        json.dump(template, f)


def ensure_advisors_split(pdf_path):
    """Splits pdf_path into ADVISORS_PATH unless it's the same file that
    was split last time (a plain path comparison, same as the main report
    template's own new-vs-unchanged check) -- returns the resulting list
    of advisor names either way."""
    pdf_path = str(pdf_path)
    cached_source, cached_names = load_cached_advisors()
    if cached_source == pdf_path and cached_names and _cached_split_layout() >= SPLIT_LAYOUT_VERSION:
        return cached_names

    names, combos = split_advisors_pdf(pdf_path)
    _save_cached_advisors(pdf_path, names, combos)
    return names


def refresh_outdated_split():
    """Re-splits the advisors file if the library was split by an older
    version of this (before page order was kept) and the file is still
    where it was. Returns True if it rebuilt anything."""
    source, names = load_cached_advisors()
    if not source or not names or _cached_split_layout() >= SPLIT_LAYOUT_VERSION:
        return False
    if not Path(source).exists():
        return False
    ensure_advisors_split(source)
    return True


def _combo_path(names):
    return ADVISORS_PATH / ("_".join(slugify_advisor_name(name) for name in names) + ".pdf")


def order_distance(wanted, actual):
    """How far apart two orderings of the same people are: the number of
    pairs that come the other way round, then the number that sit in a
    different position. (0, 0) means identical."""
    position = {name: i for i, name in enumerate(actual)}
    pairs = sum(
        1
        for i, first in enumerate(wanted)
        for second in wanted[i + 1:]
        if position[first] > position[second]
    )
    moved = sum(1 for i, name in enumerate(wanted) if position[name] != i)
    return pairs, moved


def advisor_combo_file(selected_names):
    """The combo file for these people, in this order, or None if the
    advisors PDF has no page for them. Order matters: "Dan, Christie,
    Sally" and "Christie, Dan, Sally" are separate pages.

    selected_names may come straight from the Advisor 1/2/3/Service
    dropdowns, so blanks are dropped and a name picked twice counts once
    (a literal slug with a repeated name would never match any file).

    When no page has exactly that order, the page with the same people laid
    out closest to it is used -- a team picked from the dropdowns can't
    always reproduce a page's order exactly (the Service slot is always
    last, say), and the right people on the nearest page is better than a
    placeholder.
    """
    names = list(dict.fromkeys(name for name in selected_names if name))
    if not names:
        return None

    exact = _combo_path(names)
    if exact.exists():
        return exact

    candidates = [
        combo for combo in load_cached_advisor_combos()
        if set(combo) == set(names) and _combo_path(combo).exists()
    ]
    if not candidates:
        return None
    return _combo_path(min(candidates, key=lambda combo: order_distance(names, combo)))


# Each team member is classified once, by the user, as either an advisor
# (eligible for the Advisor 1/2/3 dropdowns) or service (eligible for the
# Service dropdown) -- nothing on the team pages themselves reliably says
# which. Keyed by name rather than tied to a particular advisors file, so
# a classification survives re-providing (or replacing) the team pages
# and is only asked for again for someone never seen before.
ROLE_ADVISOR = "advisor"
ROLE_SERVICE = "service"


def load_advisor_roles():
    """{name -> ROLE_ADVISOR | ROLE_SERVICE} for everyone classified so far."""
    try:
        with open(TEMPLATE_CONFIG_PATH) as f:
            template = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return template.get("advisor_roles", {})


def save_advisor_roles(roles):
    """Merges roles into the persisted name -> role map."""
    try:
        with open(TEMPLATE_CONFIG_PATH) as f:
            template = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        template = {}

    template["advisor_roles"] = {**template.get("advisor_roles", {}), **roles}

    with open(TEMPLATE_CONFIG_PATH, "w") as f:
        json.dump(template, f)


def unclassified_advisors(names=None):
    """The subset of names (default: the cached roster) with no saved role yet."""
    if names is None:
        _, names = load_cached_advisors()
    roles = load_advisor_roles()
    return [name for name in names if name not in roles]
