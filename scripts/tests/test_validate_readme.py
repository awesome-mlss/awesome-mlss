"""Tests for ``scripts/validate_readme.py``.

The validator is the source of truth for PR status checks. These tests cover
the headline failure modes listed in the task spec:

* Missing required field on an entry
* Duplicate ``id``
* Malformed YAML
* Mismatched column counts in the UPCOMING README tables
* Happy path on complete, valid fixtures

Plus an integration check that runs the validator against the real repo data
to catch regressions in the renderer / YAML state of the repo itself.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import validate_readme
from scripts.validate_readme import (
    ValidationError,
    check_required_fields,
    check_table_column_counts,
    check_unique_ids,
    validate,
)


FIXTURES = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[2]


VALID_TYPES_YML = """---
- color: '#ffd300'
  name: Machine Learning
  sub: ML
- color: '#ff0000'
  name: Generative AI
  sub: GenAI
- color: '#deff0a'
  name: Computer Vision
  sub: CV
"""


README_WITH_GOOD_TABLES = """# Header

<!-- UPCOMING:START -->
## Upcoming Summer Schools

### Deadlines Soon

Title|Topics|Place|Deadline|Dates|Details
-----|------|-----|--------|-----|-------
Alpha|ML|Paris|Apr 22|Jun 1-5|[d](x)
Beta|CV|Rome|Apr 28|Apr 30 - May 10|[d](x)

### Happening Soon

*No schools currently match this window.*
<!-- UPCOMING:END -->
"""


README_MISMATCH_COLUMNS = """# Header

<!-- UPCOMING:START -->
## Upcoming Summer Schools

