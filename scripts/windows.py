"""Compute README visibility windows for a summer-school entry.

Used by ``scripts/pr_preview.py`` to tell a contributor when their entry will
appear in the rolling "Deadlines Soon" and "Happening Soon" tables in README.md.
"""

from __future__ import annotations

import datetime
from typing import Optional, Tuple

from dateutil.parser import parse as _dateutil_parse


# ---------------------------------------------------------------------------
# Date coercion (intentional copy from update_readme.py — keeps this module
# standalone so it can be imported without pulling in the full update script)
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
# Public interface
# ---------------------------------------------------------------------------

WindowResult = Optional[Tuple[datetime.date, datetime.date]]


def compute_visibility(
    entry: dict,
    today,
    window_days: int = 14,
) -> dict:
    """Return the windows during which *entry* will appear in the README tables.

    Args:
        entry:       A school dict parsed from ``summerschools.yml``.
        today:       Reference date (``datetime.date`` or ``datetime.datetime``).
        window_days: Size of each rolling window (default 14).

    Returns:
        A dict with two keys:

        ``"deadline"``
            ``(from_date, to_date)`` where ``to_date`` is the parsed deadline
            and ``from_date`` is ``deadline - window_days``.  ``None`` when the
            deadline field is absent or unparseable.

        ``"happening"``
            ``(from_date, to_date)`` where ``to_date`` is the parsed start date
            and ``from_date`` is ``start - window_days``.  ``None`` when the
            start field is absent or unparseable.

    Both ``from_date`` and ``to_date`` are ``datetime.date`` objects.
    """
    # Coerce today to a plain date so callers may pass datetime objects.
    if isinstance(today, datetime.datetime):
        today = today.date()

    delta = datetime.timedelta(days=window_days)

    deadline_date = _coerce_to_date(entry.get("deadline"))
    if deadline_date is not None:
        deadline_window: WindowResult = (deadline_date - delta, deadline_date)
    else:
        deadline_window = None

    start_date = _coerce_to_date(entry.get("start"))
    if start_date is not None:
        happening_window: WindowResult = (start_date - delta, start_date)
    else:
        happening_window = None

    return {
        "deadline": deadline_window,
        "happening": happening_window,
    }
