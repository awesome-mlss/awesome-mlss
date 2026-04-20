"""Move past-year entries from summerschools.yml to archive.yml.

One-off-per-year migration script. A maintainer runs this once per year
(typically early January) after previous-year schools have ended and need to
move out of the live data file into the archive.

CLI::

    python scripts/rollover_year.py [--dry-run] [--cutoff YYYY-MM-DD]

- Default cutoff is ``datetime.date.today()``.
- Moves any entry whose ``end`` date is strictly before ``cutoff``
  (cutoff-day entries are NOT moved).
- Entries with missing or unparseable ``end`` are skipped (left in the live
  file) and listed as warnings in the summary. They are never moved silently.
- ``--dry-run`` prints which entries would move but touches no files.

Uses ``ruamel.yaml`` with its round-trip loader/dumper so that comments,
quoting, and key ordering survive the re-serialization. Some cosmetic drift
(trailing whitespace on blank lines, ``null`` vs empty scalar) is inherent to
ruamel.yaml and accepted — a maintainer reviews the diff before committing.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from dateutil.parser import parse as _dateutil_parse
from ruamel.yaml import YAML

LIVE_YML_PATH = "site/_data/summerschools.yml"
ARCHIVE_YML_PATH = "site/_data/archive.yml"


# ---------------------------------------------------------------------------
# ruamel.yaml setup
# ---------------------------------------------------------------------------


def _make_yaml() -> YAML:
    """Return a ``YAML`` configured for round-trip with this repo's style."""
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    # Do not reflow long single-line scalars.
    yaml.width = 10000
    # Top-level sequence entries in this repo sit flush-left (``- title:``),
    # so use sequence=2, offset=0 rather than the conventional sequence=4,
    # offset=2 which would shift every top-level ``-`` inward by 2 cols.
    yaml.indent(mapping=2, sequence=2, offset=0)
    return yaml


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------


def _coerce_to_date(value) -> Optional[datetime.date]:
    """Best-effort convert a YAML ``end`` value to ``datetime.date``.

    Returns ``None`` when missing or unparseable. Distinguishing "missing"
    from "unparseable" is done by the caller via the raw value.
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
# Core rollover
# ---------------------------------------------------------------------------


def rollover(
    live_path: Path,
    archive_path: Path,
    cutoff: datetime.date,
    dry_run: bool = False,
) -> Tuple[List[dict], List[Tuple[str, str]]]:
    """Move past-year entries from ``live_path`` to ``archive_path``.

    Parameters
    ----------
    live_path, archive_path:
        Paths to the YAML files. Both must exist and be valid YAML.
    cutoff:
        Entries whose ``end`` date is strictly before ``cutoff`` are moved.
        Entries with ``end == cutoff`` are kept.
    dry_run:
        When True, the files on disk are untouched. The returned ``moved``
        list still identifies which entries would move.

    Returns
    -------
    (moved, skipped_with_reasons)
        ``moved`` is the list of entries that were moved (or would be moved,
        in dry-run). ``skipped_with_reasons`` is a list of
        ``(entry_id, reason)`` tuples for entries whose ``end`` could not be
        parsed.
    """
    yaml = _make_yaml()

    with open(live_path, "r", encoding="utf-8") as f:
        live_data = yaml.load(f)
    with open(archive_path, "r", encoding="utf-8") as f:
        archive_data = yaml.load(f)

    # ``archive.yml`` may be empty or contain only comments. Treat None as [].
    if live_data is None:
        live_data = []
    if archive_data is None:
        archive_data = []

    kept: List[dict] = []
    moved: List[dict] = []
    skipped: List[Tuple[str, str]] = []

    for entry in live_data:
        entry_id = _entry_id_or_placeholder(entry)
        raw_end = entry.get("end") if hasattr(entry, "get") else None
        end_date = _coerce_to_date(raw_end)

        if end_date is None:
            if raw_end is None or (isinstance(raw_end, str) and not raw_end.strip()):
                skipped.append((entry_id, "missing end date"))
            else:
                skipped.append(
                    (entry_id, f"unparseable end date: {raw_end!r}")
                )
            kept.append(entry)
            continue

        if end_date < cutoff:
            moved.append(entry)
        else:
            kept.append(entry)

    if not dry_run and moved:
        # Preserve the ruamel-wrapped CommentedSeq types by mutating in place
        # so top-level comments / anchors on the sequences are preserved.
        live_data[:] = kept
        for entry in moved:
            archive_data.append(entry)

        with open(live_path, "w", encoding="utf-8") as f:
            yaml.dump(live_data, f)
        with open(archive_path, "w", encoding="utf-8") as f:
            yaml.dump(archive_data, f)

    return moved, skipped


def _entry_id_or_placeholder(entry) -> str:
    """Return ``entry['id']`` or a best-effort placeholder."""
    if hasattr(entry, "get"):
        val = entry.get("id")
        if val:
            return str(val)
        title = entry.get("title")
        if title:
            return f"<no id; title={title!r}>"
    return "<unknown entry>"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_cutoff(value: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"--cutoff must be YYYY-MM-DD (got {value!r}): {exc}"
        ) from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Move past-year entries from summerschools.yml to archive.yml. "
            "Entries whose end date is strictly before cutoff are moved; "
            "cutoff-day entries are kept."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print which entries would move but do not modify files.",
    )
    parser.add_argument(
        "--cutoff",
        type=_parse_cutoff,
        default=None,
        help="Cutoff date as YYYY-MM-DD (default: today).",
    )
    parser.add_argument(
        "--live",
        default=LIVE_YML_PATH,
        help=f"Path to live YAML (default: {LIVE_YML_PATH}).",
    )
    parser.add_argument(
        "--archive",
        default=ARCHIVE_YML_PATH,
        help=f"Path to archive YAML (default: {ARCHIVE_YML_PATH}).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    cutoff = args.cutoff if args.cutoff is not None else datetime.date.today()

    live_path = Path(args.live)
    archive_path = Path(args.archive)
    if not live_path.exists():
        print(f"ERROR: live file not found: {live_path}", file=sys.stderr)
        return 2
    if not archive_path.exists():
        print(f"ERROR: archive file not found: {archive_path}", file=sys.stderr)
        return 2

    moved, skipped = rollover(
        live_path=live_path,
        archive_path=archive_path,
        cutoff=cutoff,
        dry_run=args.dry_run,
    )

    verb = "Would move" if args.dry_run else "Moved"
    print(
        f"{verb} {len(moved)} entries. "
        f"Skipped {len(skipped)} entries with missing/unparseable end dates."
    )
    if args.dry_run and moved:
        print("Entries that would move:")
        for entry in moved:
            print(f"  - {_entry_id_or_placeholder(entry)}")
    if skipped:
        print("Skipped entries:")
        for entry_id, reason in skipped:
            print(f"  - {entry_id}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
