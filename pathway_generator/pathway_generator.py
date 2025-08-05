#!/usr/bin/env python3
import json
import os
from pathlib import Path
from pprint import pprint


from major_checker import MajorRequirements, get_major_requirements
from ge_checker import GE_Tracker
from prereq_resolver import get_eligible_courses, load_prereq_data
from ge_helper import load_ge_lookup, build_ge_courses
from unit_balancer import select_courses_for_term
# from elective_filler import fill_electives
from plan_exporter import export_term_plan, save_plan_to_json

# ─── Constants ────────────────────────────────────────────────────────────────
MAX_UNITS = 18             # semester cap (use 20 for quarters)
TOTAL_UNITS_REQUIRED = 60  # typical CC → UC transfer target

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


# ─── Helpers for User Input ──────────────────────────────────────────────────
def normalize_cc_name(cc_input):
    """Map a short CC ID to the exact JSON filename in data/prereqs/."""
    mapping = {
        "cabrillo": "cabrillo_college_prereqs.json",
        "chabot": "chabot_college_prereqs.json",
        "city_college_of_san_francisco": "city_college_of_san_francisco_prereqs.json",
        "consumes_river": "consumes_river_college_prereqs.json",
        "de_anza": "de_anza_college_prereqs.json",
        "diablo_valley": "diablo_valley_prereqs.json",
        "folsom_lake": "folsom_lake_college_prereqs.json",
        "foothill": "foothill_college_prereqs.json",
        "la_city": "la_city_college_prereqs.json",
        "las_positas": "las_positas_college_prereqs.json",
        "los_angeles_pierce": "los_angeles_pierce_prereqs.json",
        "miracosta": "miracosta_college_prereqs.json",
        "mt_san_jacinto": "mt_san_jacinto_college_prereqs.json",
        "orange_coast": "orange_coast_college_prereqs.json",
        "palomar": "palomar_prereqs.json"
    }
    return mapping.get(cc_input.strip().lower())


def get_user_inputs():
    """Prompt until the user picks a valid CC, UC, and GE pattern."""
    print("📍 Available Community Colleges:")
    for cc in SUPPORTED_CCS:
        print(f"  • {cc}")
    cc = input("\nEnter the CC ID (e.g., 'de_anza'): ").strip().lower()
    while cc not in SUPPORTED_CCS:
        cc = input("Invalid CC. Try again: ").strip().lower()

    print("\n🎓 Available UC Campuses:")
    for uc in SUPPORTED_UCS:
        print(f"  • {uc}")
    uc = input("\nEnter the UC campus (e.g., 'ucsd'): ").strip().upper()
    while uc not in SUPPORTED_UCS:
        uc = input("Invalid UC. Try again: ").strip().upper()

    print("\n📚 Available GE Patterns:")
    print("  • 7CoursePattern - Basic 7-Course GE Pattern")
    print("  • IGETC - IGETC General Education")
    ge_pattern = input("\nEnter the GE pattern (e.g., '7CoursePattern' or 'IGETC'): ").strip()
    while ge_pattern not in ["7CoursePattern", "IGETC"]:
        ge_pattern = input("Invalid GE pattern. Try again: ").strip()

    return cc, uc, ge_pattern


def build_file_paths(cc_id: str, uc_id: str):
    """Build all necessary file paths for the pathway generation."""
    # articulation file path
    art_fname = ARTICULATION_FILES.get(cc_id)
    if not art_fname:
        raise ValueError(f"No articulation file mapped for '{cc_id}'")
    art_path = ARTICULATION_DIR / art_fname
    if not art_path.exists():
        raise FileNotFoundError(f"Articulation file not found: {art_path}")

    # prerequisite file path
    prereq_fname = normalize_cc_name(cc_id)
    if not prereq_fname:
        raise ValueError(f"No prerequisite file mapped for '{cc_id}'")
    prereq_path = PREREQS_DIR / prereq_fname
    if not prereq_path.exists():
        raise FileNotFoundError(f"Prerequisite file not found: {prereq_path}")

    # GE requirements file path
    ge_path = PREREQS_DIR / "ge_reqs.json"
    if not ge_path.exists():
        raise FileNotFoundError(f"GE requirements file not found: {ge_path}")

    return {
        "articulated_courses_json": art_path,
        "prereq_file": prereq_path,
        "ge_reqs_json": ge_path,
        "course_reqs_json": COURSE_REQS_FILE
    }


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


# ─── Helper Functions for Pathway Generation ─────────────────────────────────

# def balance_units(eligible, max_units):
#     """Balance units to stay within the semester cap."""
#     # TODO: Implement unit balancing logic
#     # For now, return first few courses that fit within max_units
#     selected = []
#     total_units = 0
    
#     for course in eligible:
#         course_units = course.get("units", 3)
#         if total_units + course_units <= max_units:
#             selected.append(course)
#             total_units += course_units
    
#     return selected, total_units


