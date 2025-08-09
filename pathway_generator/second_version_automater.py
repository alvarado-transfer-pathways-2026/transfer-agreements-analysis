#semester: 12, 15, 18
#quarter: 12, 16, 20
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
from prereq_resolver import get_eligible_courses, load_prereq_data, add_missing_prereqs
from ge_helper import load_ge_lookup, build_ge_courses
from unit_balancer import select_courses_for_term, prune_uc_to_cc_map
from plan_exporter import export_term_plan, save_plan_to_json

# ─── System-Specific Constants ─────────────────────────────────────────────────
# Quarter System Settings
QUARTER_SETTINGS = {
    'MAX_UNITS': 12,            # Units per quarter
    'TOTAL_UNITS_REQUIRED': 90, # Total units for transfer (quarters typically need more)
    'TERMS_FOR_TWO_YEARS': 6    # 6 quarters = 2 years
}

# Semester System Settings  
SEMESTER_SETTINGS = {
    'MAX_UNITS': 12,            # Units per semester
    'TOTAL_UNITS_REQUIRED': 60, # Total units for transfer
    'TERMS_FOR_TWO_YEARS': 4    # 4 semesters = 2 years
}

# ─── CC System Classifications ─────────────────────────────────────────────────
# TODO: Add your CC names to the appropriate list below
QUARTER_SYSTEM_CCS = [
    "de_anza", "foothill"
    # Add quarter system CC names here (exact names as they appear in your files)
    # Example: "de_anza", "foothill", etc.
]

SEMESTER_SYSTEM_CCS = [
    # Add semester system CC names here (exact names as they appear in your files)  
    # Example: "santa_monica", "los_angeles_city_college", etc.
    "cabrillo", "chabot", "city_college_of_san_francisco", "cosumnes_river",
    "diablo_valley", "folsom_lake", "las_positas", "los_angeles_city", "los_angeles_pierce"
    "miracosta", "mt_san_jacinto", "orange_coast", "palomar"
]

# ─── Directory Setup ───────────────────────────────────────────────────────────
SCRIPT_DIR       = Path(__file__).parent.resolve()
PROJECT_ROOT     = SCRIPT_DIR.parent
ARTICULATION_DIR = PROJECT_ROOT / "articulated_courses_json"
PREREQS_DIR      = PROJECT_ROOT / "prerequisites"
COURSE_REQS_FILE = PROJECT_ROOT / "scraping" / "files" / "course_reqs.json"
RESULTS_DIR      = SCRIPT_DIR / "automation_results"

# Create results directory
RESULTS_DIR.mkdir(exist_ok=True)

# ─── UC and GE Options ─────────────────────────────────────────────────────────
SUPPORTED_UCS = ["UCSD", "UCLA", "UCI", "UCR", "UCSB", "UCD", "UCB", "UCSC", "UCM"]
GE_PATTERNS = ["IGETC"]

def get_system_settings(cc_name):
    """Get the appropriate system settings for a given CC."""
    if cc_name in QUARTER_SYSTEM_CCS:
        return QUARTER_SETTINGS, "quarter"
    elif cc_name in SEMESTER_SYSTEM_CCS:
        return SEMESTER_SETTINGS, "semester"
    else:
        print(f"⚠️ Warning: {cc_name} not classified as quarter or semester system!")
        print(f"   Using semester settings as default. Please add to appropriate list.")
        return SEMESTER_SETTINGS, "semester"

