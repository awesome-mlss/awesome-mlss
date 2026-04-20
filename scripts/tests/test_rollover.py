"""Tests for ``scripts/rollover_year.py``.

The tests copy the fixture YAML files to a ``tmp_path`` per-test so that the
fixtures on disk are never mutated.
"""

from __future__ import annotations

import datetime
import shutil
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from scripts.rollover_year import main, rollover

FIXTURES = Path(__file__).parent / "fixtures"
LIVE_FIXTURE = FIXTURES / "rollover_live.yml"
ARCHIVE_FIXTURE = FIXTURES / "rollover_archive.yml"


def _copy_fixtures(tmp_path: Path):
    live = tmp_path / "summerschools.yml"
    archive = tmp_path / "archive.yml"
    shutil.copy2(LIVE_FIXTURE, live)
    shutil.copy2(ARCHIVE_FIXTURE, archive)
    return live, archive


def _load_yaml(path: Path):
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f)


def _ids(entries) -> list[str]:
    return [str(e.get("id")) for e in (entries or [])]


# ---------------------------------------------------------------------------
# (1) Basic rollover: past moves, future stays, missing/unparseable skipped.
# ---------------------------------------------------------------------------


def test_rollover_moves_past_and_skips_bad_dates(tmp_path):
    live, archive = _copy_fixtures(tmp_path)
    cutoff = datetime.date(2026, 1, 1)

    moved, skipped = rollover(live, archive, cutoff=cutoff, dry_run=False)

    moved_ids = _ids(moved)
    assert moved_ids == ["past_alpha25"]

    live_after = _load_yaml(live)
    archive_after = _load_yaml(archive)

    assert "past_alpha25" not in _ids(live_after)
    assert "future_beta26" in _ids(live_after)
    assert "missing_gamma25" in _ids(live_after)
    assert "unparseable_delta25" in _ids(live_after)
    assert "boundary_epsilon26" in _ids(live_after)

    # Appended to archive in live-file order after the existing entry.
    assert _ids(archive_after) == ["existing_archive20", "past_alpha25"]

    # Two skipped (missing + unparseable).
    skipped_ids = sorted(entry_id for entry_id, _ in skipped)
    assert skipped_ids == ["missing_gamma25", "unparseable_delta25"]

    # Reasons distinguish missing vs unparseable.
    reasons = dict(skipped)
    assert "missing" in reasons["missing_gamma25"].lower()
    assert "unparseable" in reasons["unparseable_delta25"].lower()


# ---------------------------------------------------------------------------
# (2) Dry-run leaves files byte-identical but reports what would move.
# ---------------------------------------------------------------------------


def test_dry_run_does_not_modify_files(tmp_path):
    live, archive = _copy_fixtures(tmp_path)
    before_live = live.read_bytes()
    before_archive = archive.read_bytes()

    moved, skipped = rollover(
        live, archive, cutoff=datetime.date(2026, 1, 1), dry_run=True
    )

    assert live.read_bytes() == before_live
    assert archive.read_bytes() == before_archive

    assert _ids(moved) == ["past_alpha25"]
    # Skipped entries are reported in dry-run too.
    assert {entry_id for entry_id, _ in skipped} == {
        "missing_gamma25",
        "unparseable_delta25",
    }


# ---------------------------------------------------------------------------
# (3) Comment preservation in the live file.
# ---------------------------------------------------------------------------


def test_top_comment_preserved_after_rollover(tmp_path):
    live, archive = _copy_fixtures(tmp_path)
    rollover(live, archive, cutoff=datetime.date(2026, 1, 1), dry_run=False)

    text = live.read_text(encoding="utf-8")
    # The fixture's header comment must still be in the live file.
    assert "# Fixture: live summerschools data" in text


# ---------------------------------------------------------------------------
# (4) Key-order preservation on an entry that was NOT moved.
# ---------------------------------------------------------------------------


def test_key_order_preserved_for_kept_entry(tmp_path):
    live, archive = _copy_fixtures(tmp_path)
    rollover(live, archive, cutoff=datetime.date(2026, 1, 1), dry_run=False)

    live_after = _load_yaml(live)
    # Find the future_beta26 entry.
    kept = next(e for e in live_after if e.get("id") == "future_beta26")
    expected_order = [
        "title",
        "year",
        "id",
        "full_name",
        "link",
        "deadline",
        "timezone",
        "place",
        "date",
        "start",
        "end",
        "sub",
    ]
    assert list(kept.keys()) == expected_order


# ---------------------------------------------------------------------------
# (5) Cutoff boundary: end == cutoff → NOT moved.
# ---------------------------------------------------------------------------


