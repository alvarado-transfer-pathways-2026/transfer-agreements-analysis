#!/usr/bin/env python3
import json
import os
from pathlib import Path
from pprint import pprint
import datetime


from major_checker import MajorRequirements, get_major_requirements
from ge_checker import GE_Tracker
from prereq_resolver import get_eligible_courses, load_prereq_data, add_missing_prereqs
from ge_helper import load_ge_lookup, build_ge_courses
from unit_balancer import select_courses_for_term, prune_uc_to_cc_map
# from elective_filler import fill_electives
from plan_exporter import export_term_plan, save_plan_to_json

# ─── Constants ────────────────────────────────────────────────────────────────
MAX_UNITS = 16             # semester cap (use 20 for quarters)
TOTAL_UNITS_REQUIRED = 60  # typical CC → UC transfer target

# ─── Debug logging setup ─────────────────────────────────────────────────────
DEBUG_LOG = []

def debug_log(message, data=None):
    """Add a debug message with timestamp to the log."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    if data is not None:
        log_entry += f"\n{json.dumps(data, indent=2, default=str)}"
    DEBUG_LOG.append(log_entry)
    print(log_entry)  # Also print to console

def save_debug_log(filepath="pathway_debug.txt"):
    """Save the debug log to a file."""
    with open(filepath, 'w') as f:
        for entry in DEBUG_LOG:
            f.write(entry + "\n" + "="*80 + "\n")
    print(f"Debug log saved to {filepath}")

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
    "cosumnes_river":               "Cosumnes_River_College_articulation.json",
    "de_anza":    "De_Anza_College_articulation.json",
    "diablo_valley":"Diablo_Valley_College_articulation.json",
    "folsom_lake":"Folsom_Lake_College_articulation.json",
    "foothill":   "Foothill_College_articulation.json",
    "los_angeles_city_college":    "Los_Angeles_City_College_articulation.json",
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
        "cosumnes_river": "cosumnes_river_college_prereqs.json",
        "de_anza": "de_anza_college_prereqs.json",
        "diablo_valley": "diablo_valley_prereqs.json",
        "folsom_lake": "folsom_lake_college_prereqs.json",
        "foothill": "foothill_college_prereqs.json",
        "los_angeles_city_college": "los_angeles_city_college_prereqs.json",
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
    # uc = input("\nEnter the UC campus (e.g., 'ucsd'): ").strip().upper()
    # while uc not in SUPPORTED_UCS:
    #     uc = input("Invalid UC. Try again: ").strip().upper()
    while True:
        uc_input = input("\nEnter one or more UC campuses (comma-separated, e.g., 'ucsd, ucla'): ").strip()
        raw_ucs = [uc.strip().upper() for uc in uc_input.split(",")]
        
        valid_ucs = [uc for uc in raw_ucs if uc in SUPPORTED_UCS]
        invalid_ucs = [uc for uc in raw_ucs if uc not in SUPPORTED_UCS]

        if not valid_ucs:
            print("❌ None of the UC campuses you entered are valid. Please try again.")
            continue

        if invalid_ucs:
            print(f"⚠️ The following UC campuses were ignored because they're invalid: {', '.join(invalid_ucs)}")

        uc_list = valid_ucs
        break


    print("\n📚 Available GE Patterns:")
    print("  • 7CoursePattern - Basic 7-Course GE Pattern")
    print("  • IGETC - IGETC General Education")
    ge_pattern = input("\nEnter the GE pattern (e.g., '7CoursePattern' or 'IGETC'): ").strip()
    while ge_pattern not in ["7CoursePattern", "IGETC"]:
        ge_pattern = input("Invalid GE pattern. Try again: ").strip()

    debug_log("USER INPUT COLLECTED", {
        "cc": cc,
        "uc_list": uc_list,
        "ge_pattern": ge_pattern
    })

    return cc, uc_list, ge_pattern


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

    debug_log("FILE PATHS BUILT", {
        "articulation_file": str(art_path),
        "prereq_file": str(prereq_path),
        "ge_file": str(ge_path),
        "course_reqs_file": str(COURSE_REQS_FILE)
    })

    return {
        "articulated_courses_json": art_path,
        "prereq_file": prereq_path,
        "ge_reqs_json": ge_path,
        "course_reqs_json": COURSE_REQS_FILE
    }


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def get_course_units(course_code, prereqs, articulated=None):
    """Get the unit count for a course from prereqs or articulated data."""
    # First try to get units from prerequisites data
    # Based on your example, prereqs is a list of course objects
    if isinstance(prereqs, list):
        for course in prereqs:
            if isinstance(course, dict) and course.get('courseCode') == course_code:
                if 'units' in course:
                    units = course['units']
                    debug_log(f"Found units for {course_code} in prereqs list", {"units": units})
                    return units
                elif 'courseUnits' in course:
                    units = course['courseUnits']
                    debug_log(f"Found courseUnits for {course_code} in prereqs list", {"units": units})
                    return units
    
    # If prereqs is a dict (fallback for different data structures)
    elif isinstance(prereqs, dict):
        if course_code in prereqs:
            course_data = prereqs[course_code]
            if isinstance(course_data, dict):
                if 'units' in course_data:
                    units = course_data['units']
                    debug_log(f"Found units for {course_code} in prereqs dict", {"units": units})
                    return units
                elif 'courseUnits' in course_data:
                    units = course_data['courseUnits']
                    debug_log(f"Found courseUnits for {course_code} in prereqs dict", {"units": units})
                    return units
            elif isinstance(course_data, list):
                # Sometimes the value might be a list with course info
                for item in course_data:
                    if isinstance(item, dict) and item.get('courseCode') == course_code:
                        if 'units' in item:
                            units = item['units']
                            debug_log(f"Found units for {course_code} in prereqs dict list", {"units": units})
                            return units

    # Then try articulated data if provided
    if articulated:
        for uc_data in articulated.values():
            if isinstance(uc_data, dict):
                for major_data in uc_data.values():
                    if isinstance(major_data, dict):
                        for req_data in major_data.values():
                            if isinstance(req_data, list):
                                for course_list in req_data:
                                    if isinstance(course_list, list):
                                        for course in course_list:
                                            if isinstance(course, dict) and course.get('courseCode') == course_code:
                                                if 'units' in course:
                                                    units = course['units']
                                                    debug_log(f"Found units for {course_code} in articulated", {"units": units})
                                                    return units
                                                elif 'courseUnits' in course:
                                                    units = course['courseUnits']
                                                    debug_log(f"Found courseUnits for {course_code} in articulated", {"units": units})
                                                    return units
    
    # Default to 3 units if not found
    debug_log(f"Could not find units for {course_code}, defaulting to 3 units", {"course_code": course_code})
    return 3


def ensure_course_has_units(course_dict, prereqs, articulated=None):
    """Ensure a course dictionary has proper unit information."""
    course_code = course_dict.get('courseCode')
    if not course_code:
        return course_dict
    
    # If units already exist, use them
    if 'units' in course_dict and course_dict['units'] is not None:
        return course_dict
    
    # Otherwise, look up units
    units = get_course_units(course_code, prereqs, articulated)
    course_dict['units'] = units
    return course_dict


def is_major_requirement_complete(major_reqs, completed, articulated):
    """Check if all major requirements are truly complete by examining remaining courses."""
    try:
        remaining_major = major_reqs.get_remaining_courses(completed, articulated)
        
        debug_log("MAJOR COMPLETION CHECK", {
            "remaining_courses_count": len(remaining_major),
            "remaining_course_codes": [c.get('courseCode', 'NO_CODE') for c in remaining_major] if remaining_major else [],
            "completed_courses": sorted(list(completed))
        })
        
        # If there are no remaining courses, major requirements are complete
        return len(remaining_major) == 0
        
    except Exception as e:
        debug_log("ERROR IN MAJOR COMPLETION CHECK", {
            "error": str(e),
            "fallback": "Assuming not complete"
        })
        return False


def can_make_progress(eligible_major, eligible_ge, completed_before_term):
    """
    Check if we can make progress this term by comparing what we can take
    versus what we've already completed.
    """
    # Get course codes that are eligible
    eligible_major_codes = {c.get('courseCode') for c in eligible_major}
    eligible_ge_codes = {c.get('courseCode') for c in eligible_ge}
    all_eligible_codes = eligible_major_codes.union(eligible_ge_codes)
    
    # Check if any eligible courses are not already completed
    can_progress = len(all_eligible_codes - completed_before_term) > 0
    
    debug_log("PROGRESS CHECK", {
        "eligible_major_codes": list(eligible_major_codes),
        "eligible_ge_codes": list(eligible_ge_codes),
        "all_eligible_codes": list(all_eligible_codes),
        "completed_before_term": sorted(list(completed_before_term)),
        "new_courses_available": list(all_eligible_codes - completed_before_term),
        "can_make_progress": can_progress
    })
    
    return can_progress


# ─── Core Pathway Generation ─────────────────────────────────────────────────
def generate_pathway(art_path, prereq_path, ge_path, major_path, cc_id: str, uc_list: list[str], ge_pattern: str):
    debug_log("PATHWAY GENERATION STARTED", {
        "cc_id": cc_id,
        "uc_list": uc_list,
        "ge_pattern": ge_pattern,
        "max_units_per_term": MAX_UNITS,
        "total_units_required": TOTAL_UNITS_REQUIRED
    })

    articulated = load_json(art_path)
    debug_log("LOADED ARTICULATED COURSES", {
        "uc_campuses_in_data": list(articulated.keys()),
        "total_entries": sum(len(v) if isinstance(v, dict) else 1 for v in articulated.values())
    })

    # Load and analyze the course requirements structure
    course_reqs = load_json(major_path)
    debug_log("LOADED COURSE REQUIREMENTS", {
        "top_level_keys": list(course_reqs.keys()),
        "structure_analysis": {
            key: list(value.keys()) if isinstance(value, dict) else type(value).__name__
            for key, value in course_reqs.items()
        }
    })

    # Find the correct key structure for De Anza College
    cc_key = None
    if "UC_REQUIREMENTS" in course_reqs:
        uc_reqs = course_reqs["UC_REQUIREMENTS"]
        debug_log("UC_REQUIREMENTS STRUCTURE", {
            "colleges_available": list(uc_reqs.keys()) if isinstance(uc_reqs, dict) else "not a dict",
            "looking_for_variants": ["De_Anza_College", "de_anza", "De Anza College"]
        })
        
        # Try different possible keys for De Anza
        possible_keys = ["De_Anza_College", "de_anza", "De Anza College", "DE_ANZA_COLLEGE"]
        for key in possible_keys:
            if key in uc_reqs:
                cc_key = key
                debug_log("FOUND CC KEY", {"key": cc_key})
                break
        
        if cc_key and cc_key in uc_reqs:
            debug_log("DETAILED COURSE REQUIREMENTS ANALYSIS", {
                "cc_found": True,
                "cc_key_used": cc_key,
                "available_ucs": list(uc_reqs[cc_key].keys()),
                "detailed_requirements": {
                    uc: {
                        req_name: {
                            "num_required": req_data.get("num_required", "unknown"),
                            "course_groups_count": len(req_data.get("course_groups", [])),
                            "first_group_courses": [course.get("course") for course in req_data.get("course_groups", [[]])[0]],
                            "receiving_course": req_data.get("receiving_course", "unknown")
                        }
                        for req_name, req_data in uc_reqs[cc_key].get(uc, {}).items()
                    }
                    for uc in uc_list[:3]  # First 3 UCs for detailed analysis
                    if uc in uc_reqs[cc_key]
                }
            })
        else:
            debug_log("CC KEY NOT FOUND", {
                "available_cc_keys": list(uc_reqs.keys()) if isinstance(uc_reqs, dict) else "not a dict",
                "tried_keys": possible_keys
            })
    else:
        debug_log("COURSE REQUIREMENTS ANALYSIS", {
            "uc_requirements_found": False,
            "available_top_level_keys": list(course_reqs.keys()),
            "looking_for": "UC_REQUIREMENTS"
        })

    # load as a dict: courseCode -> metadata
    prereqs = load_prereq_data(prereq_path)
    debug_log("LOADED PREREQUISITES", {
        "total_courses": len(prereqs) if isinstance(prereqs, dict) else len(prereqs),
        "prereq_type": type(prereqs).__name__
    })

    ge_data = load_json(ge_path)
    debug_log("LOADED GE DATA", {
        "ge_patterns_available": list(ge_data.keys()),
        "selected_pattern": ge_pattern
    })
    
    # Initialize the classes
    ge_tracker = GE_Tracker(ge_data)
    # Load the appropriate GE pattern
    ge_tracker.load_pattern(ge_pattern)
    debug_log("GE TRACKER INITIALIZED", {
        "pattern_loaded": ge_pattern,
        "initial_requirements": ge_tracker.get_remaining_requirements(ge_pattern)
    })
    
    major_reqs = get_major_requirements(
        str(major_path), 
        cc_id, 
        uc_list, 
        str(ARTICULATION_DIR)
    )
    debug_log("MAJOR REQUIREMENTS LOADED", {
        "major_reqs_type": type(major_reqs).__name__,
        "available_methods": [method for method in dir(major_reqs) if not method.startswith('_')]
    })

    completed = set()
    total_units = 0
    term_num = 1
    pathway = []

    debug_log("INITIAL PATHWAY STATE", {
        "completed_courses": list(completed),
        "total_units": total_units,
        "term_number": term_num
    })

    ge_lookup = load_ge_lookup(PREREQS_DIR / "ge_reqs.json")
    debug_log("GE LOOKUP LOADED", {
        "total_ge_courses": len(ge_lookup) if ge_lookup else 0
    })

    # 1) Candidate courses from major + GE 
    major_map = MajorRequirements.get_cc_to_uc_map(cc_id, uc_list, art_path)
    debug_log("MAJOR MAP GENERATED", {
        "uc_campuses": list(major_map.keys()),
        "total_mappings": sum(len(cmap) for cmap in major_map.values()),
        "sample_mappings": {uc: list(cmap.keys())[:5] for uc, cmap in major_map.items()}
    })

    # Let's examine the actual course requirements structure in detail
    if cc_id in course_reqs:
        debug_log("DETAILED COURSE REQUIREMENTS ANALYSIS", {
            "cc_found": True,
            "available_ucs": list(course_reqs[cc_id].keys()),
            "detailed_requirements": {
                uc: {
                    req_name: {
                        "num_required": req_data.get("num_required", "unknown"),
                        "course_groups_count": len(req_data.get("course_groups", [])),
                        "first_group_courses": [course.get("course") for course in req_data.get("course_groups", [[]])[0]],
                        "receiving_course": req_data.get("receiving_course", "unknown")
                    }
                    for req_name, req_data in course_reqs[cc_id].get(uc, {}).items()
                }
                for uc in uc_list[:3]  # First 3 UCs for detailed analysis
                if uc in course_reqs[cc_id]
            }
        })
    else:
        debug_log("COURSE REQUIREMENTS ANALYSIS", {
            "cc_found": False,
            "available_ccs": list(course_reqs.keys()),
            "looking_for": cc_id
        })

    uc_to_cc_map: dict[str, list[list[str]]] = {}
    for uc, cmap in major_map.items():
        for uc_course, blocks in cmap.items():
            # merge blocks for the same UC-course across campuses
            uc_to_cc_map.setdefault(uc_course, []).extend(blocks)
    
    debug_log("UC TO CC MAP CREATED", {
        "total_uc_courses": len(uc_to_cc_map),
        "uc_courses": list(uc_to_cc_map.keys())[:10],  # First 10 for brevity
        "sample_mappings": {k: v[:2] for k, v in list(uc_to_cc_map.items())[:5]}  # First 5 mappings, 2 options each
    })

    all_cc_course_codes = set(prereqs.keys())

    # Main pathway generation loop
    while True:
        debug_log(f"STARTING TERM {term_num}", {
            "current_total_units": total_units,
            "target_units": TOTAL_UNITS_REQUIRED,
            "completed_courses_count": len(completed),
            "completed_courses": sorted(list(completed))
        })
        
        # Store completed courses at start of term for progress checking
        completed_before_term = completed.copy()
        
        # Get fresh major candidates for this term
        major_cands = major_reqs.get_remaining_courses(completed, articulated)
        debug_log(f"TERM {term_num} - FRESH MAJOR CANDIDATES", {
            "count": len(major_cands),
            "course_codes": [m.get('courseCode', 'NO_CODE') for m in major_cands],
            "duplicates_analysis": {
                "total_candidates": len(major_cands),
                "unique_courses": len(set(m.get('courseCode', 'NO_CODE') for m in major_cands)),
                "duplicate_count": len(major_cands) - len(set(m.get('courseCode', 'NO_CODE') for m in major_cands))
            }
        })

        # Add missing prerequisites
        major_cands = add_missing_prereqs(major_cands, prereqs, completed)
        debug_log(f"TERM {term_num} - MAJOR CANDIDATES AFTER ADDING PREREQS", {
            "count": len(major_cands),
            "course_codes": [m.get('courseCode', 'NO_CODE') for m in major_cands]
        })
        
        # Ensure all major candidates have proper unit information
        major_cands = [ensure_course_has_units(course, prereqs, articulated) for course in major_cands]
        
        # Check if major requirements are complete
        major_complete = is_major_requirement_complete(major_reqs, completed, articulated)
        
        # For GE courses, we need to get remaining requirements and find courses that fulfill them
        ge_remaining = ge_tracker.get_remaining_requirements(ge_pattern)
        debug_log(f"TERM {term_num} - GE REQUIREMENTS CHECK", {
            "remaining_ge_categories": list(ge_remaining.keys()),
            "ge_requirements_detail": ge_remaining
        })
        
        # Build GE courses and ensure they have unit information
        ge_course_dicts = build_ge_courses(ge_remaining, ge_lookup, unit_count=3)
        ge_course_dicts = [ensure_course_has_units(course, prereqs, articulated) for course in ge_course_dicts]
        debug_log(f"TERM {term_num} - GE COURSES BUILT", {
            "count": len(ge_course_dicts),
            "course_codes": [c.get('courseCode') for c in ge_course_dicts],
            "courses_with_units": [(c.get('courseCode'), c.get('units')) for c in ge_course_dicts]
        })

        debug_log(f"TERM {term_num} - MAJOR REQUIREMENTS CHECK", {
            "major_candidates_remaining": len(major_cands),
            "major_course_codes": [c.get('courseCode') for c in major_cands],
            "major_complete": major_complete
        })

        # Check termination conditions with improved logic
        no_major_reqs = major_complete  # Use the proper completion check
        no_ge_reqs = not ge_remaining
        unit_cap_reached = total_units >= TOTAL_UNITS_REQUIRED
        
        debug_log(f"TERM {term_num} - TERMINATION CONDITIONS", {
            "major_requirements_complete": no_major_reqs,
            "no_ge_requirements": no_ge_reqs,
            "unit_cap_reached": unit_cap_reached,
            "should_terminate_requirements": no_major_reqs and no_ge_reqs,
            "should_terminate_units": unit_cap_reached
        })
        
        # Only terminate if both major and GE requirements are complete, OR if we've hit unit cap
        if (no_major_reqs and no_ge_reqs) or unit_cap_reached:
            debug_log("PATHWAY GENERATION COMPLETED", {
                "reason": "Requirements complete" if (no_major_reqs and no_ge_reqs) else "Unit cap reached",
                "final_units": total_units,
                "total_terms": term_num - 1,
                "major_complete": no_major_reqs,
                "ge_complete": no_ge_reqs
            })
            break
        
        # Get eligible courses for this term
        eligible_major = get_eligible_courses(completed, major_cands, prereqs)
        debug_log(f"TERM {term_num} - ELIGIBLE MAJOR COURSES", {
            "count": len(eligible_major),
            "course_codes": [e.get('courseCode') for e in eligible_major]
        })

        # Filter out already completed GE courses
        available_ge_courses = [
            course for course in ge_course_dicts
            if course.get('courseCode') not in completed
        ]
        
        debug_log(f"TERM {term_num} - AVAILABLE GE COURSES", {
            "total_ge_built": len(ge_course_dicts),
            "available_ge_after_filter": len(available_ge_courses),
            "available_ge_codes": [c.get('courseCode') for c in available_ge_courses]
        })

        # Check if we can make progress this term
        if not can_make_progress(eligible_major, available_ge_courses, completed_before_term):
            debug_log(f"TERM {term_num} - CANNOT MAKE PROGRESS", {
                "reason": "No new courses available that aren't already completed",
                "eligible_major_count": len(eligible_major),
                "available_ge_count": len(available_ge_courses),
                "completed_courses": len(completed)
            })
            break

        # Build eligibility list and ensure units are properly set
        eligible_course_dicts = []
        for e in eligible_major:
            # Get the correct units for this course
            actual_units = get_course_units(e['courseCode'], prereqs, articulated)
            
            course_dict = {
                'courseCode': e['courseCode'],
                'units': actual_units  # Always use the looked-up units
            }
            # Copy over any other properties from the original course, except units
            for key, value in e.items():
                if key not in course_dict and key != 'units':  # Don't overwrite our correct units
                    course_dict[key] = value
            eligible_course_dicts.append(course_dict)

        debug_log(f"TERM {term_num} - ELIGIBLE COURSES WITH UNITS", {
            "count": len(eligible_course_dicts),
            "courses": [(c['courseCode'], c['units']) for c in eligible_course_dicts]
        })

        total_eligible = eligible_course_dicts + available_ge_courses
        debug_log(f"TERM {term_num} - TOTAL ELIGIBLE COURSES", {
            "major_eligible": len(eligible_course_dicts),
            "ge_eligible": len(available_ge_courses),
            "total_eligible": len(total_eligible),
            "all_eligible_codes": [c['courseCode'] for c in total_eligible]
        })
        
        if not total_eligible:
            debug_log(f"TERM {term_num} - NO ELIGIBLE COURSES", {
                "major_candidates_exist": len(major_cands) > 0,
                "eligible_major_after_filter": len(eligible_major),
                "ge_courses_available": len(available_ge_courses),
                "possible_issue": "All remaining courses may have unmet prerequisites or are completed"
            })
            break
        
        debug_log(f"TERM {term_num} - CALLING UNIT BALANCER", {
            "total_eligible": len(total_eligible),
            "max_units": MAX_UNITS,
            "completed_before_balancer": sorted(list(completed))
        })
        
        # 4) Balance units
        selected, units, pruned_codes = select_courses_for_term(
            total_eligible,
            completed,
            uc_to_cc_map,
            all_cc_course_codes, 
            MAX_UNITS
        )
        
        debug_log(f"TERM {term_num} - UNIT BALANCER RESULTS", {
            "selected_count": len(selected),
            "selected_courses": [s.get('courseCode') for s in selected] if selected else [],
            "total_units": units,
            "pruned_codes": pruned_codes,
            "completed_after_balancer": sorted(list(completed))
        })

        if not selected:
            debug_log(f"TERM {term_num} - NO COURSES SELECTED", {
                "total_eligible_courses": len(total_eligible),
                "current_completed": len(completed),
                "unit_balancer_output": {"selected": selected, "units": units},
                "reason": "Unit balancer returned no courses"
            })
            break

        # Ensure selected courses have proper unit information
        for i, course in enumerate(selected):
            course_code = course['courseCode']
            if 'units' not in course or course['units'] is None:
                course['units'] = get_course_units(course_code, prereqs, articulated)
            selected[i] = course

        debug_log(f"TERM {term_num} - FINAL SELECTED COURSES", {
            "count": len(selected),
            "total_units": units,
            "courses_with_units": [(c['courseCode'], c['units']) for c in selected]
        })

        debug_log(f"TERM {term_num} - UPDATING STATE", {
            "completed_before": sorted(list(completed)),
            "courses_to_add": [c['courseCode'] for c in selected]
        })
        
        # 6) Update GE‐tracker state and completed courses
        for course in selected:
            code = course["courseCode"]
            
            # Add to completed set
            completed.add(code)
            debug_log(f"TERM {term_num} - ADDED TO COMPLETED", {
                "course_code": code,
                "course_units": course.get('units')
            })
            
            # Update GE tracker if it's a GE course
            if "reqIds" in course:
                for req in course["reqIds"]:
                    ge_tracker.add_completed_course(code, req)
                    debug_log(f"TERM {term_num} - GE REQUIREMENT FULFILLED", {
                        "course_code": code,
                        "ge_requirement": req
                    })
            else:
                ge_tracker.add_completed_course(code, course.get("tag", code))
        
        debug_log(f"TERM {term_num} - STATE AFTER UPDATE", {
            "completed_after": sorted(list(completed)),
            "completed_count": len(completed)
        })

        # 7) Record this term and update total units
        export_term_plan(f"Term {term_num}", selected, pathway)
        total_units += units
        term_num += 1
        
        debug_log(f"TERM {term_num-1} COMPLETED", {
            "term_units": units,
            "running_total_units": total_units,
            "completed_courses_count": len(completed),
            "remaining_major_candidates": "will be recalculated next term"
        })

        # Safety check to prevent infinite loops
        if term_num > 12:
            debug_log("MAXIMUM TERMS REACHED", {
                "max_terms": 12,
                "current_term": term_num,
                "reason": "Safety limit reached"
            })
            break
        
        # Additional progress check: if we didn't complete any new courses this term, break
        if completed == completed_before_term:
            debug_log(f"TERM {term_num-1} - NO PROGRESS MADE", {
                "reason": "No new courses were completed this term",
                "completed_before": sorted(list(completed_before_term)),
                "completed_after": sorted(list(completed)),
                "selected_courses": [c['courseCode'] for c in selected]
            })
            break

    debug_log("PATHWAY GENERATION FINAL RESULTS", {
        "total_terms": term_num - 1,
        "final_total_units": total_units,
        "target_units": TOTAL_UNITS_REQUIRED,
        "average_units_per_term": total_units / max(1, term_num - 1),
        "final_completed_courses": sorted(list(completed)),
        "final_completed_count": len(completed),
        "major_requirements_complete": is_major_requirement_complete(major_reqs, completed, articulated),
        "ge_requirements_remaining": ge_tracker.get_remaining_requirements(ge_pattern)
    })

    return pathway


# ─── Script Entrypoint ───────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        cc, uc, ge_pattern = get_user_inputs()
        debug_log("BUILDING FILE PATHS", {
            "cc": cc,
            "uc": uc,
            "ge_pattern": ge_pattern
        })
        paths = build_file_paths(cc, uc)

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

        # Save debug log
        debug_log_path = SCRIPT_DIR / "pathway_debug.txt"
        save_debug_log(str(debug_log_path))
            
    except Exception as e:
        debug_log("ERROR OCCURRED", {
            "error_message": str(e),
            "error_type": type(e).__name__
        })
        import traceback
        debug_log("FULL TRACEBACK", {
            "traceback": traceback.format_exc()
        })
        
        # Still save the debug log even if there's an error
        try:
            debug_log_path = SCRIPT_DIR / "pathway_debug.txt"
            save_debug_log(str(debug_log_path))
        except:
            pass