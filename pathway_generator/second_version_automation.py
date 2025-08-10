#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from itertools import combinations
import traceback
from datetime import datetime
import csv

# Import your existing modules
from major_checker import MajorRequirements, get_major_requirements
from ge_checker import GE_Tracker
from prereq_resolver import (
    get_eligible_courses,
    load_prereq_data,
    add_missing_prereqs,
    get_unlocker_courses,   # unlockers
)
from ge_helper import load_ge_lookup, build_ge_courses
from unit_balancer import select_courses_for_term
# from unit_balancer import prune_uc_to_cc_map   # not required here
# from plan_exporter import export_term_plan, save_plan_to_json  # not needed in automation

# ─── System-Specific Constants ─────────────────────────────────────────────────
QUARTER_SETTINGS = {
    'MAX_UNITS': 20,
    'TOTAL_UNITS_REQUIRED': 90,
    'TERMS_FOR_TWO_YEARS': 6
}

SEMESTER_SETTINGS = {
    'MAX_UNITS': 18,
    'TOTAL_UNITS_REQUIRED': 60,
    'TERMS_FOR_TWO_YEARS': 4
}

# ─── CC System Classifications ─────────────────────────────────────────────────
QUARTER_SYSTEM_CCS = [
    "de_anza", "foothill"
]

SEMESTER_SYSTEM_CCS = [
    "cabrillo", "chabot", "city_college_of_san_francisco", "cosumnes_river",
    "diablo_valley", "folsom_lake", "las_positas", "los_angeles_city_college",
    "los_angeles_pierce", "miracosta", "mt_san_jacinto", "orange_coast", "palomar"
]

# ─── Directory Setup ───────────────────────────────────────────────────────────
SCRIPT_DIR       = Path(__file__).parent.resolve()
PROJECT_ROOT     = SCRIPT_DIR.parent
ARTICULATION_DIR = PROJECT_ROOT / "articulated_courses_json"
PREREQS_DIR      = PROJECT_ROOT / "prerequisites"
COURSE_REQS_FILE = PROJECT_ROOT / "scraping" / "files" / "course_reqs.json"
RESULTS_DIR      = SCRIPT_DIR / "automation_results"

RESULTS_DIR.mkdir(exist_ok=True)

# ─── UC and GE Options ─────────────────────────────────────────────────────────
SUPPORTED_UCS = ["UCSD", "UCLA", "UCI", "UCR", "UCSB", "UCD", "UCB", "UCSC", "UCM"]
GE_PATTERNS = ["IGETC", "7CoursePattern"]  # allow both

# ─── Small helpers mirroring pathway_generator ─────────────────────────────────
def _dedupe_by_code(items):
    seen = set()
    out = []
    for it in items:
        c = it.get("courseCode") if isinstance(it, dict) else None
        if not c:
            continue
        if c in seen:
            continue
        seen.add(c)
        out.append(it)
    return out

def _get_course_units_from_prereqs_or_default(code, prereqs, default=3):
    meta = prereqs.get(code, {})
    units = meta.get('units')
    if units is None:
        units = meta.get('courseUnits')
    return units if units is not None else default

def _ensure_units(course_dict, prereqs, default=3):
    if not isinstance(course_dict, dict):
        return course_dict
    code = course_dict.get('courseCode')
    if not code:
        return course_dict
    if ('units' not in course_dict) or (course_dict['units'] is None):
        course_dict['units'] = _get_course_units_from_prereqs_or_default(code, prereqs, default)
    return course_dict

def _infer_ge_key(course):
    if not isinstance(course, dict):
        return None
    ge_key = course.get("geKey")
    if isinstance(ge_key, str) and ge_key:
        return ge_key.split("__")[0]
    req_ids = course.get("reqIds")
    if isinstance(req_ids, list) and req_ids:
        if isinstance(req_ids[0], str):
            return req_ids[0].split("__")[0]
    code = course.get("courseCode")
    if isinstance(code, str) and code.startswith("IG_"):
        return code.split("__")[0]
    return None