def discover_cc_files():
    """Discover CC files that have both articulation AND prerequisite files."""
    cc_files = {}
    prereq_mapping = {}
    
    if not ARTICULATION_DIR.exists():
        print(f"❌ Articulation directory not found: {ARTICULATION_DIR}")
        return {}, {}
    
    if not PREREQS_DIR.exists():
        print(f"❌ Prerequisites directory not found: {PREREQS_DIR}")
        return {}, {}
    
    print("🔍 Discovering CC files...")
    
    # First, discover all prerequisite files with improved name extraction
    prereq_files = {}
    print(f"📁 Scanning prerequisite files in: {PREREQS_DIR}")
    for prereq_file in PREREQS_DIR.glob("*_prereqs.json"):
        filename = prereq_file.stem
        print(f"Processing prereq file: {filename}")  # DEBUG
        
        # Remove _prereqs suffix first
        base_name = filename.replace("_prereqs", "")
        print(f"  After removing _prereqs: {base_name}")  # DEBUG
        
        # Special handling for files that have _college before _prereqs
        # BUT NOT for los_angeles_city_college - we want to keep that as-is
        if base_name.endswith("_college") and base_name != "los_angeles_city_college":
            original_base = base_name
            base_name = base_name[:-8]  # Remove _college suffix
            print(f"  Removed _college suffix: {original_base} -> {base_name}")  # DEBUG
        
        # Normalize the name to lowercase with underscores
        cc_name = base_name.lower().replace(" ", "_")
        print(f"  Final normalized name: {cc_name}")  # DEBUG
        
        prereq_files[cc_name] = prereq_file.name
        print(f"Found prereq file: {cc_name} -> {prereq_file.name}")
        
        # Special debug for LA City College
        if "los_angeles" in cc_name and "city" in cc_name:
            print(f"  *** LA CITY PREREQ DEBUG: {cc_name} ***")
    
    print(f"📁 Scanning articulation files in: {ARTICULATION_DIR}")
    
    # Create a mapping of normalized names to actual articulation files
    articulation_files = {}
    for art_file in ARTICULATION_DIR.glob("*_articulation.json"):
        filename = art_file.stem
        print(f"Processing articulation file: {filename}")  # DEBUG
        
        # Remove _articulation suffix
        base_name = filename.replace("_articulation", "")
        print(f"  After removing _articulation: {base_name}")  # DEBUG
        
        # Handle the special case for City_College_Of_San_Francisco_college
        if base_name.lower() == "city_college_of_san_francisco_college":
            base_name = "city_college_of_san_francisco"
            print(f"  Special case for SF: {base_name}")  # DEBUG
        elif base_name.endswith("_college") or base_name.endswith("_College"):
            # Remove _college or _College suffix if present
            original_base = base_name
            base_name = base_name.replace("_college", "").replace("_College", "")
            print(f"  Removed college suffix: {original_base} -> {base_name}")  # DEBUG
        
        # Normalize to lowercase with underscores, handle spaces and mixed case
        normalized_name = base_name.lower().replace(" ", "_")
        print(f"  Final normalized name: {normalized_name}")  # DEBUG
        
        articulation_files[normalized_name] = art_file.name
        print(f"Found articulation file: {normalized_name} -> {art_file.name}")
        
        # Special debug for LA City College
        if "los_angeles" in normalized_name and "city" in normalized_name:
            print(f"  *** LA CITY DEBUG: {normalized_name} ***")
    
    print(f"\n🔗 Matching prerequisite and articulation files...")
    
    # Now match prerequisite files to articulation files
    matched_count = 0
    for cc_name, prereq_filename in prereq_files.items():
        print(f"\n🔍 Looking for match for: {cc_name}")
        
        # Direct match first
        if cc_name in articulation_files:
            cc_files[cc_name] = articulation_files[cc_name]
            prereq_mapping[cc_name] = prereq_filename
            print(f"✅ Direct match: {cc_name} -> {articulation_files[cc_name]} + {prereq_filename}")
            matched_count += 1
            continue
        
        # Try variations with common patterns
        possible_variations = []
        
        # Handle specific known mismatches with more comprehensive matching
        if cc_name == "diablo_valley":
            possible_variations.extend(["diablo_valley_college"])
        elif cc_name == "los_angeles_pierce":
            possible_variations.extend(["los_angeles_pierce_college"])
        elif cc_name == "palomar":
            possible_variations.extend(["palomar_college"])
        elif cc_name == "miracosta":
            possible_variations.extend(["miracosta_college"])
        elif cc_name == "mt._san_jacinto":
            possible_variations.extend(["mt._san_jacinto_college", "mt_san_jacinto", "mt_san_jacinto_college"])
        elif cc_name == "los_angeles_city_college":
            # This should match directly, but add variations just in case
            possible_variations.extend(["los_angeles_city", "la_city_college"])
        elif cc_name == "city_college_of_san_francisco":
            # This should now match directly due to special handling above
            possible_variations.extend(["city_college_of_san_francisco_college"])
        
        # General variations - add college suffix
        if "college" not in cc_name:
            possible_variations.append(f"{cc_name}_college")
        
        # Try with different word separators and handle periods
        cc_parts = cc_name.replace("_", " ").replace(".", "").split()
        if len(cc_parts) > 1:
            # Try with different separators
            possible_variations.extend([
                "_".join(cc_parts),
                "_".join(cc_parts) + "_college"
            ])
        
        # Try to find matches
        found_match = False
        for variation in possible_variations:
            variation = variation.lower()
            print(f"  Trying: {variation}")
            if variation in articulation_files:
                cc_files[cc_name] = articulation_files[variation]
                prereq_mapping[cc_name] = prereq_filename
                print(f"✅ Variation match: {cc_name} -> {articulation_files[variation]} + {prereq_filename}")
                matched_count += 1
                found_match = True
                break
        
        if not found_match:
            print(f"⚠️ No matching articulation file found for {cc_name}")
            print(f"   Prereq file: {prereq_filename}")
            print(f"   Available articulation files starting with similar names:")
            # Show articulation files that might be close matches
            similar = [name for name in articulation_files.keys() 
                      if any(part in name for part in cc_name.split("_")[:2])]
            for sim in similar[:3]:
                print(f"     - {sim}")
    
    print(f"\n🎯 Successfully matched {matched_count} CCs with both files")
    print(f"📋 Matched CCs: {list(cc_files.keys())}")
    return cc_files, prereq_mapping

