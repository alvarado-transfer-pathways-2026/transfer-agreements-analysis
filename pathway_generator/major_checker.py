# major_checker.py
#!/usr/bin/env python3
"""
major_checker.py

Utilities for reading articulation data and mapping
community college courses to UC Computer Science major requirements,
with full support for AND/OR logic based on course_reqs.json.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_uc_requirement_groups(
    course_reqs_path: Path,
    selected_ucs: List[str]
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    data    = load_json(course_reqs_path)
    uc_reqs = data.get('UC_REQUIREMENTS', {})
    groups: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for uc in selected_ucs:
        raw = uc_reqs.get(uc, {})
        if not raw:
            continue
        groups[uc] = {}
        for group_name, options in raw.items():
            codes = [opt[0] for opt in options]
            num_req = options[0][2] if len(options[0]) >= 3 else len(codes)
            groups[uc][group_name] = {'courses': codes, 'num_required': num_req}
    return groups


def get_required_cc_courses(
    cc_name: str,
    selected_ucs: List[str],
    articulation_dir: Path
) -> List[str]:
    """
    Return flat list of CC courses from `course_groups` that articulate
    to any UC CS requirement.
    """
    path = articulation_dir / f"{cc_name}_articulation.json"
    data = load_json(path).get(cc_name, {})
    courses: Set[str] = set()
    for uc in selected_ucs:
        for entry in data.get(uc, {}).values():
            for group in entry.get('course_groups', []):
                for course_obj in group:
                    courses.add(course_obj['course'])
    return sorted(courses)


def build_uc_tuple_map(
    cc_name: str,
    selected_ucs: List[str],
    articulation_dir: Path
) -> Dict[Tuple[str, str], List[str]]:
    """
    Map each (UC, UC_course) to CC courses via `course_groups`.
    """
    path = articulation_dir / f"{cc_name}_articulation.json"
    data = load_json(path).get(cc_name, {})
    mapping: Dict[Tuple[str, str], List[str]] = {}
    for uc in selected_ucs:
        for entry in data.get(uc, {}).values():
            recs = []
            if 'receiving_course' in entry:
                recs = [entry['receiving_course']]
            elif 'receiving_courses' in entry:
                recs = entry['receiving_courses']
            sends: Set[str] = set()
            for group in entry.get('course_groups', []):
                for course_obj in group:
                    sends.add(course_obj['course'])
            for r in recs:
                mapping.setdefault((uc, r), []).extend(sorted(sends))
    # dedupe
    for k, v in mapping.items():
        mapping[k] = sorted(set(v))
    return mapping


def build_uc_group_map(
    cc_name: str,
    selected_ucs: List[str],
    articulation_dir: Path,
    course_reqs_path: Path
) -> Dict[Tuple[str, str], List[str]]:
    """
    Map each (UC, group_name) to all CC courses satisfying that group.
    """
    tuple_map = build_uc_tuple_map(cc_name, selected_ucs, articulation_dir)
    group_defs = load_uc_requirement_groups(course_reqs_path, selected_ucs)
    group_map: Dict[Tuple[str, str], List[str]] = {}
    for uc, groups in group_defs.items():
        for grp, meta in groups.items():
            sends: Set[str] = set()
            for uc_course in meta['courses']:
                sends.update(tuple_map.get((uc, uc_course), []))
            group_map[(uc, grp)] = sorted(sends)
    return group_map