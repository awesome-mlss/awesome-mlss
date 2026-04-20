"""Validate that summerschools.yml + types.yml + the renderer are in a good state.

This script is invoked by the ``validate-readme`` GitHub Actions workflow as a
required status check on every PR targeting master. It performs the following
checks and exits non-zero on the first failure, with a clear error printed to
stderr:

1. ``site/_data/summerschools.yml`` parses as a list of dicts.
2. ``site/_data/types.yml`` parses as a list of dicts.
3. Every school entry has the required fields present (presence only).
4. All ``id`` values in ``summerschools.yml`` are unique.
5. Running ``scripts/update_readme.py`` exits 0.
6. Every markdown table between ``<!-- UPCOMING:START -->`` and
   ``<!-- UPCOMING:END -->`` in the resulting ``README.md`` has consistent
   column counts (header, separator, and each data row all share the same
   number of ``|``-separated cells).

The script is intended to be robust enough to run both locally (from the repo
root) and in CI. It exits 0 silently on success.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence

import yaml


REQUIRED_SCHOOL_FIELDS: Sequence[str] = (
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
)

DEFAULT_SUMMERSCHOOLS_PATH = "site/_data/summerschools.yml"
DEFAULT_TYPES_PATH = "site/_data/types.yml"
DEFAULT_README_PATH = "README.md"
DEFAULT_RENDER_SCRIPT = "scripts/update_readme.py"

START_MARKER = "<!-- UPCOMING:START -->"
END_MARKER = "<!-- UPCOMING:END -->"


class ValidationError(Exception):
    """Raised when a validation rule fails."""


# ---------------------------------------------------------------------------
# Individual check functions (pure-ish; they read files but don't mutate them)
# ---------------------------------------------------------------------------


def _load_yaml_list(path: Path, label: str) -> List[dict]:
    """Load ``path`` as YAML and assert the top-level shape is a list of dicts."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationError(f"{label}: file not found at {path}") from exc

    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValidationError(f"{label}: malformed YAML in {path}: {exc}") from exc

    if parsed is None:
        return []
    if not isinstance(parsed, list):
        raise ValidationError(
            f"{label}: expected a YAML list at the top level of {path}, "
            f"got {type(parsed).__name__}"
        )
    for idx, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise ValidationError(
                f"{label}: entry at index {idx} in {path} is not a mapping "
                f"(got {type(item).__name__})"
            )
    return parsed


def check_required_fields(schools: Sequence[dict]) -> None:
    """Every school entry must have the required fields (presence only)."""
    for idx, school in enumerate(schools):
        missing = [f for f in REQUIRED_SCHOOL_FIELDS if f not in school]
        if missing:
            identifier = school.get("id") or school.get("title") or f"index {idx}"
            raise ValidationError(
                f"Entry `{identifier}` is missing required field(s): "
                f"{', '.join(missing)}"
            )


def check_unique_ids(schools: Sequence[dict]) -> None:
    """All ``id`` values must be unique across the school list."""
    seen: dict = {}
    duplicates: List[str] = []
    for school in schools:
        entry_id = school.get("id")
        if entry_id is None:
            # Presence is enforced separately; skip here to avoid double-reporting.
            continue
        if entry_id in seen:
            duplicates.append(str(entry_id))
        else:
            seen[entry_id] = True
    if duplicates:
        # Preserve order but dedupe for the message.
        seen_in_msg: set = set()
        unique_dupes: List[str] = []
        for d in duplicates:
            if d not in seen_in_msg:
                seen_in_msg.add(d)
                unique_dupes.append(d)
        raise ValidationError(
            f"Duplicate id(s) in summerschools.yml: {', '.join(unique_dupes)}"
        )


def run_renderer(script_path: Path, cwd: Path) -> None:
    """Invoke ``scripts/update_readme.py``; fail if it exits non-zero."""
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        raise ValidationError(
            f"Renderer `{script_path}` exited with code "
            f"{completed.returncode}.\nstdout:\n{stdout}\nstderr:\n{stderr}"
        )