def _expand_ge_into_slots(ge_remaining, ge_course_dicts, prereqs, articulated, completed):
    base_templates = {c.get("courseCode"): c for c in ge_course_dicts if isinstance(c, dict)}
    expanded = []

    for ge_key, info in (ge_remaining or {}).items():
        need = int((info or {}).get("courses_remaining", 0) or 0)
        if need <= 0:
            continue

        base_template = base_templates.get(ge_key)
        if not base_template:
            base_template = {"courseCode": ge_key, "units": 3, "reqIds": [ge_key], "geKey": ge_key}
        else:
            base_template = dict(base_template)
            base_template = _ensure_units(base_template, prereqs, 3)
            if "geKey" not in base_template:
                base_template["geKey"] = ge_key
            if "reqIds" not in base_template:
                base_template["reqIds"] = [ge_key]

        base_in_completed = ge_key in completed

        if base_in_completed:
            for i in range(1, need + 1):
                expanded.append({
                    "courseCode": f"{ge_key}__slot{i}",
                    "units": base_template.get("units", 3),
                    "reqIds": [ge_key],
                    "geKey": ge_key
                })
        else:
            expanded.append(base_template)
            for i in range(1, max(need - 1, 0) + 1):
                expanded.append({
                    "courseCode": f"{ge_key}__slot{i}",
                    "units": base_template.get("units", 3),
                    "reqIds": [ge_key],
                    "geKey": ge_key
                })
    return expanded

def _can_make_progress(eligible_major, eligible_ge, completed_before_term):
    major_codes = {c.get('courseCode') for c in eligible_major}
    ge_codes = {c.get('courseCode') for c in eligible_ge}
    new_codes = (major_codes | ge_codes) - set(completed_before_term)
    return len(new_codes) > 0

# ─── Core automation pieces ───────────────────────────────────────────────────
def get_system_settings(cc_name):
    if cc_name in QUARTER_SYSTEM_CCS:
        return QUARTER_SETTINGS, "quarter"
    elif cc_name in SEMESTER_SYSTEM_CCS:
        return SEMESTER_SETTINGS, "semester"
    else:
        print(f"⚠️ Warning: {cc_name} not classified as quarter or semester system!")
        print(f"   Using semester settings as default. Please add to appropriate list.")
        return SEMESTER_SETTINGS, "semester"

