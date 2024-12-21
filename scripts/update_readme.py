import yaml
import re
from dateutil.parser import parse  # pip install python-dateutil

SUMMERSCHOOLS_YML_PATH = "site/_data/summerschools.yml"
TYPES_YML_PATH = "site/_data/types.yml"
README_PATH = "README.md"


def parse_summerschools():
    """Load all summer schools from the YAML file."""
    with open(SUMMERSCHOOLS_YML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def parse_types():
    """
    Load the short-code to name mappings from site/_data/types.yml.
    """
    with open(TYPES_YML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    sub_map = {}
    for item in data:
        sub_code = item.get("sub")
        name = item.get("name", "")
        if sub_code:
            sub_map[sub_code] = name

    return sub_map


def sort_summerschools_for_year(summerschools, year=2025):
    """
    Filter out just the summerschools for the given year, then sort them:
      1) Descending by start date
      2) If start is the same, descending by end date as well (or adjust as needed).
    """
    filtered = [s for s in summerschools if s.get("year") == year]

    # Sort: latest (largest) start first, then largest end among ties
    sorted_filtered = sorted(
        filtered,
        key=lambda x: (x.get("start", ""), x.get("end", "")),
        reverse=True
    )
    return sorted_filtered


def format_date_abbr(date_str):
    """
    Parse a date string and return an abbreviated string, e.g. "Jan 09, 2025".
    If parsing fails, return the original string.
    """
    try:
        dt = parse(date_str)
        return dt.strftime("%b %d, %Y")  # e.g. "Jan 09, 2025"
    except Exception:
        return date_str  # fallback


def format_date_range_abbr(start_str, end_str):
    """
    Given two ISO-like date strings:
      - start_str -> displayed as "Jan 09"
      - end_str   -> displayed as "Jan 13, 2025"
    So the final combined string is "Jan 09 - Jan 13, 2025".

    If parsing fails, returns raw strings joined by a hyphen.
    """
    try:
        # e.g., "Jan 09"
        start_fmt = start_str.strftime("%b %d")
        # e.g., "Jan 13, 2025"
        end_fmt   = end_str.strftime("%b %d, %Y")

        return f"{start_fmt} - {end_fmt}"
    except Exception:
        return f"{start_str} - {end_str}"


def generate_markdown_table(summerschools, types_map, year=2025):
    """
    Creates a Markdown table for a specific year, with columns:
      Title | Topics | Place | Deadline | Dates | Details

    - 'Topics' is populated by looking up each code in 'sub' from the types_map dictionary.
    - 'Deadline' is parsed and abbreviated (e.g., "Mar 23, 2025").
    - 'Dates' is start-end in the format "Jan 09 - Jan 13, 2025".
    - The Details column links to https://awesome-mlss.com/summerschool/{id}.
    """
    filtered_sorted = sort_summerschools_for_year(summerschools, year=year)

    # Table header
    md_lines = [
        "Title|Topics|Place|Deadline|Dates|Details",
        "-----|------|-----|--------|-----|-------"
    ]

    for sch in filtered_sorted:
        title = sch.get("title", "")
        place = sch.get("place", "")

        # Format deadline
        deadline_raw = sch.get("deadline", "")
        deadline_str = format_date_abbr(deadline_raw)  # e.g. "Mar 23, 2025"

        # Format start/end
        start_raw = sch.get("start", "")
        end_raw   = sch.get("end", "")
        dates_str = format_date_range_abbr(start_raw, end_raw)
        # e.g. "Jan 09 - Jan 13, 2025"

        # Topics
        sub_codes = sch.get("sub", [])
        topics_list = [types_map.get(code, code) for code in sub_codes]
        topics_str = ", ".join(topics_list)

        # Details link
        school_id = sch.get("id", "")
        details_link = f"https://awesome-mlss.com/summerschool/{school_id}"

        # Build row
        line = f"{title}|{topics_str}|{place}|{deadline_str}|{dates_str}|[Details]({details_link})"
        md_lines.append(line)

    return "\n".join(md_lines)


def replace_section_in_readme(readme_text, new_markdown, year=2025):
    """
    Finds a section in the README that starts with '## {year} Summer Schools'
    and updates everything until the next '## ' or end of file.
    """
    pattern = re.compile(
        rf"(##\s+{year} Summer Schools)(.*?)(?=##\s|\Z)",
        re.DOTALL
    )
    new_section = f"## {year} Summer Schools\n{new_markdown}\n\n"
    updated_readme = re.sub(pattern, new_section, readme_text)
    return updated_readme


def main():
    # 1. Parse all summer schools
    summerschools = parse_summerschools()

    # 2. Parse topic codes
    types_map = parse_types()

    # 3. Generate the new table
    new_markdown_table = generate_markdown_table(summerschools, types_map, year=2025)

    # 4. Load existing README
    with open(README_PATH, "r", encoding="utf-8") as f:
        readme_text = f.read()

    # 5. Replace old section with new table
    updated_readme = replace_section_in_readme(readme_text, new_markdown_table, 2025)

    # 6. Overwrite if there's a change
    if updated_readme != readme_text:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated_readme)
        print("README.md updated successfully.")
    else:
        print("No changes to README.md.")


if __name__ == "__main__":
    main()
