# pathway_generator.py
#!/usr/bin/env python3
"""
pathway_generator.py

Demonstrates mapping of CC courses to UC requirements using updated parsing.
"""
from pathlib import Path
from collections import defaultdict
from major_checker import (
    load_uc_requirement_groups,
    get_required_cc_courses,
    build_uc_tuple_map,
    build_uc_group_map
)

def main():
    cc_name = "Palomar_College"
    selected_ucs = ["UCR", "UCSD"]
    root = Path(__file__).parent.parent
    art_dir = root / "articulated_courses_json"
    req_path = root / "scraping" / "files" / "course_reqs.json"

    flat = get_required_cc_courses(cc_name, selected_ucs, art_dir)
    print("Flat CC courses:")
    print(flat)

    tuple_map = build_uc_tuple_map(cc_name, selected_ucs, art_dir)
    print("\nPer-course mappings:")
    for (uc, uc_course), cc_list in tuple_map.items():
        print(f"{uc} {uc_course} <- {cc_list}")

    groups = load_uc_requirement_groups(req_path, selected_ucs)
    print("\nRequirement groups:")
    for uc, grp in groups.items():
        print(uc, grp)

    grp_map = build_uc_group_map(cc_name, selected_ucs, art_dir, req_path)
    print("\nGroup mappings:")
    for (uc, g), cc_list in grp_map.items():
        print(f"{uc} {g} <- {cc_list}")

    # invert
    inv = defaultdict(list)
    for (uc, uc_course), cc_list in tuple_map.items():
        for c in cc_list:
            inv[c].append((uc, uc_course))
    print("\nCC->UC:")
    for c, mappings in inv.items():
        print(f"{c} -> {mappings}")

if __name__ == "__main__":
    main()
