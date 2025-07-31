#!/usr/bin/env python3
"""
pathway_generator.py

Demonstrates mapping of CC courses to UC requirements,
including nested AND/OR articulation logic, and prints
flat lists of both CC sending courses and UC requirement courses.
"""
from pathlib import Path
from major_checker import (
    load_uc_requirement_groups,
    get_required_cc_courses,
    build_uc_block_map,
    build_uc_group_block_map
)

def main():
    cc_name = "Palomar_College"
    selected_ucs = ["UCLA", "UCSD", "UCD"]
    root = Path(__file__).parent.parent
    art_dir = root / "articulated_courses_json"
    req_path = root / "scraping" / "files" / "course_reqs.json"

    # 1. Flat list of all CC sending courses that articulate
    flat_cc = get_required_cc_courses(cc_name, selected_ucs, art_dir)
    print("Flat list of CC sending courses:")
    for course in flat_cc:
        print(f" - {course}")

    # 2. Flat list of UC requirement courses
    group_defs = load_uc_requirement_groups(req_path, selected_ucs)
    flat_uc = sorted({
        course
        for groups in group_defs.values()
        for meta in groups.values()
        for course in meta['courses']
    })
    print("\nFlat list of UC requirement courses:")
    for uc_course in flat_uc:
        print(f" - {uc_course}")

    # 3. Show block-level mappings
    # group_block_map = build_uc_group_block_map(
    #     cc_name, selected_ucs, art_dir, req_path
    # )
    # print("\nGroup block map (nested AND/OR):")
    # for (uc, group_name), blocks in sorted(group_block_map.items()):
    #     print(f"{uc} {group_name}:")
    #     for i, block in enumerate(blocks, start=1):
    #         print(f"  Option {i}: {block}")

    # 4. Per-UC requirement to CC sending courses mapping
    block_map = build_uc_block_map(cc_name, selected_ucs, art_dir)
    print("\nPer-UC requirement to CC sending courses:")
    for (uc, rec), blocks in sorted(block_map.items()):
        senders = sorted({course for block in blocks for course in block})
        mapped = ', '.join(senders) if senders else 'No matching CC courses'
        print(f"{uc} requirement '{rec}' -> [{mapped}]")

if __name__ == "__main__":
    main()
