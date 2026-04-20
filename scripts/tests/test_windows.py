"""Unit tests for ``scripts.windows.compute_visibility``."""

from __future__ import annotations

import datetime

import pytest

from scripts.windows import compute_visibility

TODAY = datetime.date(2026, 4, 20)
DEFAULT_WINDOW = 14


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(*, deadline=None, start=None):
    e: dict = {}
    if deadline is not None:
        e["deadline"] = deadline
    if start is not None:
        e["start"] = start
    return e


def _window_size(window):
    """Return the number of days spanned by (from_date, to_date), inclusive."""
    from_date, to_date = window
    return (to_date - from_date).days


# ---------------------------------------------------------------------------
# Both fields present
# ---------------------------------------------------------------------------


def test_both_fields_present_returns_both_windows():
    deadline = datetime.date(2026, 7, 15)
    start = datetime.date(2026, 8, 1)
    entry = _entry(deadline=deadline, start=start)
    result = compute_visibility(entry, TODAY)

    assert result["deadline"] is not None
    assert result["happening"] is not None


def test_deadline_window_to_date_matches_deadline():
    deadline = datetime.date(2026, 7, 15)
    entry = _entry(deadline=deadline, start=datetime.date(2026, 8, 1))
    result = compute_visibility(entry, TODAY)

    _, to_date = result["deadline"]
    assert to_date == deadline


def test_happening_window_to_date_matches_start():
    start = datetime.date(2026, 8, 1)
    entry = _entry(deadline=datetime.date(2026, 7, 15), start=start)
    result = compute_visibility(entry, TODAY)

    _, to_date = result["happening"]
    assert to_date == start


def test_deadline_window_size_is_window_days():
    deadline = datetime.date(2026, 7, 15)
    entry = _entry(deadline=deadline)
    result = compute_visibility(entry, TODAY)

    assert _window_size(result["deadline"]) == DEFAULT_WINDOW


def test_happening_window_size_is_window_days():
    start = datetime.date(2026, 8, 1)
    entry = _entry(start=start)
    result = compute_visibility(entry, TODAY)

    assert _window_size(result["happening"]) == DEFAULT_WINDOW


def test_deadline_window_from_date_is_deadline_minus_window_days():
    deadline = datetime.date(2026, 7, 15)
    entry = _entry(deadline=deadline)
    result = compute_visibility(entry, TODAY)

    from_date, _ = result["deadline"]
    assert from_date == deadline - datetime.timedelta(days=DEFAULT_WINDOW)


def test_happening_window_from_date_is_start_minus_window_days():
    start = datetime.date(2026, 8, 1)
    entry = _entry(start=start)
    result = compute_visibility(entry, TODAY)

    from_date, _ = result["happening"]
    assert from_date == start - datetime.timedelta(days=DEFAULT_WINDOW)


# ---------------------------------------------------------------------------
# Missing fields
# ---------------------------------------------------------------------------


def test_missing_deadline_returns_none_for_deadline_key():
    entry = _entry(start=datetime.date(2026, 8, 1))
    result = compute_visibility(entry, TODAY)

    assert result["deadline"] is None


def test_missing_deadline_still_computes_happening():
    start = datetime.date(2026, 8, 1)
    entry = _entry(start=start)
    result = compute_visibility(entry, TODAY)

    assert result["happening"] is not None
    _, to_date = result["happening"]
    assert to_date == start


def test_missing_start_returns_none_for_happening_key():
    entry = _entry(deadline=datetime.date(2026, 7, 15))
    result = compute_visibility(entry, TODAY)

    assert result["happening"] is None


def test_missing_start_still_computes_deadline():
    deadline = datetime.date(2026, 7, 15)
    entry = _entry(deadline=deadline)
    result = compute_visibility(entry, TODAY)

    assert result["deadline"] is not None
    _, to_date = result["deadline"]
    assert to_date == deadline


def test_both_missing_returns_both_none():
    result = compute_visibility({}, TODAY)

    assert result["deadline"] is None
    assert result["happening"] is None


# ---------------------------------------------------------------------------
# Unparseable / special strings
# ---------------------------------------------------------------------------


def test_deadline_tba_returns_none():
    entry = _entry(deadline="TBA", start=datetime.date(2026, 8, 1))
    result = compute_visibility(entry, TODAY)

    assert result["deadline"] is None


def test_happening_still_computed_when_deadline_is_tba():
    start = datetime.date(2026, 8, 1)
    entry = _entry(deadline="TBA", start=start)
    result = compute_visibility(entry, TODAY)

    assert result["happening"] is not None


# ---------------------------------------------------------------------------
# String inputs
# ---------------------------------------------------------------------------


def test_deadline_as_iso_string_parses_correctly():
    entry = _entry(deadline="2026-07-15")
    result = compute_visibility(entry, TODAY)

    assert result["deadline"] is not None
    _, to_date = result["deadline"]
    assert to_date == datetime.date(2026, 7, 15)


def test_deadline_window_from_date_type_is_date_when_string_input():
    entry = _entry(deadline="2026-07-15")
    result = compute_visibility(entry, TODAY)

    from_date, to_date = result["deadline"]
    assert isinstance(from_date, datetime.date)
    assert isinstance(to_date, datetime.date)


# ---------------------------------------------------------------------------
# datetime.datetime inputs
# ---------------------------------------------------------------------------


def test_deadline_as_datetime_coerced_to_date():
    dt = datetime.datetime(2026, 7, 15, 23, 59, 59)
    entry = _entry(deadline=dt)
    result = compute_visibility(entry, TODAY)

    assert result["deadline"] is not None
    _, to_date = result["deadline"]
    assert to_date == datetime.date(2026, 7, 15)
    assert type(to_date) is datetime.date


def test_today_as_datetime_is_accepted():
    """compute_visibility should not raise when today is a datetime."""
    dt_today = datetime.datetime(2026, 4, 20, 12, 0, 0)
    entry = _entry(deadline=datetime.date(2026, 7, 15))
    # Should not raise.
    result = compute_visibility(entry, dt_today)
    assert result["deadline"] is not None


# ---------------------------------------------------------------------------
# Custom window_days
# ---------------------------------------------------------------------------


def test_custom_window_days_reflected_in_deadline_window():
    deadline = datetime.date(2026, 7, 15)
    entry = _entry(deadline=deadline)
    result = compute_visibility(entry, TODAY, window_days=7)

    assert _window_size(result["deadline"]) == 7


def test_custom_window_days_reflected_in_happening_window():
    start = datetime.date(2026, 8, 1)
    entry = _entry(start=start)
    result = compute_visibility(entry, TODAY, window_days=7)

    assert _window_size(result["happening"]) == 7


def test_custom_window_days_from_date_correct():
    deadline = datetime.date(2026, 7, 15)
    entry = _entry(deadline=deadline)
    result = compute_visibility(entry, TODAY, window_days=7)

    from_date, _ = result["deadline"]
    assert from_date == deadline - datetime.timedelta(days=7)