def discover_cc_files():
    cc_files = {}
    prereq_mapping = {}

    if not ARTICULATION_DIR.exists():
        print(f"❌ Articulation directory not found: {ARTICULATION_DIR}")
        return {}, {}

    if not PREREQS_DIR.exists():
        print(f"❌ Prerequisites directory not found: {PREREQS_DIR}")
        return {}, {}

    print("🔍 Discovering CC files...")

    prereq_files = {}
    print(f"📁 Scanning prerequisite files in: {PREREQS_DIR}")
    for prereq_file in PREREQS_DIR.glob("*_prereqs.json"):
        filename = prereq_file.stem
        base_name = filename.replace("_prereqs", "")
        if base_name.endswith("_college") and base_name != "los_angeles_city_college":
            base_name = base_name[:-8]
        cc_name = base_name.lower().replace(" ", "_")
        prereq_files[cc_name] = prereq_file.name

    print(f"📁 Scanning articulation files in: {ARTICULATION_DIR}")
    articulation_files = {}
    for art_file in ARTICULATION_DIR.glob("*_articulation.json"):
        filename = art_file.stem
        base_name = filename.replace("_articulation", "")
        if base_name.lower() == "city_college_of_san_francisco_college":
            base_name = "city_college_of_san_francisco"
        elif base_name.endswith("_college") or base_name.endswith("_College"):
            base_name = base_name.replace("_college", "").replace("_College", "")
        normalized_name = base_name.lower().replace(" ", "_")
        articulation_files[normalized_name] = art_file.name

    print(f"\n🔗 Matching prerequisite and articulation files...")
    matched_count = 0
    for cc_name, prereq_filename in prereq_files.items():
        if cc_name in articulation_files:
            cc_files[cc_name] = articulation_files[cc_name]
            prereq_mapping[cc_name] = prereq_filename
            matched_count += 1
            continue

        possible_variations = []
        if cc_name == "diablo_valley":
            possible_variations.extend(["diablo_valley_college"])
        elif cc_name == "los_angeles_pierce":
            possible_variations.extend(["los_angeles_pierce_college"])
        elif cc_name == "palomar":
            possible_variations.extend(["palomar_college"])
        elif cc_name == "miracosta":
            possible_variations.extend(["miracosta_college"])
        elif cc_name in ["mt._san_jacinto", "mt_san_jacinto"]:
            possible_variations.extend(["mt._san_jacinto_college", "mt_san_jacinto", "mt_san_jacinto_college"])
        elif cc_name == "los_angeles_city_college":
            possible_variations.extend(["los_angeles_city", "la_city_college"])
        elif cc_name == "city_college_of_san_francisco":
            possible_variations.extend(["city_college_of_san_francisco_college"])

        if "college" not in cc_name:
            possible_variations.append(f"{cc_name}_college")

        cc_parts = cc_name.replace("_", " ").replace(".", "").split()
        if len(cc_parts) > 1:
            possible_variations.extend([
                "_".join(cc_parts),
                "_".join(cc_parts) + "_college"
            ])

        found_match = False
        for variation in possible_variations:
            variation = variation.lower()
            if variation in articulation_files:
                cc_files[cc_name] = articulation_files[variation]
                prereq_mapping[cc_name] = prereq_filename
                matched_count += 1
                found_match = True
                break

        if not found_match:
            print(f"⚠️ No matching articulation file found for {cc_name} (prereq: {prereq_filename})")

    print(f"\n🎯 Successfully matched {matched_count} CCs with both files")
    return cc_files, prereq_mapping