Title|Topics|Place|Deadline|Dates|Details
-----|------|-----|--------|-----|-------
Alpha|ML|Paris|Apr 22|Jun 1-5|[d](x)
Beta|CV|Rome|Apr 28
<!-- UPCOMING:END -->
"""


def _stage_repo(tmp_path: Path, schools_fixture: Path, readme_text: str) -> Path:
    """Build a minimal repo layout under ``tmp_path`` suitable for validate().

    Copies the real ``update_readme.py`` + fixture schools/types so the
    renderer step can actually run, and writes a provided README.md.
    """
    (tmp_path / "scripts").mkdir()
    (tmp_path / "site" / "_data").mkdir(parents=True)

    shutil.copy2(REPO_ROOT / "scripts" / "update_readme.py",
                 tmp_path / "scripts" / "update_readme.py")
    (tmp_path / "scripts" / "__init__.py").write_text("", encoding="utf-8")

    shutil.copy2(schools_fixture,
                 tmp_path / "site" / "_data" / "summerschools.yml")
    (tmp_path / "site" / "_data" / "types.yml").write_text(
        VALID_TYPES_YML, encoding="utf-8"
    )
    (tmp_path / "README.md").write_text(readme_text, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Unit tests for individual check functions
# ---------------------------------------------------------------------------


def test_check_required_fields_passes_on_complete_entry():
    entry = {
        "title": "x", "year": 2026, "id": "x26", "full_name": "X",
        "link": "https://x", "deadline": "2026-01-01",
        "timezone": "UTC", "place": "Earth", "date": "Jan 1",
        "start": "2026-01-01", "end": "2026-01-02", "sub": ["ML"],
    }
    check_required_fields([entry])


def test_check_required_fields_fails_on_missing_field():
    entry = {"title": "x", "id": "x26"}  # many missing
    with pytest.raises(ValidationError, match="missing required field"):
        check_required_fields([entry])


def test_check_required_fields_names_offending_entry():
    entry = {"title": "x", "id": "my_school_id"}
    with pytest.raises(ValidationError, match="my_school_id"):
        check_required_fields([entry])


def test_check_unique_ids_passes_on_unique():
    entries = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    check_unique_ids(entries)


def test_check_unique_ids_fails_on_duplicate():
    entries = [{"id": "a"}, {"id": "b"}, {"id": "a"}]
    with pytest.raises(ValidationError, match="Duplicate id"):
        check_unique_ids(entries)


def test_check_unique_ids_message_includes_dup_id():
    entries = [{"id": "school_x"}, {"id": "school_x"}]
    with pytest.raises(ValidationError, match="school_x"):
        check_unique_ids(entries)


def test_check_table_column_counts_passes_on_valid():
    # Should not raise.
    check_table_column_counts(README_WITH_GOOD_TABLES)


def test_check_table_column_counts_fails_on_mismatch():
    with pytest.raises(ValidationError, match="columns"):
        check_table_column_counts(README_MISMATCH_COLUMNS)


def test_check_table_column_counts_fails_without_start_marker():
    bad = "no markers here\n"
    with pytest.raises(ValidationError, match="start marker"):
        check_table_column_counts(bad)


def test_check_table_column_counts_fails_without_end_marker():
    bad = "<!-- UPCOMING:START -->\nstuff\n"
    with pytest.raises(ValidationError, match="end marker"):
        check_table_column_counts(bad)


# ---------------------------------------------------------------------------
# End-to-end validate() with staged repo
# ---------------------------------------------------------------------------


def test_validate_happy_path_passes_on_good_fixture(tmp_path):
    root = _stage_repo(
        tmp_path,
        FIXTURES / "validate_schools_good.yml",
        README_WITH_GOOD_TABLES,
    )
    # Should not raise.
    validate(repo_root=root)


def test_validate_fails_on_missing_required_field(tmp_path):
    root = _stage_repo(
        tmp_path,
        FIXTURES / "validate_schools_missing_field.yml",
        README_WITH_GOOD_TABLES,
    )
    with pytest.raises(ValidationError, match="missing required field"):
        validate(repo_root=root)


def test_validate_fails_on_duplicate_id(tmp_path):
    root = _stage_repo(
        tmp_path,
        FIXTURES / "validate_schools_duplicate_id.yml",
        README_WITH_GOOD_TABLES,
    )
    with pytest.raises(ValidationError, match="Duplicate id"):
        validate(repo_root=root)


def test_validate_fails_on_malformed_yaml(tmp_path):
    root = _stage_repo(
        tmp_path,
        FIXTURES / "validate_schools_malformed.yml",
        README_WITH_GOOD_TABLES,
    )
    with pytest.raises(ValidationError, match="malformed YAML"):
        validate(repo_root=root)


def test_validate_fails_on_mismatched_table_columns(tmp_path):
    # Use `run_render=False` so the renderer doesn't overwrite our deliberately
    # broken README before check_table_column_counts reads it.
    root = _stage_repo(
        tmp_path,
        FIXTURES / "validate_schools_good.yml",
        README_MISMATCH_COLUMNS,
    )
    with pytest.raises(ValidationError, match="columns"):
        validate(repo_root=root, run_render=False)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def test_main_returns_zero_on_good_fixture(tmp_path, monkeypatch):
    root = _stage_repo(
        tmp_path,
        FIXTURES / "validate_schools_good.yml",
        README_WITH_GOOD_TABLES,
    )
    monkeypatch.chdir(root)
    assert validate_readme.main() == 0


def test_main_returns_one_and_prints_error_on_duplicate_id(
    tmp_path, monkeypatch, capsys
):
    root = _stage_repo(
        tmp_path,
        FIXTURES / "validate_schools_duplicate_id.yml",
        README_WITH_GOOD_TABLES,
    )
    monkeypatch.chdir(root)
    assert validate_readme.main() == 1
    captured = capsys.readouterr()
    assert "Duplicate id" in captured.err


# ---------------------------------------------------------------------------
# Real-data integration: catches regressions in the repo itself.
# ---------------------------------------------------------------------------


def test_validate_real_repo_data_passes():
    validate(repo_root=REPO_ROOT)


def test_real_repo_yaml_parses_and_renderer_works():
    """Weaker real-repo test: YAML parses + renderer exits 0.

    Guards against breaking the renderer even while the missing-`date` bug
    makes the strict validate() xfail.
    """
    # Parse both YAML files.
    import yaml as _yaml  # local alias to avoid top-level import noise
    schools = _yaml.safe_load(
        (REPO_ROOT / "site" / "_data" / "summerschools.yml").read_text(
            encoding="utf-8"
        )
    )
    types = _yaml.safe_load(
        (REPO_ROOT / "site" / "_data" / "types.yml").read_text(encoding="utf-8")
    )
    assert isinstance(schools, list) and schools
    assert isinstance(types, list) and types

    # ids are unique even if some entries are incomplete.
    ids = [s.get("id") for s in schools if s.get("id")]
    assert len(ids) == len(set(ids)), "id uniqueness regressed"

    # Renderer exits 0 against real data.
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "update_readme.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"renderer failed: stdout={completed.stdout} stderr={completed.stderr}"
    )
