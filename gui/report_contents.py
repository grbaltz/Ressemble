"""What the assembled report will and won't contain, given the builder's
current choices -- shown live in the Builder's "Report contents" panel.

Kept free of Qt so it can be tested on its own. The rules mirror
assemble_report() in src/assembler.py: which template slots disappear when
a source is missing comes straight from its SECTION_SLOTS, so the two
can't drift apart.
"""
from dataclasses import dataclass
from src.assembler import SECTION_SLOTS


@dataclass(frozen=True)
class PagePreview:
    """One page of a PDF that can be shown when hovering a row."""
    pdf_path: str
    page: int = 0


@dataclass(frozen=True)
class ContentRow:
    key: str
    title: str
    detail: str
    included: bool
    # Set only when the row contributes exactly one page to the report --
    # there's no single page to show for a section that spans several.
    preview: PagePreview = None


def describe_contents(
    *,
    client_name,
    date_text,
    has_emx,
    has_bd,
    include_plan_360,
    team_names,
    emx_detail=None,
    bd_detail=None,
    emx_pdf=None,
    emx_pages=None,
    disclaimer_pdf=None,
    team_pdf=None,
):
    """`emx_pdf`/`emx_pages` (the EMX file and its page count), `disclaimer_pdf`
    (the template's Plan 360 disclaimer page) and `team_pdf` (the one-page
    team file for the chosen advisors) are only used to offer hover
    previews, for rows that come down to a single page."""
    rows = []

    rows.append(ContentRow(
        "cover",
        "Cover and agenda",
        f"{client_name.strip() or 'Client name needed'} · {date_text}",
        True,
    ))

    rows.append(ContentRow(
        "emx",
        "Financial plan",
        (emx_detail or "EMX") if has_emx else "Left out. No EMX file.",
        has_emx,
        PagePreview(emx_pdf, 0) if has_emx and emx_pdf and emx_pages == 1 else None,
    ))

    # The title page belongs to the EMX section (it's dropped along with
    # it), but the disclaimer only ever depends on the Plan 360 option.
    title_needs_emx = "plan360Title" in SECTION_SLOTS["emx"]
    title_included = include_plan_360 and (has_emx or not title_needs_emx)
    if not include_plan_360:
        plan_detail = "Left out. Turned off in options."
    elif title_included:
        plan_detail = "Title page and disclaimer"
    else:
        plan_detail = "Disclaimer only. The title page needs an EMX file."
    # With the title page gone only the disclaimer is left: one page.
    plan_preview = PagePreview(disclaimer_pdf, 0) if include_plan_360 and not title_included and disclaimer_pdf else None
    rows.append(ContentRow("plan360", "Plan 360", plan_detail, include_plan_360, plan_preview))

    rows.append(ContentRow(
        "portfolio",
        "Portfolio and allocation",
        (bd_detail or "Black Diamond") if has_bd else "Left out. No Black Diamond file.",
        has_bd,
    ))

    team_names = [name for name in team_names if name]
    rows.append(ContentRow(
        "team",
        "Team page",
        ", ".join(team_names) if team_names else "Choose at least one advisor",
        bool(team_names),
        PagePreview(team_pdf, 0) if team_names and team_pdf else None,
    ))

    return rows