def load_json(path):
    """Load JSON file with error handling."""
    try:
        with open(path, "r", encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {path}: {e}")
        return None

def generate_uc_combinations(max_combinations=None):
    """Generate all possible UC combinations (1 to 9 UCs)."""
    all_combinations = []
    
    for r in range(1, len(SUPPORTED_UCS) + 1):
        for combo in combinations(SUPPORTED_UCS, r):
            all_combinations.append(list(combo))
            if max_combinations and len(all_combinations) >= max_combinations:
                return all_combinations
    
    return all_combinations

def generate_pathway_automated(art_path, prereq_path, ge_path, major_path, cc_id, uc_list, ge_pattern, system_settings):
    """Modified pathway generation that returns summary statistics."""
    try:
        # Use the system-specific settings
        MAX_UNITS = system_settings['MAX_UNITS']
        TOTAL_UNITS_REQUIRED = system_settings['TOTAL_UNITS_REQUIRED'] 
        TERMS_FOR_TWO_YEARS = system_settings['TERMS_FOR_TWO_YEARS']
        
        articulated = load_json(art_path)
        if not articulated:
            return None
            
        prereqs = load_prereq_data(prereq_path)
        ge_data = load_json(ge_path)
        
        if not ge_data:
            return None
        
        # Initialize the classes
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
        pathway = []
        terms_data = []

        ge_lookup = load_ge_lookup(PREREQS_DIR / "ge_reqs.json")

        # Get major course mapping
        major_map = MajorRequirements.get_cc_to_uc_map(cc_id, uc_list, art_path)
        uc_to_cc_map = {}
        for uc, cmap in major_map.items():
            for uc_course, blocks in cmap.items():
                uc_to_cc_map.setdefault(uc_course, []).extend(blocks)

        major_cands = major_reqs.get_remaining_courses(completed, articulated)
        major_cands = add_missing_prereqs(major_cands, prereqs, completed)

        # Limit iterations to prevent infinite loops
        max_terms = 12
        
        while term_num <= max_terms:
            # Get remaining requirements
            ge_remaining = ge_tracker.get_remaining_requirements(ge_pattern)
            
            if not major_cands and not ge_remaining:
                break
            
            ge_course_dicts = build_ge_courses(ge_remaining, ge_lookup, unit_count=3)
            
            # Filter eligible courses
            eligible = get_eligible_courses(completed, major_cands, prereqs)
            
            eligible_course_dicts = [
                {'courseCode': e['courseCode'], 'units': e['units']}
                for e in eligible
            ]

            all_cc_course_codes = set(prereqs.keys())
            total_eligible = eligible_course_dicts + ge_course_dicts
            
            # Select courses for this term
            selected, units, pruned_codes = select_courses_for_term(
                total_eligible, completed, uc_to_cc_map, all_cc_course_codes, MAX_UNITS
            )
            
            if pruned_codes:
                major_cands = [
                    m for m in major_cands
                    if m['courseCode'] not in pruned_codes
                ]
            
            if not selected:
                break
            
            # Update GE tracker state
            for course in selected:
                code = course["courseCode"]
                if "reqIds" in course:
                    for req in course["reqIds"]:
                        ge_tracker.add_completed_course(code, req)
                else:
                    ge_tracker.add_completed_course(code, course.get("tag", code))
            
            # Record term data
            terms_data.append({
                'term': term_num,
                'units': units,
                'courses': len(selected),
                'course_codes': [c['courseCode'] for c in selected]
            })
            
            total_units += units
            term_num += 1
        
        return {
            'success': True,
            'total_terms': len(terms_data),
            'total_units': total_units,
            'terms': terms_data,
            'over_2_years': len(terms_data) > TERMS_FOR_TWO_YEARS,  # True if takes more than 2 years
            'meets_unit_requirement': total_units >= TOTAL_UNITS_REQUIRED,
            'system_settings': system_settings  # Include the settings used
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

def save_results_for_cc(cc_name, cc_results, ge_pattern, timestamp, system_type):
    """Save individual CC results to its own folder and files."""
    # Create CC-specific folder
    cc_folder = RESULTS_DIR / cc_name
    cc_folder.mkdir(exist_ok=True)
    
    # Include system type in filename
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
    
    # Save CC-specific CSV
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
            
            # Add per-term units (up to 6 terms)
            for i in range(1, 7):
                term_key = f'units_term_{i}'
                if i <= len(result['terms_detail']):
                    row[term_key] = result['terms_detail'][i-1]['units']
                else:
                    row[term_key] = 0
            
            writer.writerow(row)

def run_automation(ge_pattern_filter=None):
    """Main automation function with optional GE pattern filtering."""
    if ge_pattern_filter:
        print(f"🚀 Starting Pathway Generator Automation - {ge_pattern_filter} ONLY")
        patterns_to_test = [ge_pattern_filter]
    else:
        print("🚀 Starting Pathway Generator Automation - ALL GE PATTERNS")
        patterns_to_test = GE_PATTERNS
    
    print("=" * 60)
    
    # Check if system classifications are set up
    if not QUARTER_SYSTEM_CCS and not SEMESTER_SYSTEM_CCS:
        print("⚠️ WARNING: No CCs classified as quarter or semester systems!")
        print("   Please add CC names to QUARTER_SYSTEM_CCS and SEMESTER_SYSTEM_CCS lists")
        print("   All CCs will default to semester system settings.")
    
    # Discover CC files that have BOTH articulation AND prerequisite files
    cc_files, prereq_mapping = discover_cc_files()
    
    if not cc_files:
        print("❌ No CC files found with both articulation and prerequisite files. Exiting.")
        return
    
    print(f"📁 Found {len(cc_files)} CCs with both articulation and prerequisite files")
    
    # Show system classification for discovered CCs
    quarter_ccs = [cc for cc in cc_files.keys() if cc in QUARTER_SYSTEM_CCS]
    semester_ccs = [cc for cc in cc_files.keys() if cc in SEMESTER_SYSTEM_CCS]
    unclassified_ccs = [cc for cc in cc_files.keys() if cc not in QUARTER_SYSTEM_CCS and cc not in SEMESTER_SYSTEM_CCS]
    
    print(f"\n📊 System Classifications:")
    print(f"  Quarter System ({len(quarter_ccs)}): {quarter_ccs}")
    print(f"  Semester System ({len(semester_ccs)}): {semester_ccs}")
    if unclassified_ccs:
        print(f"  Unclassified ({len(unclassified_ccs)}): {unclassified_ccs}")
        print(f"    ⚠️ These will use semester settings by default")
    
    # Generate ALL UC combinations (1 to 9 UCs)
    print("\n🎯 Generating UC combinations...")
    uc_combinations = generate_uc_combinations()  # This generates ALL combinations 1-9
    
    print(f"🎯 Generated {len(uc_combinations)} UC combinations")
    print("📊 Breakdown by UC count:")
    for r in range(1, len(SUPPORTED_UCS) + 1):
        count = len(list(combinations(SUPPORTED_UCS, r)))
        print(f"  {r} UC{'s' if r > 1 else ''}: {count} combinations")
    
    # Prepare results storage
    results = []
    cc_results = {}  # Store results by CC for individual file generation
    summary_stats = {
        'total_runs': 0,
        'successful_runs': 0,
        'failed_runs': 0,
        'by_cc': {},
        'by_ge_pattern': {},
        'by_uc_count': {},
        'by_system_type': {'quarter': {'runs': 0, 'success': 0}, 'semester': {'runs': 0, 'success': 0}}
    }
    
    # Check required files
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
    
    # Main automation loop - only process CCs that have prerequisite files
    for cc_name in cc_files.keys():  # Only iterate over CCs with both files
        # Get system settings for this CC
        system_settings, system_type = get_system_settings(cc_name)
        
        print(f"🏫 Processing CC: {cc_name} ({system_type.upper()} system)")
        print(f"   Settings: {system_settings['MAX_UNITS']} max units, {system_settings['TOTAL_UNITS_REQUIRED']} total required, {system_settings['TERMS_FOR_TWO_YEARS']} terms = 2 years")
        
        art_path = ARTICULATION_DIR / cc_files[cc_name]
        prereq_path = PREREQS_DIR / prereq_mapping[cc_name]
        
        summary_stats['by_cc'][cc_name] = {'success': 0, 'failed': 0, 'system_type': system_type}
        cc_results[cc_name] = []  # Initialize results list for this CC
        
        for uc_combo in uc_combinations:
            for ge_pattern in patterns_to_test:
                current_run += 1
                uc_combo_str = "+".join(sorted(uc_combo))
                uc_count = len(uc_combo)  # Calculate UC count
                
                print(f"  [{current_run}/{total_combinations}] {cc_name} ({system_type}) -> {uc_combo_str} ({ge_pattern}) - {uc_count} UCs")
                
                summary_stats['total_runs'] += 1
                summary_stats['by_system_type'][system_type]['runs'] += 1
                
                # Run pathway generation with system-specific settings
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
                    
                    # Store successful result
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
                    cc_results[cc_name].append(result_entry)  # Add to CC-specific results
                    
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
                    cc_results[cc_name].append(result_entry)  # Add to CC-specific results
                    
                    print(f"    ❌ Failed: {error_msg}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ge_suffix = f"_{ge_pattern_filter}" if ge_pattern_filter else "_ALL"
    
    print(f"\n💾 Saving individual CC files...")
    # Save individual CC results
    for cc_name, cc_result_list in cc_results.items():
        if cc_result_list:  # Only save if there are results
            try:
                _, system_type = get_system_settings(cc_name)
                save_results_for_cc(cc_name, cc_result_list, ge_pattern_filter or "ALL", timestamp, system_type)
                print(f"  📁 {cc_name} ({system_type}): {len(cc_result_list)} combinations saved")
            except Exception as e:
                print(f"  ❌ {cc_name}: Error during save - {e}")
        else:
            print(f"  ⏭️ {cc_name}: No results to save")
    
    print(f"💾 Saving master files...")
    # Save master/combined results as JSON
    results_json_path = RESULTS_DIR / f"pathway_results{ge_suffix}_{timestamp}.json"
    with open(results_json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': summary_stats,
            'results': results,
            'metadata': {
                'timestamp': timestamp,
                'total_combinations': total_combinations,
                'cc_files_processed': list(cc_files.keys()),
                'ge_patterns_tested': patterns_to_test,
                'uc_combinations_count': len(uc_combinations),
                'system_settings': {
                    'quarter': QUARTER_SETTINGS,
                    'semester': SEMESTER_SETTINGS
                },
                'cc_classifications': {
                    'quarter_ccs': quarter_ccs,
                    'semester_ccs': semester_ccs,
                    'unclassified_ccs': unclassified_ccs
                }
            }
        }, f, indent=2)
    
    # Save master/combined summary as CSV
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
            
            # Add per-term units (up to 6 terms)
            for i in range(1, 7):
                term_key = f'units_term_{i}'
                if i <= len(result['terms_detail']):
                    row[term_key] = result['terms_detail'][i-1]['units']
                else:
                    row[term_key] = 0
            
            writer.writerow(row)
    
    # Print final summary
    print("\n" + "=" * 60)
    print("🎉 AUTOMATION COMPLETE!")
    print("=" * 60)
    print(f"📊 Total runs: {summary_stats['total_runs']}")
    print(f"✅ Successful: {summary_stats['successful_runs']}")
    print(f"❌ Failed: {summary_stats['failed_runs']}")
    print(f"📈 Success rate: {summary_stats['successful_runs']/summary_stats['total_runs']*100:.1f}%")
    
    # System-specific statistics
    print(f"\n📊 Success Rates by System:")
    for system_type, stats in summary_stats['by_system_type'].items():
        if stats['runs'] > 0:
            rate = stats['success'] / stats['runs'] * 100
            print(f"  {system_type.title()} System: {rate:.1f}% ({stats['success']}/{stats['runs']})")
    
    print(f"\n📁 Master Results saved to:")
    print(f"  JSON: {results_json_path}")
    print(f"  CSV:  {csv_path}")
    
    print(f"\n📂 Individual CC folders created in: {RESULTS_DIR}")
    print(f"   Each CC has its own folder with separate JSON/CSV files")
    print(f"   Filenames now include system type (quarter/semester)")
    
    print(f"\n🏫 CC Success Rates:")
    for cc, stats in summary_stats['by_cc'].items():
        total = stats['success'] + stats['failed']
        system_type = stats['system_type']
        if total > 0:
            rate = stats['success'] / total * 100
            print(f"  {cc} ({system_type}): {rate:.1f}% ({stats['success']}/{total})")
    
    print(f"\n🎯 Success Rates by UC Count:")
    for uc_count in sorted(summary_stats['by_uc_count'].keys()):
        print(f"  {uc_count} UC{'s' if uc_count > 1 else ''}: {summary_stats['by_uc_count'][uc_count]} successful runs")
    
    print(f"\n📋 System Settings Used:")
    print(f"  Quarter System:")
    print(f"    Max units per term: {QUARTER_SETTINGS['MAX_UNITS']}")
    print(f"    Total units required: {QUARTER_SETTINGS['TOTAL_UNITS_REQUIRED']}")
    print(f"    Terms for 2 years: {QUARTER_SETTINGS['TERMS_FOR_TWO_YEARS']}")
    print(f"  Semester System:")
    print(f"    Max units per term: {SEMESTER_SETTINGS['MAX_UNITS']}")
    print(f"    Total units required: {SEMESTER_SETTINGS['TOTAL_UNITS_REQUIRED']}")
    print(f"    Terms for 2 years: {SEMESTER_SETTINGS['TERMS_FOR_TWO_YEARS']}")
    
    return results  # Return results so the function doesn't end early

def print_cc_classification_helper():
    """Helper function to print discovered CCs for manual classification."""
    print("\n" + "=" * 60)
    print("🏫 CC CLASSIFICATION HELPER")
    print("=" * 60)
    
    cc_files, _ = discover_cc_files()
    
    if not cc_files:
        print("❌ No CC files found. Run discovery first.")
        return
    
    print(f"📋 Found {len(cc_files)} CCs that need classification:")
    print("\nCopy and paste the appropriate CC names into the lists at the top of the script:")
    print("\nQUARTER_SYSTEM_CCS = [")
    for cc in sorted(cc_files.keys()):
        print(f'    # "{cc}",  # <-- Add this if it\'s a quarter system')
    print("]\n")
    
    print("SEMESTER_SYSTEM_CCS = [")
    for cc in sorted(cc_files.keys()):
        print(f'    # "{cc}",  # <-- Add this if it\'s a semester system')
    print("]")
    
    print(f"\n💡 Tip: Most California CCs use semester system.")
    print(f"   Quarter system CCs include: De Anza, Foothill, some CSU-adjacent colleges")

if __name__ == "__main__":
    # Allow running separate GE patterns or all patterns in GE_PATTERNS
    if len(sys.argv) > 1:
        arg = sys.argv[1].upper()
        
        # Special command to help with CC classification
        if arg == "HELP" or arg == "CLASSIFY":
            print_cc_classification_helper()
            sys.exit(0)
        
        # Check if the requested pattern is in our supported patterns
        all_supported = ["IGETC", "7COURSEPATTERN"]
        if arg in all_supported:
            run_automation(arg)
        else:
            print(f"❌ Invalid GE pattern. Available patterns: {', '.join(all_supported)}")
            print("Usage:")
            print("  python automated_pathway_generator.py IGETC")
            print("  python automated_pathway_generator.py 7CoursePattern") 
            print("  python automated_pathway_generator.py help     # Show CC classification helper")
            print("  python automated_pathway_generator.py          # (runs all patterns in GE_PATTERNS)")
    else:
        # Run all patterns defined in GE_PATTERNS
        if len(GE_PATTERNS) == 1:
            print(f"🔄 Running {GE_PATTERNS[0]}...")
            run_automation(GE_PATTERNS[0])
        else:
            for i, pattern in enumerate(GE_PATTERNS):
                if i > 0:
                    print("\n" + "="*80 + "\n")
                print(f"🔄 Running {pattern} ({i+1}/{len(GE_PATTERNS)})...")
                run_automation(pattern)