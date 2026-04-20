"""Regenerate the upcoming-schools region of README.md.

The renderer looks at ``site/_data/summerschools.yml`` and, given a reference
``today``, writes two Markdown tables into README.md between the marker lines
``<!-- UPCOMING:START -->`` and ``<!-- UPCOMING:END -->``:

* Deadlines Soon: entries whose ``deadline`` falls in ``[today, today+14]``.
* Happening Soon: entries whose ``start`` falls in ``[today, today+14]``.

Both tables are strictly time-ordered (soonest first). ``featured: true`` still
renders an inline badge on the Title cell but does not influence sort order.

Run from the repo root::

    python scripts/update_readme.py
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml
from dateutil.parser import parse as _dateutil_parse

SUMMERSCHOOLS_YML_PATH = "site/_data/summerschools.yml"
TYPES_YML_PATH = "site/_data/types.yml"
README_PATH = "README.md"

START_MARKER = "<!-- UPCOMING:START -->"
END_MARKER = "<!-- UPCOMING:END -->"

FEATURED_BADGE_URL = "https://img.shields.io/badge/featured-blue?style=plastic"
DETAILS_URL_TEMPLATE = "https://awesome-mlss.com/summerschool/{id}"
FALLBACK_MESSAGE = (
    "*No schools currently match this window. "
    "See [awesome-mlss.com](https://awesome-mlss.com/) for upcoming schools.*"
)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load(
    summerschools_path: str = SUMMERSCHOOLS_YML_PATH,
    types_path: str = TYPES_YML_PATH,
) -> Tuple[List[dict], dict]:
    """Load schools and topic-code -> display-name map from YAML."""
    with open(summerschools_path, "r", encoding="utf-8") as f:
        schools = yaml.safe_load(f) or []

    with open(types_path, "r", encoding="utf-8") as f:
        types_raw = yaml.safe_load(f) or []

    types_map = {}
    for item in types_raw:
        sub_code = item.get("sub")
        name = item.get("name", "")
        if sub_code:
            types_map[sub_code] = name

    return schools, types_map


# ---------------------------------------------------------------------------
# Date parsing helpers
# ---------------------------------------------------------------------------


def _coerce_to_date(value) -> Optional[datetime.date]:
    """Best-effort convert a YAML value to ``datetime.date``.

    Returns ``None`` when the input is missing or unparseable. YAML-native
    date/datetime values pass through directly; strings are parsed with
    python-dateutil.
    """
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return _dateutil_parse(stripped).date()
        except (ValueError, TypeError, OverflowError):
            return None
    return None


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def filter_and_sort(
    schools: Sequence[dict],
    today: datetime.date,
    window_days: int = 14,
) -> Tuple[List[dict], List[dict]]:
    """Return ``(deadlines_soon, happening_soon)`` given a reference ``today``.

    Both lists contain the original school dicts, untouched, strictly sorted
    ascending by the relevant date field (soonest first). Entries with missing
    or unparseable date fields are silently skipped from that list.
    """
    window_end = today + datetime.timedelta(days=window_days)

    deadlines_soon: List[Tuple[datetime.date, int, dict]] = []
    happening_soon: List[Tuple[datetime.date, int, dict]] = []

    for idx, school in enumerate(schools):
        deadline = _coerce_to_date(school.get("deadline"))
        if deadline is not None and today <= deadline <= window_end:
            deadlines_soon.append((deadline, idx, school))

        start = _coerce_to_date(school.get("start"))
        if start is not None and today <= start <= window_end:
            happening_soon.append((start, idx, school))

    # Stable sort: primary key is the date, tiebreaker is the YAML order index
    # so that two entries with an identical date stay in file order.
    deadlines_soon.sort(key=lambda t: (t[0], t[1]))
    happening_soon.sort(key=lambda t: (t[0], t[1]))

    return (
        [s for _, _, s in deadlines_soon],
        [s for _, _, s in happening_soon],
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _format_deadline_cell(school: dict) -> str:
    deadline = _coerce_to_date(school.get("deadline"))
    if deadline is None:
        deadline_str = str(school.get("deadline", ""))
    else:
        deadline_str = deadline.strftime("%b %d, %Y")
    school_id = school.get("id", "")
    calendar_link = DETAILS_URL_TEMPLATE.format(id=school_id)
    return f"{deadline_str} <br>\u23f0 [Add to Calendar]({calendar_link})"


def _format_date_range(school: dict) -> str:
    start = _coerce_to_date(school.get("start"))
    end = _coerce_to_date(school.get("end"))
    if start is not None and end is not None:
        return f"{start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
    # Fallback: best-effort string join.
    return f"{school.get('start', '')} - {school.get('end', '')}"


def _format_title(school: dict) -> str:
    title = school.get("title", "")
    if school.get("featured", False):
        badge = (
            f'<img src="{FEATURED_BADGE_URL}" alt="featured" width="50" />'
        )
        title = f"{title} {badge}"
    return title


def _format_topics(school: dict, types_map: Mapping[str, str]) -> str:
    sub_codes = school.get("sub", []) or []
    return ", ".join(types_map.get(code, code) for code in sub_codes)


def _render_table(
    schools: Iterable[dict],
    types_map: Mapping[str, str],
) -> str:
    rows = [
        "Title|Topics|Place|Deadline|Dates|Details",
        "-----|------|-----|--------|-----|-------",
    ]
    for school in schools:
        title = _format_title(school)
        topics = _format_topics(school, types_map)
        place = school.get("place", "")
        deadline_cell = _format_deadline_cell(school)
        dates_cell = _format_date_range(school)
        details_link = DETAILS_URL_TEMPLATE.format(id=school.get("id", ""))
        rows.append(
            f"{title}|{topics}|{place}|{deadline_cell}|{dates_cell}|"
            f"[Details]({details_link})"
        )
    return "\n".join(rows)


def render(
    deadlines: Sequence[dict],
    happening: Sequence[dict],
    types_map: Mapping[str, str],
) -> str:
    """Return the full Markdown block between (and including) the markers."""
    deadlines_body = (
        _render_table(deadlines, types_map) if deadlines else FALLBACK_MESSAGE
    )
    happening_body = (
        _render_table(happening, types_map) if happening else FALLBACK_MESSAGE
    )

    return (
        f"{START_MARKER}\n"
        "## Upcoming Summer Schools\n"
        "\n"
        "For the full list of schools worldwide, visit "
        "[awesome-mlss.com](https://awesome-mlss.com/).\n"
        "\n"
        "### Deadlines Soon\n"
        "Schools with application deadlines in the next 2 weeks.\n"
        "\n"
        f"{deadlines_body}\n"
        "\n"
        "### Happening Soon\n"
        "Schools starting in the next 2 weeks.\n"
        "\n"
        f"{happening_body}\n"
        f"{END_MARKER}"
    )


# ---------------------------------------------------------------------------
# README rewrite
# ---------------------------------------------------------------------------


def _rewrite_readme(readme_text: str, block: str) -> str:
    """Replace the region between START_MARKER and END_MARKER (inclusive)."""
    lines = readme_text.splitlines(keepends=False)

    start_count = sum(1 for line in lines if line.strip() == START_MARKER)
    end_count = sum(1 for line in lines if line.strip() == END_MARKER)
    if start_count > 1:
        raise RuntimeError(
            f"Marker appears more than once in README: {START_MARKER}"
        )
    if end_count > 1:
        raise RuntimeError(
            f"Marker appears more than once in README: {END_MARKER}"
        )

    start_idx = _find_marker_line(lines, START_MARKER)
    end_idx = _find_marker_line(lines, END_MARKER)

    if start_idx is None or end_idx is None:
        missing = []
        if start_idx is None:
            missing.append(START_MARKER)
        if end_idx is None:
            missing.append(END_MARKER)
        raise RuntimeError(
            f"Could not find required marker(s) in README: {', '.join(missing)}"
        )

    if end_idx < start_idx:
        raise RuntimeError(
            f"Marker order is wrong in README: {END_MARKER} appears before "
            f"{START_MARKER}."
        )

    new_lines = lines[:start_idx] + block.splitlines() + lines[end_idx + 1 :]
    trailing_newline = "\n" if readme_text.endswith("\n") else ""
    return "\n".join(new_lines) + trailing_newline


def _find_marker_line(lines: Sequence[str], marker: str) -> Optional[int]:
    for i, line in enumerate(lines):
        if line.strip() == marker:
            return i
    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(today: Optional[datetime.date] = None) -> None:
    """CLI entry point: load data, render upcoming block, rewrite README.md. Exits 1 if markers are missing, malformed, or duplicated."""
    if today is None:
        today = datetime.date.today()

    schools, types_map = load(SUMMERSCHOOLS_YML_PATH, TYPES_YML_PATH)
    deadlines, happening = filter_and_sort(schools, today)
    block = render(deadlines, happening, types_map)

    readme_path = Path(README_PATH)
    original = readme_path.read_text(encoding="utf-8")
    try:
        updated = _rewrite_readme(original, block)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if updated != original:
        readme_path.write_text(updated, encoding="utf-8")
        print("README.md updated successfully.")
    else:
        print("No changes to README.md.")


if __name__ == "__main__":
    main()