def load_json_silent(path):
    try:
        with open(path, "r", encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {path}: {e}")
        return None

def generate_uc_combinations(max_combinations=None):
    all_combinations = []
    for r in range(1, len(SUPPORTED_UCS) + 1):
        for combo in combinations(SUPPORTED_UCS, r):
            all_combinations.append(list(combo))
            if max_combinations and len(all_combinations) >= max_combinations:
                return all_combinations
    return all_combinations

def generate_pathway_automated(art_path, prereq_path, ge_path, major_path, cc_id, uc_list, ge_pattern, system_settings):
    """
    Mirror the main generator’s semantics:
      - Use unlockers
      - Expand GE into per-slot placeholders
      - Stop only when: major complete AND GE complete AND units >= required
      - Big safety cap and 'no progress possible' break
    """
    try:
        MAX_UNITS = system_settings['MAX_UNITS']
        TOTAL_UNITS_REQUIRED = system_settings['TOTAL_UNITS_REQUIRED']
        SAFETY_LIMIT = 999

        articulated = load_json_silent(art_path)
        if not articulated:
            return {'success': False, 'error': 'Missing or invalid articulated JSON'}

        prereqs = load_prereq_data(str(prereq_path))
        ge_data = load_json_silent(ge_path)
        if not ge_data:
            return {'success': False, 'error': 'Missing or invalid GE JSON'}

        ge_tracker = GE_Tracker(ge_data)
        ge_tracker.load_pattern(ge_pattern)

        major_reqs = get_major_requirements(
            str(major_path),
            cc_id,
            uc_list,
            str(ARTICULATION_DIR)
        )

        completed = set()
        total_units = 0
        term_num = 1
        terms_data = []

        ge_lookup = load_ge_lookup(PREREQS_DIR / "ge_reqs.json")

        major_map = MajorRequirements.get_cc_to_uc_map(cc_id, uc_list, art_path)
        uc_to_cc_map = {}
        for uc, cmap in major_map.items():
            for uc_course, blocks in cmap.items():
                uc_to_cc_map.setdefault(uc_course, []).extend(blocks)

        all_cc_course_codes = set(prereqs.keys())

        while term_num <= SAFETY_LIMIT:
            completed_before_term = completed.copy()

            # Remaining majors + add missing prereqs
            major_cands = major_reqs.get_remaining_courses(completed, articulated)
            major_cands = add_missing_prereqs(major_cands, prereqs, completed)

            # Ensure units on candidates
            major_cands = [_ensure_units(dict(c), prereqs) for c in major_cands if isinstance(c, dict)]

            # Major completion
            try:
                remaining_major = major_reqs.get_remaining_courses(completed, articulated)
                major_done = (len(remaining_major) == 0)
            except Exception:
                major_done = False

            # GE remaining
            ge_remaining = ge_tracker.get_remaining_requirements(ge_pattern)
            ge_done = (not ge_remaining)

            # Units condition
            min_units_met = (total_units >= TOTAL_UNITS_REQUIRED)

            # Termination
            if major_done and ge_done and min_units_met:
                break

            # Build base GE placeholders
            base_ge_courses = build_ge_courses(ge_remaining, ge_lookup, unit_count=3)
            base_ge_courses = [_ensure_units(c, prereqs) for c in base_ge_courses]

            # Expand multi-course GE areas into slots
            ge_course_dicts = _expand_ge_into_slots(ge_remaining, base_ge_courses, prereqs, articulated, completed)

            # Eligible majors this term
            eligible_major = get_eligible_courses(completed, major_cands, prereqs)

            # Identify blocked majors to find unlockers
            eligible_codes = {e['courseCode'] for e in eligible_major}
            blocked_major = []
            for c in major_cands:
                code = c.get('courseCode')
                if code and code not in eligible_codes and code not in completed:
                    blocked_major.append({'courseCode': code, 'units': _get_course_units_from_prereqs_or_default(code, prereqs)})

            unlockers = get_unlocker_courses(blocked_major, completed, prereqs)
            # Tag unlockers
            for u in unlockers:
                u['tag'] = 'UNLOCKER'

            # Merge unlockers + eligible majors, ensure units
            merged_major_pool = _dedupe_by_code([_ensure_units(u, prereqs) for u in (unlockers + eligible_major)])

            # Available GE items (include slots not yet taken)
            available_ge_courses = [c for c in ge_course_dicts if c.get('courseCode') not in completed]

            # If requirements done but units short, pad with electives (simple heuristic)
            if major_done and ge_done and not min_units_met:
                padding = []
                counter = 0
                ELECTIVE_PADDING_MAX_POOL = 50
                for code in sorted(all_cc_course_codes):
                    if counter >= ELECTIVE_PADDING_MAX_POOL:
                        break
                    if code in completed:
                        continue
                    if code.startswith("IG_"):
                        continue
                    if " " not in code and not any(code.startswith(p) for p in ["CS", "MATH", "PHYS", "CHEM", "BIO", "ENGL", "HIST", "PHIL", "ECON", "PSY", "SOC"]):
                        continue
                    units = _get_course_units_from_prereqs_or_default(code, prereqs)
                    padding.append({"courseCode": code, "units": units, "tag": "ELECTIVE"})
                    counter += 1
                available_ge_courses += padding

            # No progress possible?
            if not _can_make_progress(merged_major_pool, available_ge_courses, completed_before_term):
                break

            # Build eligible list for balancer
            eligible_course_dicts = []
            for e in merged_major_pool:
                code = e['courseCode']
                units = _get_course_units_from_prereqs_or_default(code, prereqs)
                course_dict = {'courseCode': code, 'units': units}
                # carry metadata except units
                for k, v in e.items():
                    if k not in course_dict and k != 'units':
                        course_dict[k] = v
                eligible_course_dicts.append(course_dict)

            total_eligible = eligible_course_dicts + available_ge_courses
            if not total_eligible:
                break

            # Balance units
            selected, units, pruned_codes = select_courses_for_term(
                total_eligible, completed, uc_to_cc_map, all_cc_course_codes, MAX_UNITS
            )
            if not selected:
                break

            # Ensure units on selected
            for i, course in enumerate(selected):
                code = course['courseCode']
                if 'units' not in course or course['units'] is None:
                    course['units'] = _get_course_units_from_prereqs_or_default(code, prereqs)
                selected[i] = course

            # Update state + GE tracker (pass TAGS AS LISTS)
            for course in selected:
                code = course["courseCode"]
                completed.add(code)
                ge_key = _infer_ge_key(course)
                if ge_key is not None:
                    ge_tracker.add_completed_course(code, [ge_key])
                else:
                    credited = course.get("tag", code)
                    ge_tracker.add_completed_course(code, [credited])

            # Record term
            terms_data.append({
                'term': term_num,
                'units': units,
                'courses': len(selected),
                'course_codes': [c['courseCode'] for c in selected]
            })
            total_units += units
            term_num += 1

            # No progress this term guard
            if completed == completed_before_term:
                break

        return {
            'success': True,
            'total_terms': len(terms_data),
            'total_units': total_units,
            'terms': terms_data,
            'over_2_years': len(terms_data) > system_settings['TERMS_FOR_TWO_YEARS'],
            'meets_unit_requirement': total_units >= TOTAL_UNITS_REQUIRED,
            'system_settings': system_settings
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

def save_results_for_cc(cc_name, cc_results, ge_pattern, timestamp, system_type):
    cc_folder = RESULTS_DIR / cc_name
    cc_folder.mkdir(exist_ok=True)

    cc_json_path = cc_folder / f"{cc_name}_{ge_pattern}_{system_type}_{timestamp}.json"
    with open(cc_json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'cc_name': cc_name,
            'system_type': system_type,
            'ge_pattern': ge_pattern,
            'results': cc_results,
            'summary': {
                'total_combinations': len(cc_results),
                'successful': len([r for r in cc_results if r['status'] == 'success']),
                'failed': len([r for r in cc_results if r['status'] == 'failed']),
                'timestamp': timestamp
            }
        }, f, indent=2)

    cc_csv_path = cc_folder / f"{cc_name}_{ge_pattern}_{system_type}_{timestamp}.csv"
    with open(cc_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'cc', 'system_type', 'ucs', 'uc_count', 'ge_pattern', 'status', 'total_terms', 'total_units',
            'over_2_years', 'units_term_1', 'units_term_2', 'units_term_3',
            'units_term_4', 'units_term_5', 'units_term_6', 'error'
        ])
        writer.writeheader()
        for result in cc_results:
            row = {
                'cc': result['cc'],
                'system_type': result.get('system_type', system_type),
                'ucs': result['ucs'],
                'uc_count': result['uc_count'],
                'ge_pattern': result['ge_pattern'],
                'status': result['status'],
                'total_terms': result['total_terms'],
                'total_units': result['total_units'],
                'over_2_years': result['over_2_years'],
                'error': result.get('error', '')
            }
            for i in range(1, 7):
                term_key = f'units_term_{i}'
                if i <= len(result['terms_detail']):
                    row[term_key] = result['terms_detail'][i-1]['units']
                else:
                    row[term_key] = 0
            writer.writerow(row)

