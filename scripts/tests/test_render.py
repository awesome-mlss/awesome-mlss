"""Golden-file tests for ``scripts.update_readme.render``."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from scripts.update_readme import (
    END_MARKER,
    START_MARKER,
    FALLBACK_MESSAGE,
    _rewrite_readme,
    filter_and_sort,
    load,
    render,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _read_golden(name: str) -> str:
    # Golden files store the block with a single trailing newline for tidy
    # editor behavior; ``render`` returns the block with no trailing newline,
    # so strip exactly one.
    return FIXTURES_DIR.joinpath(name).read_text(encoding="utf-8").rstrip("\n")


def test_render_matches_golden_fixture():
    schools, types_map = load(
        str(FIXTURES_DIR / "schools.yml"),
        str(FIXTURES_DIR / "types.yml"),
    )
    today = datetime.date(2026, 4, 20)
    deadlines, happening = filter_and_sort(schools, today)

    actual = render(deadlines, happening, types_map)
    expected = _read_golden("expected_readme_block.md")

    assert actual == expected


def test_render_empty_both_sections_fallback():
    actual = render([], [], {})
    expected = _read_golden("expected_empty_block.md")

    assert actual == expected
    # Also a direct structural check so a future golden edit can't silently
    # remove the fallback line.
    assert actual.count(FALLBACK_MESSAGE) == 2


def test_render_wraps_in_markers():
    block = render([], [], {})
    assert block.startswith(START_MARKER + "\n")
    assert block.endswith(END_MARKER)


# ---------------------------------------------------------------------------
# _rewrite_readme: marker plumbing
# ---------------------------------------------------------------------------


def test_rewrite_replaces_region_between_markers():
    original = (
        "before\n"
        f"{START_MARKER}\n"
        "old content line 1\n"
        "old content line 2\n"
        f"{END_MARKER}\n"
        "after\n"
    )
    new_block = f"{START_MARKER}\nNEW\n{END_MARKER}"
    updated = _rewrite_readme(original, new_block)
    assert updated == (
        "before\n"
        f"{START_MARKER}\n"
        "NEW\n"
        f"{END_MARKER}\n"
        "after\n"
    )


def test_rewrite_preserves_trailing_newline_absence():
    original = (
        f"{START_MARKER}\nold\n{END_MARKER}"  # no trailing newline
    )
    new_block = f"{START_MARKER}\nNEW\n{END_MARKER}"
    updated = _rewrite_readme(original, new_block)
    assert updated == new_block
    assert not updated.endswith("\n")


def test_rewrite_missing_start_marker_raises():
    original = f"just some content\n{END_MARKER}\n"
    with pytest.raises(RuntimeError, match=START_MARKER):
        _rewrite_readme(original, "ignored")


def test_rewrite_missing_end_marker_raises():
    original = f"{START_MARKER}\njust some content\n"
    with pytest.raises(RuntimeError, match=END_MARKER):
        _rewrite_readme(original, "ignored")


def test_rewrite_both_markers_missing_raises():
    with pytest.raises(RuntimeError):
        _rewrite_readme("nothing here\n", "ignored")


def test_rewrite_reversed_markers_raises():
    original = f"{END_MARKER}\nstuff\n{START_MARKER}\n"
    with pytest.raises(RuntimeError):
        _rewrite_readme(original, "ignored")


def test_rewrite_duplicate_start_marker_raises():
    original = (
        f"{START_MARKER}\n"
        "old content\n"
        f"{END_MARKER}\n"
        "middle\n"
        f"{START_MARKER}\n"
        "extra\n"
        f"{END_MARKER}\n"
    )
    with pytest.raises(RuntimeError, match=START_MARKER):
        _rewrite_readme(original, "ignored")


def test_rewrite_duplicate_end_marker_raises():
    original = (
        f"{START_MARKER}\n"
        "old content\n"
        f"{END_MARKER}\n"
        "middle\n"
        f"{END_MARKER}\n"
    )
    with pytest.raises(RuntimeError, match=END_MARKER):
        _rewrite_readme(original, "ignored")


def test_rewrite_duplicate_start_error_names_marker():
    """Error message must identify which marker was duplicated."""
    original = (
        f"{START_MARKER}\ncontent\n{END_MARKER}\n"
        f"{START_MARKER}\nmore\n{END_MARKER}\n"
    )
    with pytest.raises(RuntimeError, match=START_MARKER):
        _rewrite_readme(original, "ignored")


def test_rewrite_duplicate_end_error_names_marker():
    """Error message must identify which marker was duplicated."""
    original = (
        f"{START_MARKER}\ncontent\n{END_MARKER}\n"
        f"extra line\n{END_MARKER}\n"
    )
    with pytest.raises(RuntimeError, match=END_MARKER):
        _rewrite_readme(original, "ignored")
