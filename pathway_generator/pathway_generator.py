#!/usr/bin/env python3
import json
import os

from major_checker import get_major_requirements
# from ge_checker import get_ge_requirements
# from prereq_resolver import filter_by_prereqs
# from unit_balancer import balance_units
# from elective_filler import fill_electives
# from plan_exporter import export_term

# ─── Constants ────────────────────────────────────────────────────────────────
MAX_UNITS = 18             # semester cap (use 20 for quarters)
TOTAL_UNITS_REQUIRED = 60  # typical CC → UC transfer target

SUPPORTED_CCS = [
    "cabrillo", "chabot", "city_college_of_san_francisco", "consumes_river",
    "de_anza", "diablo_valley", "folsom_lake", "foothill", "la_city",
    "las_positas", "los_angeles_pierce", "miracosta",
    "mt_san_jacinto", "orange_coast", "palomar"
]

SUPPORTED_UCS = [
    "ucsd", "ucla", "uci", "ucr", "ucsb", "ucd", "ucb", "ucsc", "ucmerced"
]


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
    """Prompt until the user picks a valid CC and UC."""
    print("📍 Available Community Colleges:")
    for cc in SUPPORTED_CCS:
        print(f"  • {cc}")
    cc = input("\nEnter the CC ID (e.g., 'de_anza'): ").strip().lower()
    while cc not in SUPPORTED_CCS:
        cc = input("Invalid CC. Try again: ").strip().lower()

    print("\n🎓 Available UC Campuses:")
    for uc in SUPPORTED_UCS:
        print(f"  • {uc}")
    uc = input("\nEnter the UC campus (e.g., 'ucsd'): ").strip().lower()
    while uc not in SUPPORTED_UCS:
        uc = input("Invalid UC. Try again: ").strip().lower()

    return cc, uc


def build_file_paths(cc, uc):
    """Given valid IDs, build all the JSON paths we need."""
    prereq_file = normalize_cc_name(cc)
    assert prereq_file, f"No prereqs file found for '{cc}'"

    return {
        "articulated_courses_json": os.path.join("data", "articulated", f"{cc}_to_{uc}.json"),
        "prereq_file":              os.path.join("data", "prereqs", prereq_file),
        "ge_reqs_json":             os.path.join("data", "ge", "ge_reqs.json"),
        "course_reqs_json":         os.path.join("data", "major", f"{uc}.json")
    }


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


# ─── Core Pathway Generation ─────────────────────────────────────────────────
def generate_pathway(art_path, prereq_path, ge_path, major_path):
    articulated = load_json(art_path)
    prereqs     = load_json(prereq_path)
    ge_reqs     = get_ge_requirements(ge_path)
    major_reqs  = get_major_requirements(major_path)

    completed = set()
    total_units = 0
    term_num = 1
    pathway = []

    while total_units < TOTAL_UNITS_REQUIRED:
        print(f"\n📘 Generating Term {term_num}…")

        # 1) Candidate courses from major + GE
        major_cands = major_reqs.get_remaining_courses(completed, articulated)
        ge_cands    = ge_reqs.get_remaining_areas(completed, articulated)
        candidates  = major_cands + ge_cands

        # 2) Prereq filter
        eligible = filter_by_prereqs(candidates, completed, prereqs)

        # 3) Balance units
        selected, units = balance_units(eligible, MAX_UNITS)

        # 4) Fill electives if under cap & still under 60 total
        if units < MAX_UNITS and total_units + units < TOTAL_UNITS_REQUIRED:
            selected, units = fill_electives(selected, units, MAX_UNITS)

        # 5) Update state
        completed.update(course["courseCode"] for course in selected)
        total_units += units

        # 6) Record this term
        export_term(pathway, term_num, selected)
        term_num += 1

    return pathway


# ─── Script Entrypoint ───────────────────────────────────────────────────────
if __name__ == "__main__":
    cc, uc = get_user_inputs()
    paths = build_file_paths(cc, uc)

    pathway = generate_pathway(
        paths["articulated_courses_json"],
        paths["prereq_file"],
        paths["ge_reqs_json"],
        paths["course_reqs_json"]
    )

    # Print or further save the full plan
    print("\n🎉 Final Pathway:")
    for term in pathway:
        print(term)
