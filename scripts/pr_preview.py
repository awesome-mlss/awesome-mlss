"""Produce a PR-comment body describing what a PR changes in the README.

Invoked by the ``diff-readme-on-pr.yml`` GitHub Actions workflow from a
checkout of the PR branch. Reads the PR's ``site/_data/summerschools.yml``
from disk, the master version via ``git show master:site/_data/summerschools.yml``,
and renders a unified diff of the README block plus lists of entries that are
added/modified/removed but fall outside the live 2-week visibility window.

The comment body always starts with ``<!-- readme-preview-bot -->\\n`` so that
``peter-evans/find-comment`` can locate and update the prior comment rather
than duplicate it.

CLI::

    python scripts/pr_preview.py [--output preview.md] [--today YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml

# Allow `python scripts/pr_preview.py` from the repo root even before the
# package is installed; mirrors conftest.py's path-insertion trick.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.update_readme import (  # noqa: E402
    SUMMERSCHOOLS_YML_PATH,
    TYPES_YML_PATH,
    filter_and_sort,
    load,
    render,
)
from scripts.windows import compute_visibility  # noqa: E402


MARKER = "<!-- readme-preview-bot -->"
NO_CHANGES_BODY = (
    f"{MARKER}\n"
    "**README preview for this PR**\n"
    "\n"
    "No detected changes to entries in `summerschools.yml`.\n"
)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_schools_yaml(text: str, source_label: str) -> List[dict]:
    """Parse YAML content into a list of school dicts.

    ``source_label`` is used to annotate any error message that bubbles up.
    """
    try:
        parsed = yaml.safe_load(text) or []
    except yaml.YAMLError as exc:
        raise RuntimeError(
            f"Failed to parse summerschools.yml from {source_label}: {exc}"
        ) from exc
    if not isinstance(parsed, list):
        raise RuntimeError(
            f"Expected list of schools in summerschools.yml from "
            f"{source_label}, got {type(parsed).__name__}"
        )
    return parsed


def _read_master_schools_text() -> str:
    """Fetch master's copy of summerschools.yml via ``git show``.

    Raises ``RuntimeError`` on failure so the caller can print a clear
    error to stderr and exit.
    """
    try:
        completed = subprocess.run(
            ["git", "show", f"master:{SUMMERSCHOOLS_YML_PATH}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "git executable not found; pr_preview.py must be run inside a "
            "git checkout"
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(
            "Could not resolve master:"
            f"{SUMMERSCHOOLS_YML_PATH} via `git show` "
            f"(exit {completed.returncode}): {stderr}"
        )
    return completed.stdout


# ---------------------------------------------------------------------------
# Core diff logic (pure functions — exhaustively tested)
# ---------------------------------------------------------------------------


def _index_by_id(schools: Sequence[dict]) -> "dict[str, dict]":
    """Return ``{id: entry}``; silently drops entries without an ``id``."""
    out: "dict[str, dict]" = {}
    for entry in schools:
        entry_id = entry.get("id")
        if entry_id:
            out[entry_id] = entry
    return out


def _classify(
    master_by_id: Mapping[str, dict],
    pr_by_id: Mapping[str, dict],
) -> Tuple[List[str], List[str], List[str]]:
    """Split ids into (added, modified, removed) lists, each sorted."""
    master_ids = set(master_by_id)
    pr_ids = set(pr_by_id)

    added = sorted(pr_ids - master_ids)
    removed = sorted(master_ids - pr_ids)
    modified = sorted(
        i for i in pr_ids & master_ids if pr_by_id[i] != master_by_id[i]
    )
    return added, modified, removed


def _is_entry_in_window(entry: dict, today: datetime.date) -> bool:
    """Does ``entry`` land in either the deadline or happening visible window?

    The window here is "would appear in the README tables given today" — i.e.
    today ∈ [deadline-14, deadline] or today ∈ [start-14, start].
    """
    windows = compute_visibility(entry, today)
    for window in (windows.get("deadline"), windows.get("happening")):
        if window is None:
            continue
        from_date, to_date = window
        if from_date <= today <= to_date:
            return True
    return False


def _format_window_line(
    label: str,
    window: Optional[Tuple[datetime.date, datetime.date]],
    missing_fallback: str,
) -> str:
    """Render one of the two "Not currently visible" bullet lines."""
    if window is None:
        return f"  - **{label}**: {missing_fallback}"
    from_date, to_date = window
    return (
        f"  - **{label}**: {from_date.isoformat()} \u2192 {to_date.isoformat()}"
    )


def _format_not_visible_entry(entry: dict, today: datetime.date) -> str:
    """Render one "Not currently visible" entry — id, title, both windows."""
    windows = compute_visibility(entry, today)

    deadline_line = _format_window_line(
        "Deadlines Soon",
        windows.get("deadline"),
        "*(deadline is TBA \u2014 will not appear in Deadlines Soon until a "
        "date is set)*",
    )
    happening_line = _format_window_line(
        "Happening Soon",
        windows.get("happening"),
        "*(start date not set \u2014 will not appear in Happening Soon "
        "until a date is set)*",
    )

    entry_id = entry.get("id", "")
    title = entry.get("title", "")
    header = f"- `{entry_id}` \u2014 \"{title}\""
    return f"{header}\n{deadline_line}\n{happening_line}"


def _render_diff(
    master_schools: Sequence[dict],
    pr_schools: Sequence[dict],
    types_map: Mapping[str, str],
    today: datetime.date,
) -> str:
    """Unified diff between the two rendered README blocks."""
    master_deadlines, master_happening = filter_and_sort(master_schools, today)
    pr_deadlines, pr_happening = filter_and_sort(pr_schools, today)

    master_block = render(master_deadlines, master_happening, types_map)
    pr_block = render(pr_deadlines, pr_happening, types_map)

    diff_lines = difflib.unified_diff(
        master_block.splitlines(),
        pr_block.splitlines(),
        fromfile="master README",
        tofile="PR README",
        lineterm="",
    )
    return "\n".join(diff_lines)


def build_preview(
    master_schools: Sequence[dict],
    pr_schools: Sequence[dict],
    types_map: Mapping[str, str],
    today: datetime.date,
) -> str:
    """Return the full PR-comment body.

    Pure function — no I/O — so it can be tested exhaustively without git.
    """
    master_by_id = _index_by_id(master_schools)
    pr_by_id = _index_by_id(pr_schools)
    added, modified, removed = _classify(master_by_id, pr_by_id)

    diff_text = _render_diff(master_schools, pr_schools, types_map, today)

    # Partition added/modified into in-window and out-of-window for messaging.
    not_visible_entries: List[dict] = []
    for entry_id in added:
        entry = pr_by_id[entry_id]
        if not _is_entry_in_window(entry, today):
            not_visible_entries.append(entry)
    for entry_id in modified:
        entry = pr_by_id[entry_id]
        # A modified entry might be in-window in either master or PR; the
        # diff section already surfaces visible changes. Surface in "not
        # currently visible" only when its PR form is outside the window.
        if not _is_entry_in_window(entry, today):
            not_visible_entries.append(entry)

    # Short-circuit: nothing changed at all.
    any_changes = bool(diff_text) or bool(added or modified or removed)
    if not any_changes:
        return NO_CHANGES_BODY

    sections: List[str] = [f"{MARKER}\n**README preview for this PR**"]

    if diff_text:
        sections.append(
            "**Currently visible in README** "
            "(edits within the live 2-week window)\n"
            "```diff\n"
            f"{diff_text}\n"
            "```"
        )

    if not_visible_entries:
        lines = [
            "**Not currently visible** "
            "(outside the 2-week window \u2014 these entries will appear "
            "later)"
        ]
        for entry in not_visible_entries:
            lines.append(_format_not_visible_entry(entry, today))
        sections.append("\n".join(lines))

    if removed:
        lines = ["**Removed entries**"]
        for entry_id in removed:
            entry = master_by_id[entry_id]
            was_in_window = _is_entry_in_window(entry, today)
            clause = (
                "*(was in window at time of removal)*"
                if was_in_window
                else "*(was not in window at time of removal)*"
            )
            lines.append(
                f"- `{entry_id}` \u2014 entry was deleted in this PR. {clause}"
            )
        sections.append("\n".join(lines))

    # Join sections with one blank line between them, then a trailing newline.
    return "\n\n".join(sections) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate README preview comment for a PR."
    )
    parser.add_argument(
        "--output",
        default="preview.md",
        help="Path to write the comment body (default: preview.md).",
    )
    parser.add_argument(
        "--today",
        default=None,
        help="Override today's date (ISO YYYY-MM-DD) for deterministic runs.",
    )
    return parser.parse_args(argv)


def _resolve_today(today_str: Optional[str]) -> datetime.date:
    if today_str is None:
        return datetime.date.today()
    try:
        return datetime.date.fromisoformat(today_str)
    except ValueError as exc:
        raise SystemExit(
            f"--today must be ISO YYYY-MM-DD, got: {today_str!r} ({exc})"
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    today = _resolve_today(args.today)

    # PR's working-copy YAML (schools + shared types map loaded from disk).
    try:
        pr_schools, types_map = load(SUMMERSCHOOLS_YML_PATH, TYPES_YML_PATH)
    except yaml.YAMLError as exc:
        print(
            f"ERROR: Failed to parse PR's summerschools.yml: {exc}",
            file=sys.stderr,
        )
        return 1
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # master's YAML via git.
    try:
        master_text = _read_master_schools_text()
        master_schools = _parse_schools_yaml(master_text, "master")
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    body = build_preview(master_schools, pr_schools, types_map, today)

    output_path = Path(args.output)
    output_path.write_text(body, encoding="utf-8")

    # Echo to stdout so workflow logs show the full comment body.
    sys.stdout.write(body)
    if not body.endswith("\n"):
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
