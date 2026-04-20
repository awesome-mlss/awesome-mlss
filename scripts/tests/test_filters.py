"""Unit tests for ``scripts.update_readme.filter_and_sort``."""

from __future__ import annotations

import datetime

import pytest

from scripts.update_readme import filter_and_sort


def _school(
    school_id: str,
    *,
    deadline=None,
    start=None,
    end=None,
    featured: bool = False,
    title: str | None = None,
):
    entry = {"id": school_id, "title": title or school_id}
    if deadline is not None:
        entry["deadline"] = deadline
    if start is not None:
        entry["start"] = start
    if end is not None:
        entry["end"] = end
    if featured:
        entry["featured"] = True
    return entry


TODAY = datetime.date(2026, 4, 20)


def _ids(entries):
    return [s["id"] for s in entries]


# ---------------------------------------------------------------------------
# Deadline-window membership
# ---------------------------------------------------------------------------


def test_deadline_inside_window_included():
    schools = [_school("a", deadline=datetime.date(2026, 4, 25))]
    deadlines, _ = filter_and_sort(schools, TODAY)
    assert _ids(deadlines) == ["a"]


def test_deadline_on_lower_boundary_included():
    schools = [_school("a", deadline=TODAY)]
    deadlines, _ = filter_and_sort(schools, TODAY)
    assert _ids(deadlines) == ["a"]


def test_deadline_on_upper_boundary_included():
    schools = [_school("a", deadline=TODAY + datetime.timedelta(days=14))]
    deadlines, _ = filter_and_sort(schools, TODAY)
    assert _ids(deadlines) == ["a"]


def test_deadline_before_window_excluded():
    schools = [_school("a", deadline=TODAY - datetime.timedelta(days=1))]
    deadlines, _ = filter_and_sort(schools, TODAY)
    assert deadlines == []


def test_deadline_after_window_excluded():
    schools = [_school("a", deadline=TODAY + datetime.timedelta(days=15))]
    deadlines, _ = filter_and_sort(schools, TODAY)
    assert deadlines == []


def test_missing_deadline_skipped_from_deadlines_but_not_happening():
    """Missing ``deadline`` should not stop the entry from being considered
    for Happening Soon."""
    schools = [_school("a", start=TODAY + datetime.timedelta(days=3))]
    deadlines, happening = filter_and_sort(schools, TODAY)
    assert deadlines == []
    assert _ids(happening) == ["a"]


def test_unparseable_deadline_skipped():
    schools = [_school("a", deadline="TBA")]
    deadlines, _ = filter_and_sort(schools, TODAY)
    assert deadlines == []


def test_string_deadline_with_time_parsed():
    schools = [_school("a", deadline="2026-04-23 23:59:59")]
    deadlines, _ = filter_and_sort(schools, TODAY)
    assert _ids(deadlines) == ["a"]


# ---------------------------------------------------------------------------
# Start-window membership
# ---------------------------------------------------------------------------


def test_start_inside_window_included():
    schools = [_school("a", start=TODAY + datetime.timedelta(days=7))]
    _, happening = filter_and_sort(schools, TODAY)
    assert _ids(happening) == ["a"]


def test_start_outside_window_excluded():
    schools = [_school("a", start=TODAY + datetime.timedelta(days=30))]
    _, happening = filter_and_sort(schools, TODAY)
    assert happening == []


def test_missing_start_skipped_from_happening():
    schools = [_school("a", deadline=TODAY + datetime.timedelta(days=3))]
    _, happening = filter_and_sort(schools, TODAY)
    assert happening == []


def test_unparseable_start_skipped():
    schools = [_school("a", start="to be confirmed")]
    _, happening = filter_and_sort(schools, TODAY)
    assert happening == []


# ---------------------------------------------------------------------------
# Both lists
# ---------------------------------------------------------------------------


def test_entry_in_both_windows_appears_in_both_lists():
    schools = [
        _school(
            "a",
            deadline=TODAY + datetime.timedelta(days=2),
            start=TODAY + datetime.timedelta(days=10),
        )
    ]
    deadlines, happening = filter_and_sort(schools, TODAY)
    assert _ids(deadlines) == ["a"]
    assert _ids(happening) == ["a"]


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------


def test_deadlines_sorted_ascending():
    schools = [
        _school("late", deadline=TODAY + datetime.timedelta(days=10)),
        _school("early", deadline=TODAY + datetime.timedelta(days=1)),
        _school("mid", deadline=TODAY + datetime.timedelta(days=5)),
    ]
    deadlines, _ = filter_and_sort(schools, TODAY)
    assert _ids(deadlines) == ["early", "mid", "late"]


def test_happening_sorted_ascending():
    schools = [
        _school("late", start=TODAY + datetime.timedelta(days=12)),
        _school("early", start=TODAY + datetime.timedelta(days=2)),
        _school("mid", start=TODAY + datetime.timedelta(days=7)),
    ]
    _, happening = filter_and_sort(schools, TODAY)
    assert _ids(happening) == ["early", "mid", "late"]


def test_featured_does_not_affect_order():
    """Featured entries should stay strictly time-ordered, not bubble to top."""
    schools = [
        _school(
            "featured_late",
            deadline=TODAY + datetime.timedelta(days=10),
            featured=True,
        ),
        _school("plain_early", deadline=TODAY + datetime.timedelta(days=1)),
    ]
    deadlines, _ = filter_and_sort(schools, TODAY)
    assert _ids(deadlines) == ["plain_early", "featured_late"]


def test_identical_deadlines_preserve_file_order():
    same = TODAY + datetime.timedelta(days=5)
    schools = [
        _school("first", deadline=same),
        _school("second", deadline=same),
    ]
    deadlines, _ = filter_and_sort(schools, TODAY)
    assert _ids(deadlines) == ["first", "second"]


# ---------------------------------------------------------------------------
# Leap-day boundary
# ---------------------------------------------------------------------------


def test_leap_day_window_math():
    """T=2024-02-29 plus 14 days should land on 2024-03-14 (leap year)."""
    leap_today = datetime.date(2024, 2, 29)
    schools = [
        _school("on_leap", deadline=leap_today),
        _school("last_day_in_window", deadline=datetime.date(2024, 3, 14)),
        _school("just_past_window", deadline=datetime.date(2024, 3, 15)),
    ]
    deadlines, _ = filter_and_sort(schools, leap_today)
    assert _ids(deadlines) == ["on_leap", "last_day_in_window"]


def test_non_leap_year_feb_28_plus_14_lands_in_march():
    """Sanity check: 2026-02-28 + 14 days = 2026-03-14."""
    today = datetime.date(2026, 2, 28)
    schools = [
        _school("on_boundary", deadline=datetime.date(2026, 3, 14)),
        _school("past_boundary", deadline=datetime.date(2026, 3, 15)),
    ]
    deadlines, _ = filter_and_sort(schools, today)
    assert _ids(deadlines) == ["on_boundary"]


# ---------------------------------------------------------------------------
# Mixed-input sanity
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty_lists():
    deadlines, happening = filter_and_sort([], TODAY)
    assert deadlines == []
    assert happening == []


def test_window_days_override():
    schools = [_school("a", deadline=TODAY + datetime.timedelta(days=20))]
    # Default 14 -> empty.
    deadlines_default, _ = filter_and_sort(schools, TODAY)
    assert deadlines_default == []
    # Extended 30 -> included.
    deadlines_extended, _ = filter_and_sort(schools, TODAY, window_days=30)
    assert _ids(deadlines_extended) == ["a"]
