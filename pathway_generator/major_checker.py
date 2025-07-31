#!/usr/bin/env python3
"""
major_checker.py

Extracts all community college courses that articulate to the specified
UC Computer Science major requirements.

Example usage:
    from pathlib import Path
    from major_checker import get_required_cc_courses

    courses = get_required_cc_courses(
        cc_name="Palomar_College",
        selected_ucs=["UCLA", "UCSD"],
        articulation_dir=Path("articulated_courses_json")
    )
    # courses is a sorted list of unique CCC course codes that map to those UCs
"""
import json
from pathlib import Path
from typing import List, Set, Dict, Any


def load_json(path: Path) -> Dict[str, Any]:
    """Load JSON data from the specified file path."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_required_cc_courses(
    cc_name: str,
    selected_ucs: List[str],
    articulation_dir: Path
) -> List[str]:
    """
    Load the CC articulation file and collect all courses that articulate
    to the given UC campuses' CS Major requirements.

    Args:
        cc_name: Name prefix of the CC articulation file (e.g. "Palomar_College").
        selected_ucs: List of UC campus codes to extract courses for.
        articulation_dir: Directory containing <cc_name>_articulation.json.

    Returns:
        Sorted, deduplicated list of course codes from 'receiving_course(s)'.
    """
    file_path = articulation_dir / f"{cc_name}_articulation.json"
    data = load_json(file_path)
    cc_data = data.get(cc_name, {})

    courses: Set[str] = set()
    for uc in selected_ucs:
        uc_map = cc_data.get(uc, {})
        for entry in uc_map.values():
            rec = entry.get('receiving_course') or entry.get('receiving_courses')
            if not rec:
                continue
            if isinstance(rec, str):
                courses.add(rec)
            elif isinstance(rec, list):
                courses.update(rec)
    return sorted(courses)
