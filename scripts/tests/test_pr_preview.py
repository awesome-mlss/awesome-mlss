"""Unit tests for ``scripts.pr_preview.build_preview`` and friends.

The core logic lives in ``build_preview`` — a pure function that takes the
two YAML-parsed school lists, a ``types_map``, and ``today``, and returns
the comment body. Tests focus on that function; the git-shell wrapper is
covered by a single smoke test that invokes the CLI inside this repo's
working tree.
"""

from __future__ import annotations

import datetime
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.pr_preview import (
    MARKER,
    NO_CHANGES_BODY,
    build_preview,
)


TODAY = datetime.date(2026, 4, 20)

# A minimal types_map big enough that the renderer picks up every sub code
# used in the fixtures below. Unknown codes fall back to the code string, so
# the tests work either way.
TYPES_MAP = {
    "ML": "Machine Learning",
    "CV": "Computer Vision",
    "NLP": "Natural Language Proc",
    "RL": "Reinforcement Learning",
    "GenAI": "Generative AI",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _school(
    school_id: str,
    *,
    title: str | None = None,
    deadline=None,
    start=None,
    end=None,
    place: str = "Somewhere",
    sub=None,
    featured: bool = False,
):
    entry = {
        "id": school_id,
        "title": title or school_id.capitalize(),
        "place": place,
        "sub": list(sub) if sub else ["ML"],
    }
    if deadline is not None:
        entry["deadline"] = deadline
    if start is not None:
        entry["start"] = start
    if end is not None:
        entry["end"] = end
    if featured:
        entry["featured"] = True
    return entry


def _always_starts_with_marker(body: str) -> None:
    assert body.startswith(MARKER + "\n"), (
        f"Body must start with marker + newline. First 80 chars: {body[:80]!r}"
    )


# ---------------------------------------------------------------------------
# Marker discipline
# ---------------------------------------------------------------------------


def test_marker_is_first_bytes_of_output_no_changes():
    body = build_preview([], [], TYPES_MAP, TODAY)
    _always_starts_with_marker(body)


def test_marker_is_first_bytes_of_output_with_changes():
    pr_entry = _school(
        "late26",
        deadline=datetime.date(2026, 10, 1),
        start=datetime.date(2026, 11, 1),
        end=datetime.date(2026, 11, 5),
    )
    body = build_preview([], [pr_entry], TYPES_MAP, TODAY)
    _always_starts_with_marker(body)


# ---------------------------------------------------------------------------
# 1. Added entry fully out-of-window
# ---------------------------------------------------------------------------


def test_added_entry_out_of_window_goes_to_not_visible_section():
    pr_entry = _school(
        "mlss-future26",
        title="MLSS Future",
        deadline=datetime.date(2026, 10, 1),
        start=datetime.date(2026, 11, 1),
        end=datetime.date(2026, 11, 5),
    )
    body = build_preview([], [pr_entry], TYPES_MAP, TODAY)

    _always_starts_with_marker(body)
    assert "**Not currently visible**" in body
    # Both window lines present, both resolved to date ranges.
    assert "`mlss-future26`" in body
    assert "**Deadlines Soon**: 2026-09-17 \u2192 2026-10-01" in body
    assert "**Happening Soon**: 2026-10-18 \u2192 2026-11-01" in body
    # Entry is out-of-window on both sides of the diff, so the diff
    # section should NOT appear.
    assert "**Currently visible in README**" not in body


# ---------------------------------------------------------------------------
# 2. Added entry in-window -> diff section appears
# ---------------------------------------------------------------------------


def test_added_entry_in_window_goes_to_diff_section():
    pr_entry = _school(
        "soon26",
        title="Soon School",
        deadline=datetime.date(2026, 4, 25),  # within 14 days of TODAY
        start=datetime.date(2026, 5, 5),
        end=datetime.date(2026, 5, 7),
    )
    body = build_preview([], [pr_entry], TYPES_MAP, TODAY)

    _always_starts_with_marker(body)
    assert "**Currently visible in README**" in body
    assert "```diff" in body
    # The PR side adds lines -> unified-diff will contain a "+" line
    # mentioning the title.
    assert "Soon School" in body
    # No out-of-window bucket for this entry.
    assert "**Not currently visible**" not in body


# ---------------------------------------------------------------------------
# 3. Modified entry in-window -> diff section shows the edit
# ---------------------------------------------------------------------------


def test_modified_entry_in_window_shows_in_diff():
    master_entry = _school(
        "abc26",
        title="Original Title",
        deadline=datetime.date(2026, 4, 25),
        start=datetime.date(2026, 5, 5),
        end=datetime.date(2026, 5, 7),
    )
    pr_entry = _school(
        "abc26",
        title="Revised Title",
        deadline=datetime.date(2026, 4, 25),
        start=datetime.date(2026, 5, 5),
        end=datetime.date(2026, 5, 7),
    )
    body = build_preview([master_entry], [pr_entry], TYPES_MAP, TODAY)

    _always_starts_with_marker(body)
    assert "**Currently visible in README**" in body
    assert "Original Title" in body
    assert "Revised Title" in body
    assert "**Not currently visible**" not in body
    assert "**Removed entries**" not in body


# ---------------------------------------------------------------------------
# 4. Modified entry out-of-window -> not-currently-visible section
# ---------------------------------------------------------------------------


def test_modified_entry_out_of_window_goes_to_not_visible_section():
    master_entry = _school(
        "far26",
        title="Far School",
        deadline=datetime.date(2026, 10, 1),
        start=datetime.date(2026, 11, 1),
        end=datetime.date(2026, 11, 5),
    )
    # Same id, shifted a bit; still fully out of window.
    pr_entry = _school(
        "far26",
        title="Far School",
        deadline=datetime.date(2026, 10, 15),
        start=datetime.date(2026, 11, 1),
        end=datetime.date(2026, 11, 5),
    )
    body = build_preview([master_entry], [pr_entry], TYPES_MAP, TODAY)

    _always_starts_with_marker(body)
    assert "**Not currently visible**" in body
    assert "`far26`" in body
    assert "**Deadlines Soon**: 2026-10-01 \u2192 2026-10-15" in body
    # The diff section should NOT appear because neither master nor PR
    # render includes this entry (both are out-of-window).
    assert "**Currently visible in README**" not in body


# ---------------------------------------------------------------------------
# 5. Removed entry that was in-window at removal
# ---------------------------------------------------------------------------


def test_removed_entry_in_window_reports_was_in_window():
    master_entry = _school(
        "goodbye26",
        title="Goodbye School",
        deadline=datetime.date(2026, 4, 25),
        start=datetime.date(2026, 5, 5),
        end=datetime.date(2026, 5, 7),
    )
    body = build_preview([master_entry], [], TYPES_MAP, TODAY)

    _always_starts_with_marker(body)
    assert "**Removed entries**" in body
    assert "`goodbye26`" in body
    assert "*(was in window at time of removal)*" in body
    # Since removal makes the master render include it but the PR render
    # excludes it, the diff section should ALSO appear here.
    assert "**Currently visible in README**" in body


# ---------------------------------------------------------------------------
# 6. Removed entry that was out-of-window
# ---------------------------------------------------------------------------


def test_removed_entry_out_of_window_reports_was_not_in_window():
    master_entry = _school(
        "farbye26",
        title="Far Goodbye",
        deadline=datetime.date(2026, 10, 1),
        start=datetime.date(2026, 11, 1),
        end=datetime.date(2026, 11, 5),
    )
    body = build_preview([master_entry], [], TYPES_MAP, TODAY)

    _always_starts_with_marker(body)
    assert "**Removed entries**" in body
    assert "`farbye26`" in body
    assert "*(was not in window at time of removal)*" in body
    # Out-of-window on both sides -> diff section must be absent.
    assert "**Currently visible in README**" not in body


# ---------------------------------------------------------------------------
# 7. No changes -> short body
# ---------------------------------------------------------------------------


def test_no_changes_returns_short_no_changes_body():
    # Same schools on both sides, same object graph -> no diff, nothing to
    # classify.
    entry = _school(
        "same26",
        deadline=datetime.date(2026, 10, 1),
        start=datetime.date(2026, 11, 1),
        end=datetime.date(2026, 11, 5),
    )
    body = build_preview([entry], [entry], TYPES_MAP, TODAY)

    assert body == NO_CHANGES_BODY
    _always_starts_with_marker(body)
    assert "No detected changes" in body


# ---------------------------------------------------------------------------
# 8. Added entry with deadline='TBA' -> fallback text + real happening window
# ---------------------------------------------------------------------------


def test_added_entry_with_tba_deadline_shows_fallback_for_deadline_window():
    pr_entry = _school(
        "tba26",
        title="TBA School",
        deadline="TBA",
        start=datetime.date(2026, 11, 1),
        end=datetime.date(2026, 11, 5),
    )
    body = build_preview([], [pr_entry], TYPES_MAP, TODAY)

    _always_starts_with_marker(body)
    assert "**Not currently visible**" in body
    assert "`tba26`" in body
    # Deadlines Soon fallback wording.
    assert (
        "**Deadlines Soon**: *(deadline is TBA \u2014 will not appear in "
        "Deadlines Soon until a date is set)*"
    ) in body
    # Happening Soon still computed.
    assert "**Happening Soon**: 2026-10-18 \u2192 2026-11-01" in body


def test_added_entry_with_missing_start_shows_fallback_for_happening_window():
    pr_entry = {
        "id": "nostart26",
        "title": "No Start",
        "deadline": datetime.date(2026, 10, 1),
        "place": "Nowhere",
        "sub": ["ML"],
        # Deliberately no "start".
    }
    body = build_preview([], [pr_entry], TYPES_MAP, TODAY)

    _always_starts_with_marker(body)
    assert "**Not currently visible**" in body
    assert (
        "**Happening Soon**: *(start date not set \u2014 will not appear in "
        "Happening Soon until a date is set)*"
    ) in body


# ---------------------------------------------------------------------------
# 9. Empty sections are not rendered
# ---------------------------------------------------------------------------


def test_empty_currently_visible_section_is_omitted():
    # Only out-of-window adds -> must NOT contain the "Currently visible"
    # header.
    pr_entry = _school(
        "far2",
        deadline=datetime.date(2027, 1, 1),
        start=datetime.date(2027, 2, 1),
        end=datetime.date(2027, 2, 5),
    )
    body = build_preview([], [pr_entry], TYPES_MAP, TODAY)
    assert "**Currently visible in README**" not in body
    # Sanity: the section we DO expect is still there.
    assert "**Not currently visible**" in body


def test_empty_not_currently_visible_section_is_omitted():
    # Only an in-window modification -> "Not currently visible" header
    # should be absent.
    master_entry = _school(
        "inwin26",
        title="Before",
        deadline=datetime.date(2026, 4, 25),
        start=datetime.date(2026, 5, 5),
        end=datetime.date(2026, 5, 7),
    )
    pr_entry = _school(
        "inwin26",
        title="After",
        deadline=datetime.date(2026, 4, 25),
        start=datetime.date(2026, 5, 5),
        end=datetime.date(2026, 5, 7),
    )
    body = build_preview([master_entry], [pr_entry], TYPES_MAP, TODAY)
    assert "**Currently visible in README**" in body
    assert "**Not currently visible**" not in body
    assert "**Removed entries**" not in body


def test_empty_removed_section_is_omitted():
    pr_entry = _school(
        "solo26",
        deadline=datetime.date(2026, 10, 1),
        start=datetime.date(2026, 11, 1),
        end=datetime.date(2026, 11, 5),
    )
    body = build_preview([], [pr_entry], TYPES_MAP, TODAY)
    assert "**Removed entries**" not in body


# ---------------------------------------------------------------------------
# Ordering: marker first, then the README preview header on the next line
# ---------------------------------------------------------------------------


def test_preview_header_follows_marker():
    pr_entry = _school(
        "hdr26",
        deadline=datetime.date(2026, 4, 25),
        start=datetime.date(2026, 5, 5),
        end=datetime.date(2026, 5, 7),
    )
    body = build_preview([], [pr_entry], TYPES_MAP, TODAY)
    lines = body.splitlines()
    assert lines[0] == MARKER
    assert lines[1] == "**README preview for this PR**"


# ---------------------------------------------------------------------------
# Smoke test: run the CLI inside this repo. Verifies that git-plumbing works
# when a master ref actually exists. We don't assert content — only that the
# script exits 0 and writes a file starting with the marker.
# ---------------------------------------------------------------------------


def test_cli_smoke_runs_inside_repo(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    # If this checkout has no master ref (e.g. shallow PR clone), skip.
    rc = subprocess.run(
        ["git", "rev-parse", "--verify", "master"],
        cwd=repo_root,
        capture_output=True,
    )
    if rc.returncode != 0:
        pytest.skip("master ref not available in this checkout")

    output = tmp_path / "preview.md"
    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "pr_preview.py"),
            "--output",
            str(output),
            "--today",
            "2026-04-20",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    body = output.read_text(encoding="utf-8")
    assert body.startswith(MARKER + "\n")