def run_automation(ge_pattern_filter=None):
    if ge_pattern_filter:
        print(f"🚀 Starting Pathway Generator Automation - {ge_pattern_filter} ONLY")
        patterns_to_test = [ge_pattern_filter]
    else:
        print("🚀 Starting Pathway Generator Automation - ALL GE PATTERNS")
        patterns_to_test = GE_PATTERNS

    print("=" * 60)

    cc_files, prereq_mapping = discover_cc_files()
    if not cc_files:
        print("❌ No CC files found with both articulation and prerequisite files. Exiting.")
        return

    print(f"📁 Found {len(cc_files)} CCs with both articulation and prerequisite files")

    quarter_ccs = [cc for cc in cc_files.keys() if cc in QUARTER_SYSTEM_CCS]
    semester_ccs = [cc for cc in cc_files.keys() if cc in SEMESTER_SYSTEM_CCS]
    unclassified_ccs = [cc for cc in cc_files.keys() if cc not in QUARTER_SYSTEM_CCS and cc not in SEMESTER_SYSTEM_CCS]

    print(f"\n📊 System Classifications:")
    print(f"  Quarter System ({len(quarter_ccs)}): {quarter_ccs}")
    print(f"  Semester System ({len(semester_ccs)}): {semester_ccs}")
    if unclassified_ccs:
        print(f"  Unclassified ({len(unclassified_ccs)}): {unclassified_ccs}")
        print(f"    ⚠️ These will use semester settings by default")

    print("\n🎯 Generating UC combinations...")
    uc_combinations = generate_uc_combinations()
    print(f"🎯 Generated {len(uc_combinations)} UC combinations")

    results = []
    cc_results = {}
    summary_stats = {
        'total_runs': 0,
        'successful_runs': 0,
        'failed_runs': 0,
        'by_cc': {},
        'by_ge_pattern': {},
        'by_uc_count': {},
        'by_system_type': {'quarter': {'runs': 0, 'success': 0}, 'semester': {'runs': 0, 'success': 0}}
    }

    ge_path = PREREQS_DIR / "ge_reqs.json"
    if not ge_path.exists():
        print(f"❌ GE requirements file not found: {ge_path}")
        return
    if not COURSE_REQS_FILE.exists():
        print(f"❌ Course requirements file not found: {COURSE_REQS_FILE}")
        return

    total_combinations = len(cc_files) * len(uc_combinations) * len(patterns_to_test)
    print(f"🔢 Total combinations to test: {total_combinations}")
    print("⏳ This may take a while...\n")

    current_run = 0
    for cc_name in cc_files.keys():
        system_settings, system_type = get_system_settings(cc_name)
        print(f"🏫 Processing CC: {cc_name} ({system_type.upper()} system)")
        print(f"   Settings: {system_settings['MAX_UNITS']} max units, {system_settings['TOTAL_UNITS_REQUIRED']} total required, {system_settings['TERMS_FOR_TWO_YEARS']} terms = 2 years")

        art_path = ARTICULATION_DIR / cc_files[cc_name]
        prereq_path = PREREQS_DIR / prereq_mapping[cc_name]

        summary_stats['by_cc'][cc_name] = {'success': 0, 'failed': 0, 'system_type': system_type}
        cc_results[cc_name] = []

        for uc_combo in uc_combinations:
            for ge_pattern in patterns_to_test:
                current_run += 1
                uc_combo_str = "+".join(sorted(uc_combo))
                uc_count = len(uc_combo)

                print(f"  [{current_run}/{total_combinations}] {cc_name} ({system_type}) -> {uc_combo_str} ({ge_pattern}) - {uc_count} UCs")

                summary_stats['total_runs'] += 1
                summary_stats['by_system_type'][system_type]['runs'] += 1

                result = generate_pathway_automated(
                    art_path, prereq_path, ge_path, COURSE_REQS_FILE,
                    cc_name, uc_combo, ge_pattern, system_settings
                )

                if result and result.get('success'):
                    summary_stats['successful_runs'] += 1
                    summary_stats['by_cc'][cc_name]['success'] += 1
                    summary_stats['by_ge_pattern'][ge_pattern] = summary_stats['by_ge_pattern'].get(ge_pattern, 0) + 1
                    summary_stats['by_uc_count'][uc_count] = summary_stats['by_uc_count'].get(uc_count, 0) + 1
                    summary_stats['by_system_type'][system_type]['success'] += 1

                    result_entry = {
                        'cc': cc_name,
                        'system_type': system_type,
                        'ucs': uc_combo_str,
                        'uc_count': uc_count,
                        'ge_pattern': ge_pattern,
                        'total_terms': result['total_terms'],
                        'total_units': result['total_units'],
                        'over_2_years': result['over_2_years'],
                        'terms_detail': result['terms'],
                        'status': 'success',
                        'settings_used': result['system_settings']
                    }
                    results.append(result_entry)
                    cc_results[cc_name].append(result_entry)
                    print(f"    ✅ Success: {result['total_terms']} terms, {result['total_units']} units")

                else:
                    summary_stats['failed_runs'] += 1
                    summary_stats['by_cc'][cc_name]['failed'] += 1
                    error_msg = result.get('error', 'Unknown error') if result else 'Generation failed'
                    result_entry = {
                        'cc': cc_name,
                        'system_type': system_type,
                        'ucs': uc_combo_str,
                        'uc_count': uc_count,
                        'ge_pattern': ge_pattern,
                        'total_terms': 0,
                        'total_units': 0,
                        'over_2_years': False,
                        'terms_detail': [],
                        'status': 'failed',
                        'error': error_msg
                    }
                    results.append(result_entry)
                    cc_results[cc_name].append(result_entry)
                    print(f"    ❌ Failed: {error_msg}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ge_suffix = f"_{ge_pattern_filter}" if ge_pattern_filter else "_ALL"

    print(f"\n💾 Saving individual CC files...")
    for cc_name, cc_result_list in cc_results.items():
        if cc_result_list:
            try:
                _, system_type = get_system_settings(cc_name)
                save_results_for_cc(cc_name, cc_result_list, ge_pattern_filter or "ALL", timestamp, system_type)
                print(f"  📁 {cc_name} ({system_type}): {len(cc_result_list)} combinations saved")
            except Exception as e:
                print(f"  ❌ {cc_name}: Error during save - {e}")
        else:
            print(f"  ⏭️ {cc_name}: No results to save")

    print(f"💾 Saving master files...")
    results_json_path = RESULTS_DIR / f"pathway_results{ge_suffix}_{timestamp}.json"
    with open(results_json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': summary_stats,
            'results': results,
            'metadata': {
                'timestamp': timestamp,
                'total_combinations': len(results),
                'cc_files_processed': list(cc_files.keys()),
                'ge_patterns_tested': patterns_to_test,
                'uc_combinations_count': len(uc_combinations),
                'system_settings': {
                    'quarter': QUARTER_SETTINGS,
                    'semester': SEMESTER_SETTINGS
                },
                'cc_classifications': {
                    'quarter_ccs': [c for c in cc_files.keys() if c in QUARTER_SYSTEM_CCS],
                    'semester_ccs': [c for c in cc_files.keys() if c in SEMESTER_SYSTEM_CCS],
                    'unclassified_ccs': [c for c in cc_files.keys() if c not in QUARTER_SYSTEM_CCS and c not in SEMESTER_SYSTEM_CCS]
                }
            }
        }, f, indent=2)

    csv_path = RESULTS_DIR / f"pathway_summary{ge_suffix}_{timestamp}.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'cc', 'system_type', 'ucs', 'uc_count', 'ge_pattern', 'status', 'total_terms', 'total_units',
            'over_2_years', 'units_term_1', 'units_term_2', 'units_term_3',
            'units_term_4', 'units_term_5', 'units_term_6', 'error'
        ])
        writer.writeheader()
        for result in results:
            row = {
                'cc': result['cc'],
                'system_type': result['system_type'],
                'ucs': result['ucs'],
                'uc_count': result['uc_count'],
                'ge_pattern': result['ge_pattern'],
                'status': result['status'],
                'total_terms': result['total_terms'],
                'total_units': result['total_units'],
                'over_2_years': result['over_2_years'],
                'error': result.get('error', '')
            }
            for i in range(1, 7):
                term_key = f'units_term_{i}'
                if i <= len(result['terms_detail']):
                    row[term_key] = result['terms_detail'][i-1]['units']
                else:
                    row[term_key] = 0
            writer.writerow(row)

    print("\n" + "=" * 60)
    print("🎉 AUTOMATION COMPLETE!")
    print("=" * 60)
    print(f"📊 Total runs: {summary_stats['total_runs']}")
    print(f"✅ Successful: {summary_stats['successful_runs']}")
    print(f"❌ Failed: {summary_stats['failed_runs']}")
    rate = (summary_stats['successful_runs'] / summary_stats['total_runs'] * 100) if summary_stats['total_runs'] else 0.0
    print(f"📈 Success rate: {rate:.1f}%")

    print(f"\n📁 Master Results saved to:")
    print(f"  JSON: {results_json_path}")
    print(f"  CSV:  {csv_path}")

    print(f"\n📂 Individual CC folders in: {RESULTS_DIR}")

    print(f"\n🏫 CC Success Rates:")
    for cc, stats in summary_stats['by_cc'].items():
        total = stats['success'] + stats['failed']
        system_type = stats['system_type']
        if total > 0:
            r = stats['success'] / total * 100
            print(f"  {cc} ({system_type}): {r:.1f}% ({stats['success']}/{total})")

    print(f"\n🎯 Success Rates by UC Count:")
    for uc_count in sorted(summary_stats['by_uc_count'].keys()):
        print(f"  {uc_count} UC{'s' if uc_count > 1 else ''}: {summary_stats['by_uc_count'][uc_count]} successful runs")

    print(f"\n📋 System Settings Used:")
    print(f"  Quarter: {QUARTER_SETTINGS}")
    print(f"  Semester: {SEMESTER_SETTINGS}")

    return results

