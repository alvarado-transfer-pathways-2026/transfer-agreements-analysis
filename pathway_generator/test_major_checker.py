#!/usr/bin/env python3
"""
test_major_checker.py

Prompt for a CC & UCs, then use the MajorRequirements interface
and get_cc_to_uc_map from major_checker.py to list:
  1) candidate CC courses for the first term across all selected UCs
  2) the mapping of UC courses to CC courses with clear breaks per UC
"""

import json
import sys
from pathlib import Path

from major_checker import get_major_requirements, get_cc_to_uc_map

# ─── 1) Locate directories ────────────────────────────────────────────────────
SCRIPT_DIR       = Path(__file__).parent.resolve()  # .../pathway_generator
PROJECT_ROOT     = SCRIPT_DIR.parent               # .../transfer-agreements-analysis
ARTICULATION_DIR = PROJECT_ROOT / "articulated_courses_json"
PREREQS_DIR      = PROJECT_ROOT / "prerequisites"
COURSE_REQS_FILE = PROJECT_ROOT / "scraping" / "files" / "course_reqs.json"

# ─── 2) CC and UC options ─────────────────────────────────────────────────────
ARTICULATION_FILES = {
    "cabrillo":   "Cabrillo_College_articulation.json",
    "chabot":     "Chabot_College_articulation.json",
    "city_college_of_san_francisco": "City_College_Of_San_Francisco_articulation.json",
    "consumes_river":               "Consumnes_River_College_articulation.json",
    "de_anza":    "De_Anza_College_articulation.json",
    "diablo_valley":"Diablo_Valley_College_articulation.json",
    "folsom_lake":"Folsom_Lake_College_articulation.json",
    "foothill":   "Foothill_College_articulation.json",
    "la_city":    "Los_Angeles_City_College_articulation.json",
    "las_positas":"Las_Positas_College_articulation.json",
    "los_angeles_pierce":"Los_Angeles_Pierce_College_articulation.json",
    "miracosta":  "MiraCosta_College_articulation.json",
    "mt_san_jacinto":"Mt_San_Jacinto_College_articulation.json",
    "orange_coast":"Orange_Coast_College_articulation.json",
    "palomar":    "Palomar_College_articulation.json",
}
SUPPORTED_CCS = list(ARTICULATION_FILES.keys())
SUPPORTED_UCS = ["UCSD", "UCLA", "UCI", "UCR", "UCSB", "UCD", "UCB", "UCSC", "UCM"]


def get_user_inputs():
    """
    Prompt the user to select a CC ID and one or more UC campuses.
    Returns:
      cc_id (str), uc_keys (List[str])
    """
    # Select CC
    print("📍 Available Community Colleges:")
    for cc in SUPPORTED_CCS:
        print(f"  • {cc}")
    cc = input("\nEnter the CC ID (e.g., 'de_anza'): ").strip().lower()
    while cc not in SUPPORTED_CCS:
        cc = input("Invalid CC. Try again: ").strip().lower()

    # Select multiple UCs
    print("\n🎓 Available UC Campuses:")
    for uc in SUPPORTED_UCS:
        print(f"  • {uc}")
    ucs_input = input(
        "\nEnter one or more UC campuses (comma-separated, e.g., 'UCSD,UCLA'): "
    ).strip().upper()
    uc_keys = [u.strip() for u in ucs_input.split(',') if u.strip()]
    while not uc_keys or any(u not in SUPPORTED_UCS for u in uc_keys):
        print("Invalid UC selection. Please use comma-separated values from the list.")
        ucs_input = input("Enter UC campuses (e.g., 'UCSD,UCLA'): ").strip().upper()
        uc_keys = [u.strip() for u in ucs_input.split(',') if u.strip()]

    return cc, uc_keys


def build_file_paths(cc_id: str):
    # articulation file path
    art_fname = ARTICULATION_FILES.get(cc_id)
    if not art_fname:
        raise ValueError(f"No articulation file mapped for '{cc_id}'")
    art_path = ARTICULATION_DIR / art_fname
    if not art_path.exists():
        raise FileNotFoundError(f"Articulation file not found: {art_path}")

    return art_path, COURSE_REQS_FILE


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    cc_id, uc_keys = get_user_inputs()
    try:
        art_path, course_reqs_path = build_file_paths(cc_id)
    except Exception as e:
        print(f"✖ {e}")
        sys.exit(1)

    # load articulation JSON
    data = json.load(open(art_path, 'r', encoding='utf-8'))
    cc_key = next(iter(data.keys()))
    articulated = data[cc_key]

    print(f"\n▶ Using articulation: {art_path.name}")
    print(f"▶ CC JSON key: '{cc_key}'")
    print(f"▶ UC keys: {uc_keys}\n")

    # 1) Test MajorRequirements interface
    mr = get_major_requirements(
        course_reqs_path=str(course_reqs_path),
        cc_name=cc_key,
        selected_ucs=uc_keys,
        articulation_dir=str(ARTICULATION_DIR)
    )
    candidates = mr.get_remaining_courses(set(), articulated)
    print(f"✅ Found {len(candidates)} candidate courses for first term across {uc_keys}:")
    for c in candidates:
        print(f"  • {c['courseCode']:<10} {c['units']:>2} units   [{c['tag']}]  ")

    # 2) Test get_cc_to_uc_map with formatted breaks
    uc_map = get_cc_to_uc_map(
        cc_name=cc_key,
        selected_ucs=uc_keys,
        articulation_dir=ARTICULATION_DIR
    )
    print(f"\n===== CC → UC Articulation Map for {uc_keys} =====")
    for uc in uc_keys:
        mapping = uc_map.get(uc, {})
        print(f"\n--- {uc} ---")
        if not mapping:
            print("  (no articulation data)")
        for uc_course, cc_groups in mapping.items():
            print(f"  {uc_course}: {cc_groups}")


if __name__ == '__main__':
    main()