def _extract_upcoming_region(readme_text: str) -> str:
    """Return the text between START_MARKER and END_MARKER (exclusive)."""
    lines = readme_text.splitlines()
    try:
        start_idx = next(
            i for i, line in enumerate(lines) if line.strip() == START_MARKER
        )
    except StopIteration as exc:
        raise ValidationError(
            f"README: missing start marker {START_MARKER}"
        ) from exc
    try:
        end_idx = next(
            i
            for i, line in enumerate(lines)
            if line.strip() == END_MARKER and i > start_idx
        )
    except StopIteration as exc:
        raise ValidationError(
            f"README: missing end marker {END_MARKER} after start marker"
        ) from exc
    return "\n".join(lines[start_idx + 1 : end_idx])


def _count_cells(row: str) -> int:
    """Count ``|``-separated cells in a markdown table row.

    A leading/trailing ``|`` (common in some table styles) is tolerated by
    stripping surrounding pipes first. Cell count then equals ``len(split)``.
    """
    stripped = row.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return len(stripped.split("|"))


def _is_separator_row(row: str) -> bool:
    """Is this the `---|---` separator line of a markdown table?"""
    stripped = row.strip()
    if not stripped:
        return False
    # Tolerate leading/trailing pipe.
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    cells = stripped.split("|")
    if not cells:
        return False
    for cell in cells:
        c = cell.strip()
        if not c:
            return False
        # allow leading/trailing colons for alignment (:---, ---:, :---:)
        if c.startswith(":"):
            c = c[1:]
        if c.endswith(":"):
            c = c[:-1]
        if not c or set(c) != {"-"}:
            return False
    return True


def _looks_like_table_row(row: str) -> bool:
    """Heuristic: any non-empty line containing a ``|`` is part of a table."""
    return "|" in row and bool(row.strip())


def check_table_column_counts(readme_text: str) -> None:
    """Walk tables in the UPCOMING region; error on mismatched column counts."""
    region = _extract_upcoming_region(readme_text)
    lines = region.splitlines()

    i = 0
    table_num = 0
    while i < len(lines):
        line = lines[i]
        # A table starts on a line with `|`, where the NEXT non-empty line is
        # a separator row.
        if _looks_like_table_row(line):
            # Look for separator on the immediate next line.
            if i + 1 < len(lines) and _is_separator_row(lines[i + 1]):
                table_num += 1
                header_cells = _count_cells(line)
                separator_cells = _count_cells(lines[i + 1])
                if separator_cells != header_cells:
                    raise ValidationError(
                        f"README table #{table_num}: separator row has "
                        f"{separator_cells} columns but header has "
                        f"{header_cells}"
                    )
                # Walk rows until a non-table line or blank line.
                j = i + 2
                row_num = 0
                while j < len(lines) and _looks_like_table_row(lines[j]):
                    row_num += 1
                    row_cells = _count_cells(lines[j])
                    if row_cells != header_cells:
                        raise ValidationError(
                            f"README table #{table_num}, row {row_num}: has "
                            f"{row_cells} columns but header has "
                            f"{header_cells}"
                        )
                    j += 1
                i = j
                continue
        i += 1


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def validate(
    repo_root: Optional[Path] = None,
    *,
    run_render: bool = True,
) -> None:
    """Run all checks; raise ``ValidationError`` on the first failure.

    Parameters
    ----------
    repo_root:
        Directory containing ``site/_data/summerschools.yml`` et al. Defaults
        to the current working directory.
    run_render:
        Whether to invoke ``scripts/update_readme.py`` via subprocess. Tests
        keep this ``True`` on the happy path (real data) but the check is a
        no-op friendly boundary if a caller wants to skip it.
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()

    summerschools_path = root / DEFAULT_SUMMERSCHOOLS_PATH
    types_path = root / DEFAULT_TYPES_PATH
    readme_path = root / DEFAULT_README_PATH
    render_script = root / DEFAULT_RENDER_SCRIPT

    schools = _load_yaml_list(summerschools_path, "summerschools.yml")
    _load_yaml_list(types_path, "types.yml")

    check_required_fields(schools)
    check_unique_ids(schools)

    if run_render:
        run_renderer(render_script, cwd=root)

    try:
        readme_text = readme_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationError(
            f"README.md not found at {readme_path}"
        ) from exc
    check_table_column_counts(readme_text)


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        validate()
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
