# major_checker.py
#!/usr/bin/env python3
"""
major_checker.py

Utilities for reading articulation data and mapping
community college courses to UC Computer Science major requirements,
with full support for nested AND/OR logic in articulation JSON.
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
    path = articulation_dir / f"{cc_name}_articulation.json"
    data = load_json(path).get(cc_name, {})
    courses: Set[str] = set()
    for uc in selected_ucs:
        for entry in data.get(uc, {}).values():
            for group in entry.get('course_groups', []):
                for course_obj in group:
                    courses.add(course_obj['course'])
    return sorted(courses)


def build_uc_block_map(
    cc_name: str,
    selected_ucs: List[str],
    articulation_dir: Path
) -> Dict[Tuple[str, str], List[List[str]]]:
    """
    Map each (uc, receiving_course) to a list of sending-course blocks:
      - OR-level: choose one block
      - AND-level: take all courses within a block
    """
    path = articulation_dir / f"{cc_name}_articulation.json"
    data = load_json(path).get(cc_name, {})
    block_map: Dict[Tuple[str, str], List[List[str]]] = {}

    for uc in selected_ucs:
        for entry in data.get(uc, {}).values():
            recs = []
            if 'receiving_course' in entry:
                recs = [entry['receiving_course']]
            elif 'receiving_courses' in entry:
                recs = entry['receiving_courses']
            # extract each block (AND within)
            blocks: List[List[str]] = []
            for group in entry.get('course_groups', []):
                block = [course_obj['course'] for course_obj in group]
                blocks.append(block)
            for r in recs:
                block_map.setdefault((uc, r), []).extend(blocks)
    return block_map


def build_uc_group_block_map(
    cc_name: str,
    selected_ucs: List[str],
    articulation_dir: Path,
    course_reqs_path: Path
) -> Dict[Tuple[str, str], List[List[str]]]:
    """
    Map each (uc, group_name) to all CC blocks satisfying that group.
    """
    block_map = build_uc_block_map(cc_name, selected_ucs, articulation_dir)
    group_defs = load_uc_requirement_groups(course_reqs_path, selected_ucs)
    group_block_map: Dict[Tuple[str, str], List[List[str]]] = {}

    for uc, groups in group_defs.items():
        for grp, meta in groups.items():
            all_blocks: List[List[str]] = []
            for uc_course in meta['courses']:
                for block in block_map.get((uc, uc_course), []):
                    all_blocks.append(block)
            group_block_map[(uc, grp)] = all_blocks
    return group_block_map