def print_cc_classification_helper():
    print("\n" + "=" * 60)
    print("🏫 CC CLASSIFICATION HELPER")
    print("=" * 60)
    cc_files, _ = discover_cc_files()
    if not cc_files:
        print("❌ No CC files found. Run discovery first.")
        return
    print(f"📋 Found {len(cc_files)} CCs that need classification:\n")
    print("QUARTER_SYSTEM_CCS = [")
    for cc in sorted(cc_files.keys()):
        print(f'    # "{cc}",')
    print("]\n")
    print("SEMESTER_SYSTEM_CCS = [")
    for cc in sorted(cc_files.keys()):
        print(f'    # "{cc}",')
    print("]")
    print("\n💡 Tip: Most California CCs use semester system. Known quarter: De Anza, Foothill.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].upper()
        if arg in ("HELP", "CLASSIFY"):
            print_cc_classification_helper()
            sys.exit(0)
        all_supported = ["IGETC", "7COURSEPATTERN", "7COURSEPATTERN".upper()]
        if arg in ["IGETC", "7COURSEPATTERN"]:
            run_automation("IGETC" if arg == "IGETC" else "7CoursePattern")
        else:
            print(f"❌ Invalid GE pattern. Available: IGETC, 7CoursePattern")
            print("Usage:")
            print("  python automated_pathway_generator.py IGETC")
            print("  python automated_pathway_generator.py 7CoursePattern")
            print("  python automated_pathway_generator.py help")
    else:
        # Run all patterns by default
        for i, pattern in enumerate(GE_PATTERNS):
            if i > 0:
                print("\n" + "="*80 + "\n")
            print(f"🔄 Running {pattern} ({i+1}/{len(GE_PATTERNS)})...")
            run_automation(pattern)