# ─── Core Pathway Generation ─────────────────────────────────────────────────
def generate_pathway(art_path, prereq_path, ge_path, major_path, cc_id: str, uc_id: str, ge_pattern: str):
    # articulated = load_json(art_path)
    # prereqs = load_json(prereq_path)
    articulated = load_json(art_path)
    # load as a dict: courseCode -> metadata
    prereqs = load_prereq_data(prereq_path)
    ge_data = load_json(ge_path)
    
    # Initialize the classes
    ge_tracker = GE_Tracker(ge_data)
    # Load the appropriate GE pattern
    ge_tracker.load_pattern(ge_pattern)
    
    major_reqs = get_major_requirements(
        str(major_path), 
        cc_id, 
        [uc_id.upper()], 
        str(ARTICULATION_DIR)
    )

    # Debug: Print major requirements information
    # print(f"\n🔍 Major Requirements Debug:")
    # print(f"  Number of UC campuses: {len(major_reqs.group_defs)}")
    # for uc, groups in major_reqs.group_defs.items():
    #     print(f"  {uc}: {len(groups)} requirement groups")
    #     for group_name, group_info in groups.items():
    #         print(f"    - {group_name}: {group_info['num_required']} courses required")
    #         print(f"      Required UC courses: {group_info['courses']}")
    
    # print(f"\n  Number of CC→UC block mappings: {len(major_reqs.group_block_map)}")
    # for (uc, group), blocks in major_reqs.group_block_map.items():
    #     print(f"    {uc}:{group}: {len(blocks)} course blocks available")
    #     for i, block in enumerate(blocks[:3]):  # Show first 3 blocks
    #         print(f"      Block {i+1}: {block}")
    #     if len(blocks) > 3:
    #         print(f"      ... and {len(blocks) - 3} more blocks")
    
    # Debug: Show what's actually in the articulation data for UCSD
    # print(f"\n🔍 Articulation Data Debug for UCSD:")
    # articulated_data = load_json(paths["articulated_courses_json"])
    # ucsd_data = articulated_data.get("De_Anza_College", {}).get("UCSD", {})
    # print(f"  UCSD articulation entries: {list(ucsd_data.keys())}")
    # for entry_name, entry_data in ucsd_data.items():
    #     receiving = entry_data.get('receiving_course', 'N/A')
    #     print(f"    {entry_name} -> {receiving}")
    
    # Debug: Show what's in the block_map
    # print(f"\n🔍 Block Map Debug:")
    # from major_checker import build_uc_block_map
    # block_map = build_uc_block_map("de_anza", ["UCSD"], ARTICULATION_DIR)
    # print(f"  Block map keys: {list(block_map.keys())}")
    # for (uc, uccode), blocks in block_map.items():
    #     print(f"    ({uc}, {uccode}): {len(blocks)} blocks")
    #     for i, block in enumerate(blocks[:2]):
    #         print(f"      Block {i+1}: {block}")

    completed = set()
    total_units = 0
    term_num = 1
    pathway = []

    ge_lookup = load_ge_lookup(PREREQS_DIR / "ge_reqs.json")

    while total_units < TOTAL_UNITS_REQUIRED:
        print(f"\n📘 Generating Term {term_num}…")

        # 1) Candidate courses from major + GE
        major_cands = major_reqs.get_remaining_courses(completed, articulated)
        print(f"  Found {len(major_cands)} major course candidates")
        pprint(major_cands)
        
        # For GE courses, we need to get remaining requirements and find courses that fulfill them
        ge_remaining = ge_tracker.get_remaining_requirements(ge_pattern)
        
        print(f"  GE remaining requirements: {list(ge_remaining.keys())}")

        ge_course_dicts = build_ge_courses(ge_remaining, ge_lookup, unit_count=3)
        
        
        # 2) Prereq filter
        eligible = get_eligible_courses(completed, prereqs)

        # print(f"  Eligible courses: {len(eligible)}")
        # pprint(eligible)
        # eligible_course_codes = [c['courseCode'] for c in eligible]

        # 3) Build eligibility list
        eligible_course_dicts = [
            {
                'courseCode': e['courseCode'],
                'units':      e['units']
            }
            for e in eligible
        ]

        total_eligible = eligible_course_dicts + ge_course_dicts
        print(f"Total Eligible: {total_eligible}")
        # 4) Balance units
        selected, units = select_courses_for_term(total_eligible, completed)

        # 5) Fill electives if under cap & still under 60 total
        # if units < MAX_UNITS and total_units + units < TOTAL_UNITS_REQUIRED:
        #     selected, units = fill_electives(selected, units, MAX_UNITS)

        # 6) Update state
        for course in selected:
            completed.add(course["courseCode"])
            # Update GE tracker with completed course
            tags = [course.get("tag")] if course.get("tag") else []
            ge_tracker.add_completed_course(course["courseCode"], tags)
        
        print(f"Completed courses: {completed}")
        total_units += units

        # 7) Record this term
        export_term_plan(f"Term {term_num}", selected, pathway)
        term_num += 1

        # if term_num > 2:
        #     break

    return pathway


# ─── Script Entrypoint ───────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        cc, uc, ge_pattern = get_user_inputs()
        print(f"\n🔧 Building file paths for CC: {cc}, UC: {uc}, GE Pattern: {ge_pattern}")
        paths = build_file_paths(cc, uc)
        
        print(f"  Articulation file: {paths['articulated_courses_json']}")
        print(f"  Prerequisite file: {paths['prereq_file']}")
        print(f"  GE requirements file: {paths['ge_reqs_json']}")
        print(f"  Course requirements file: {paths['course_reqs_json']}")

        pathway = generate_pathway(
            paths["articulated_courses_json"],
            paths["prereq_file"],
            paths["ge_reqs_json"],
            paths["course_reqs_json"],
            cc,
            uc,
            ge_pattern
        )

        # Save the plan JSON to the pathway_generator directory
        output_json_path = SCRIPT_DIR / "output_pathway.json"
        save_plan_to_json(pathway, str(output_json_path))

        # Print or further save the full plan
        # print("\n🎉 Final Pathway:")
        # for term in pathway:
        #     print(f"Term {term['term']}: {term['total_units']} units")
        #     for course in term['courses']:
        #         print(f"  - {course['courseCode']} ({course.get('units', 3)} units)")
        #     print()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