def test_cutoff_boundary_inclusive_stay(tmp_path):
    live, archive = _copy_fixtures(tmp_path)
    # boundary_epsilon26 ends 2026-01-15.
    cutoff = datetime.date(2026, 1, 15)

    moved, _ = rollover(live, archive, cutoff=cutoff, dry_run=False)

    moved_ids = _ids(moved)
    assert "boundary_epsilon26" not in moved_ids
    # past_alpha25 (end 2025-07-05) is still before cutoff → moved.
    assert "past_alpha25" in moved_ids

    live_after = _load_yaml(live)
    assert "boundary_epsilon26" in _ids(live_after)


# ---------------------------------------------------------------------------
# (6) Cutoff boundary: end == cutoff - 1 day → moved.
# ---------------------------------------------------------------------------


def test_cutoff_boundary_day_before_is_moved(tmp_path):
    live, archive = _copy_fixtures(tmp_path)
    # boundary_epsilon26 ends 2026-01-15 → cutoff 2026-01-16 should move it.
    cutoff = datetime.date(2026, 1, 16)

    moved, _ = rollover(live, archive, cutoff=cutoff, dry_run=False)

    assert "boundary_epsilon26" in _ids(moved)
    archive_after = _load_yaml(archive)
    assert "boundary_epsilon26" in _ids(archive_after)


# ---------------------------------------------------------------------------
# (7) --cutoff CLI arg is parsed correctly.
# ---------------------------------------------------------------------------


def test_cli_cutoff_argument(tmp_path, capsys):
    live, archive = _copy_fixtures(tmp_path)

    rc = main(
        [
            "--cutoff",
            "2026-01-01",
            "--live",
            str(live),
            "--archive",
            str(archive),
        ]
    )

    assert rc == 0

    out = capsys.readouterr().out
    # Only past_alpha25 should move at this cutoff.
    assert "Moved 1 entries" in out
    assert "Skipped 2 entries" in out

    archive_after = _load_yaml(archive)
    assert "past_alpha25" in _ids(archive_after)


def test_cli_dry_run_prints_would_move(tmp_path, capsys):
    live, archive = _copy_fixtures(tmp_path)
    before_live = live.read_bytes()
    before_archive = archive.read_bytes()

    rc = main(
        [
            "--dry-run",
            "--cutoff",
            "2026-01-01",
            "--live",
            str(live),
            "--archive",
            str(archive),
        ]
    )

    assert rc == 0
    # Files untouched.
    assert live.read_bytes() == before_live
    assert archive.read_bytes() == before_archive

    out = capsys.readouterr().out
    assert "Would move 1 entries" in out
    assert "past_alpha25" in out


def test_cli_rejects_bad_cutoff_format(tmp_path):
    live, archive = _copy_fixtures(tmp_path)
    with pytest.raises(SystemExit):
        main(
            [
                "--cutoff",
                "2026/01/01",
                "--live",
                str(live),
                "--archive",
                str(archive),
            ]
        )


# ---------------------------------------------------------------------------
# (8) Empty archive: entries are appended correctly.
# ---------------------------------------------------------------------------


def test_empty_archive_with_only_comment(tmp_path):
    live, _ = _copy_fixtures(tmp_path)
    archive = tmp_path / "archive.yml"
    archive.write_text("# empty archive\n[]\n", encoding="utf-8")

    moved, _ = rollover(
        live, archive, cutoff=datetime.date(2026, 1, 1), dry_run=False
    )
    assert _ids(moved) == ["past_alpha25"]

    archive_after = _load_yaml(archive)
    assert _ids(archive_after) == ["past_alpha25"]


def test_archive_with_null_content(tmp_path):
    """Archive file that is effectively empty (header comment only, no list)."""
    live, _ = _copy_fixtures(tmp_path)
    archive = tmp_path / "archive.yml"
    archive.write_text("# Just a header, nothing else\n", encoding="utf-8")

    moved, _ = rollover(
        live, archive, cutoff=datetime.date(2026, 1, 1), dry_run=False
    )
    assert _ids(moved) == ["past_alpha25"]

    archive_after = _load_yaml(archive)
    assert _ids(archive_after) == ["past_alpha25"]


# ---------------------------------------------------------------------------
# Additional: no moves is a clean no-op.
# ---------------------------------------------------------------------------


def test_no_moves_when_all_entries_future(tmp_path):
    live, archive = _copy_fixtures(tmp_path)
    before_live = live.read_bytes()
    before_archive = archive.read_bytes()

    # Cutoff way in the past — nothing's end is before this.
    moved, _ = rollover(
        live, archive, cutoff=datetime.date(2000, 1, 1), dry_run=False
    )
    assert moved == []
    # Files should not have been written (rollover skips writes when nothing moved).
    assert live.read_bytes() == before_live
    assert archive.read_bytes() == before_archive
