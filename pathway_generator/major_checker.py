#!/usr/bin/env python3
"""
major_checker.py

Utilities for reading articulation data and mapping
community college courses to UC Computer Science major requirements,
with full support for nested AND/OR logic in articulation JSON.

Includes:
- MajorRequirements interface (for unmet requirements)
- get_cc_to_uc_map (mapping of each UC campus to its receiving courses)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# ─── Low-Level JSON Loader ──────────────────────────────────────────────────

def load_json(path: Path) -> Dict[str, Any]:
    """Load a JSON file from disk."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# ─── MajorRequirements Interface ─────────────────────────────────────────────

class MajorRequirements:
    """
    Encapsulates UC CS major requirements for one CC→UC pairing.
    Provides a method to get remaining CC courses for unmet UC major groups.
    """

    def __init__(
        self,
        course_reqs_path: Path,
        cc_name: str,
        selected_ucs: List[str],
        articulation_dir: Path
    ):
        self.group_defs      = load_uc_requirement_groups(course_reqs_path, selected_ucs)
        self.group_block_map = build_uc_group_block_map(
            cc_name,
            selected_ucs,
            articulation_dir,
            course_reqs_path
        )

    def get_remaining_courses(
        self,
        completed: Set[str],
        articulated: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Return a list of candidate CC courses (with units & tags) for every UC-major
        group not yet fulfilled by `completed`.
        """
        remaining: List[Dict[str, Any]] = []

        for (uc, group), blocks in self.group_block_map.items():
            num_req = self.group_defs[uc][group]['num_required']
            satisfied = sum(
                1
                for block in blocks
                if any(course in completed for course in block)
            )
            if satisfied >= num_req:
                continue

            for block in blocks:
                if not any(course in completed for course in block):
                    for cc_course in block:
                        remaining.append({
                            "courseCode": cc_course,
                            "units": articulated.get(cc_course, {}).get("units", 3),
                            "tag": f"{uc}:{group}"
                        })
                    break

        return remaining


def get_major_requirements(
    course_reqs_path: str,
    cc_name: str,
    selected_ucs: List[str],
    articulation_dir: str
) -> MajorRequirements:
    return MajorRequirements(
        Path(course_reqs_path),
        cc_name,
        selected_ucs,
        Path(articulation_dir)
    )

# ─── CC→UC Mapping Utility ────────────────────────────────────────────────────

def get_cc_to_uc_map(
    cc_name: str,
    selected_ucs: List[str],
    articulation_dir: Path
) -> Dict[str, Dict[str, List[List[str]]]]:
    """
    Return a nested mapping of each UC to its receiving course codes,
    each mapping to a list of lists of CC courses that articulate into it.
    Each inner list represents an AND group, and the outer list is OR.

    Example:
      {
        "UCSD": {
          "CSE 8A": [["CISP 101"], ["CISP 102"]],
          "CSE 12": [["CISP 201"]],
          ...
        },
        "UCR": {
          "CSE 8A": [["CISP 110"]],
          ...
        }
      }
    """
    filename = get_articulation_filename(cc_name)
    path = articulation_dir / filename
    data = load_json(path).get(cc_name, {})

    uc_to_map: Dict[str, Dict[str, List[List[str]]]] = {}
    for uc in selected_ucs:
        uc_map: Dict[str, List[List[str]]] = {}
        for entry in data.get(uc, {}).values():
            recs: List[str] = []
            if 'receiving_course' in entry:
                recs = [entry['receiving_course']]
            elif 'receiving_courses' in entry:
                recs = entry['receiving_courses']

            # preserve groupings: each group is an AND, outer list is OR
            groups = entry.get('course_groups', [])
            blocks = [[course_obj['course'] for course_obj in group] for group in groups]
            for rec in recs:
                uc_map.setdefault(rec, [])
                uc_map[rec].extend(blocks)
        uc_to_map[uc] = uc_map
    return uc_to_map

# ─── Low-Level Helpers ───────────────────────────────────────────────────────

def load_uc_requirement_groups(
    course_reqs_path: Path,
    selected_ucs: List[str]
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    data    = load_json(course_reqs_path)
    uc_reqs = data.get('UC_REQUIREMENTS', {})
    groups: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for uc in selected_ucs:
        raw = uc_reqs.get(uc, {})  # Use uc directly, not uc.lower()
        if not raw:
            continue
        groups[uc] = {}
        for group_name, options in raw.items():
            codes   = [opt[0] for opt in options]
            num_req = options[0][2] if len(options[0]) >= 3 else len(codes)
            groups[uc][group_name] = {'courses': codes, 'num_required': num_req}
    return groups


def get_articulation_filename(cc_name: str) -> str:
    """Convert short CC ID to actual articulation filename."""
    mapping = {
        "cabrillo": "Cabrillo_College_articulation.json",
        "chabot": "Chabot_College_articulation.json",
        "city_college_of_san_francisco": "City_College_Of_San_Francisco_articulation.json",
        "consumes_river": "Consumnes_River_College_articulation.json",
        "de_anza": "De_Anza_College_articulation.json",
        "diablo_valley": "Diablo_Valley_College_articulation.json",
        "folsom_lake": "Folsom_Lake_College_articulation.json",
        "foothill": "Foothill_College_articulation.json",
        "la_city": "Los_Angeles_City_College_articulation.json",
        "las_positas": "Las_Positas_College_articulation.json",
        "los_angeles_pierce": "Los_Angeles_Pierce_College_articulation.json",
        "miracosta": "MiraCosta_College_articulation.json",
        "mt_san_jacinto": "Mt_San_Jacinto_College_articulation.json",
        "orange_coast": "Orange_Coast_College_articulation.json",
        "palomar": "Palomar_College_articulation.json",
    }
    return mapping.get(cc_name, f"{cc_name}_articulation.json")


def build_uc_block_map(
    cc_name: str,
    selected_ucs: List[str],
    articulation_dir: Path
) -> Dict[Tuple[str, str], List[List[str]]]:
    filename = get_articulation_filename(cc_name)
    path = articulation_dir / filename
    print(f"    Debug: Loading articulation file: {path}")
    data = load_json(path)
    print(f"    Debug: Loaded data keys: {list(data.keys())}")
    
    # Get the actual CC name from the data (first key)
    actual_cc_name = list(data.keys())[0] if data else cc_name
    print(f"    Debug: Using CC name: {actual_cc_name}")
    cc_data = data.get(actual_cc_name, {})
    print(f"    Debug: CC data keys: {list(cc_data.keys())}")
    block_map: Dict[Tuple[str, str], List[List[str]]] = {}

    for uc in selected_ucs:
        uc_data = cc_data.get(uc, {})
        print(f"    Debug: Processing {uc}, found {len(uc_data)} entries")
        for group_name, entry in uc_data.items():
            print(f"      Processing {group_name}: {list(entry.keys())}")
            
            # Handle both single receiving course and multiple receiving courses
            recs = []
            if 'receiving_course' in entry:
                recs = [entry['receiving_course']]
            elif 'receiving_courses' in entry:
                recs = entry['receiving_courses']
            
            print(f"        Receiving courses: {recs}")
            
            # Extract course groups
            course_groups = entry.get('course_groups', [])
            print(f"        Course groups: {len(course_groups)} groups")
            blocks: List[List[str]] = [[c['course'] for c in group] for group in course_groups]
            print(f"        Extracted blocks: {blocks}")
            
            for r in recs:
                block_map.setdefault((uc, r), []).extend(blocks)
                print(f"        Added to block_map[({uc}, {r})]: {blocks}")
    
    # Debug: Print what we found
    print(f"  Debug: Found {len(block_map)} entries in block_map")
    for (uc, uccode), blocks in block_map.items():
        print(f"    ({uc}, {uccode}): {len(blocks)} blocks")
    
    return block_map


def build_uc_group_block_map(
    cc_name: str,
    selected_ucs: List[str],
    articulation_dir: Path,
    course_reqs_path: Path
) -> Dict[Tuple[str, str], List[List[str]]]:
    block_map  = build_uc_block_map(cc_name, selected_ucs, articulation_dir)
    group_defs = load_uc_requirement_groups(course_reqs_path, selected_ucs)

    group_block_map: Dict[Tuple[str, str], List[List[str]]] = {}
    for uc, groups in group_defs.items():
        for grp, meta in groups.items():
            blocks: List[List[str]] = []
            for uccode in meta['courses']:
                # Look for exact match first
                exact_blocks = block_map.get((uc, uccode), [])
                blocks.extend(exact_blocks)
                
                # If no exact match, look for partial matches (e.g., "Intro" vs "Intro_B")
                if not exact_blocks:
                    for (block_uc, block_uccode), block_data in block_map.items():
                        if block_uc == uc and (block_uccode == uccode or 
                                             block_uccode.startswith(grp) or 
                                             grp.startswith(block_uccode.split('_')[0])):
                            blocks.extend(block_data)
            
            group_block_map[(uc, grp)] = blocks

    return group_block_map
