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

# ─── Constants - MODIFY THESE TO CHANGE LIMITS ───────────────────────────────
MAX_UNITS = 18             # ← CHANGE THIS: Units per term limit (18 for semesters, 20 for quarters)
TOTAL_UNITS_REQUIRED = 60  # ← CHANGE THIS: Total units needed for transfer completion
TERMS_FOR_TWO_YEARS = 4    # ← CHANGE THIS: How many terms = 2 years (4 for semesters, 6 for quarters)

# ─── 1) Locate directories ────────────────────────────────────────────────────
SCRIPT_DIR       = Path(__file__).parent.resolve()
PROJECT_ROOT     = SCRIPT_DIR.parent
ARTICULATION_DIR = PROJECT_ROOT / "articulated_courses_json"
PREREQS_DIR      = PROJECT_ROOT / "prerequisites"
COURSE_REQS_FILE = PROJECT_ROOT / "scraping" / "files" / "course_reqs.json"
RESULTS_DIR      = SCRIPT_DIR / "automation_results"

# Create results directory
RESULTS_DIR.mkdir(exist_ok=True)

# ─── 2) CC and UC options ─────────────────────────────────────────────────────
SUPPORTED_UCS = ["UCSD", "UCLA", "UCI", "UCR", "UCSB", "UCD", "UCB", "UCSC", "UCM"]
GE_PATTERNS = ["7CoursePattern", "IGETC"]

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
    
    # First, discover all prerequisite files
    prereq_files = {}
    print(f"📁 Scanning prerequisite files in: {PREREQS_DIR}")
    for prereq_file in PREREQS_DIR.glob("*_prereqs.json"):
        # Extract CC name from prerequisite filename
        cc_name = prereq_file.stem.replace("_prereqs", "").replace("_college", "").lower()
        prereq_files[cc_name] = prereq_file.name
        print(f"Found prereq file: {cc_name} -> {prereq_file.name}")
    
    print(f"📁 Scanning articulation files in: {ARTICULATION_DIR}")
    # Then, find matching articulation files
    matched_count = 0
    for cc_name, prereq_filename in prereq_files.items():
        # Try different naming patterns for articulation files
        possible_art_names = [
            f"{cc_name}_articulation.json",
            f"{cc_name}_college_articulation.json"
        ]
        
        # Also try capitalized versions and other variations
        cc_parts = cc_name.split('_')
        
        # Try title case variations
        title_case_name = '_'.join([part.title() for part in cc_parts])
        possible_art_names.extend([
            f"{title_case_name}_articulation.json",
            f"{title_case_name}_College_articulation.json"
        ])
        
        # Try with "College" inserted
        if "college" not in cc_name:
            possible_art_names.extend([
                f"{cc_name}_college_articulation.json",
                f"{title_case_name}_College_articulation.json"
            ])
        
        # Special handling for common variations
        if cc_name == "santa_monica":
            possible_art_names.extend([
                "Santa_Monica_College_articulation.json",
                "santa_monica_college_articulation.json",
                "Santa_Monica_articulation.json"
            ])
        
        found_match = False
        for art_name in possible_art_names:
            art_path = ARTICULATION_DIR / art_name
            if art_path.exists():
                cc_files[cc_name] = art_name
                prereq_mapping[cc_name] = prereq_filename
                print(f"✅ Matched CC: {cc_name} -> {art_name} + {prereq_filename}")
                matched_count += 1
                found_match = True
                break
        
        if not found_match:
            print(f"⚠️ No matching articulation file found for {cc_name} (has prereq: {prereq_filename})")
            print(f"   Tried: {possible_art_names[:3]}...")
    
    print(f"🎯 Successfully matched {matched_count} CCs with both files")
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

def generate_pathway_automated(art_path, prereq_path, ge_path, major_path, cc_id, uc_list, ge_pattern):
    """Modified pathway generation that returns summary statistics."""
    try:
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
            'meets_unit_requirement': total_units >= TOTAL_UNITS_REQUIRED
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

def save_results_for_cc(cc_name, cc_results, ge_pattern, timestamp):
    """Save individual CC results to its own folder and files."""
    # Create CC-specific folder
    cc_folder = RESULTS_DIR / cc_name
    cc_folder.mkdir(exist_ok=True)
    
    # Save CC-specific JSON
    cc_json_path = cc_folder / f"{cc_name}_{ge_pattern}_{timestamp}.json"
    with open(cc_json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'cc_name': cc_name,
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
    cc_csv_path = cc_folder / f"{cc_name}_{ge_pattern}_{timestamp}.csv"
    with open(cc_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'cc', 'ucs', 'ge_pattern', 'status', 'total_terms', 'total_units', 
            'over_2_years', 'units_term_1', 'units_term_2', 'units_term_3', 
            'units_term_4', 'units_term_5', 'units_term_6', 'error'
        ])
        writer.writeheader()
        
        for result in cc_results:
            row = {
                'cc': result['cc'],
                'ucs': result['ucs'],
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
    
    # Discover CC files that have BOTH articulation AND prerequisite files
    cc_files, prereq_mapping = discover_cc_files()
    
    if not cc_files:
        print("❌ No CC files found with both articulation and prerequisite files. Exiting.")
        return
    
    print(f"📁 Found {len(cc_files)} CCs with both articulation and prerequisite files")
    
    # Generate ALL UC combinations (1 to 9 UCs)
    print("🎯 Generating UC combinations...")
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
        'by_uc_count': {}
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
        print(f"🏫 Processing CC: {cc_name}")
        
        art_path = ARTICULATION_DIR / cc_files[cc_name]
        prereq_path = PREREQS_DIR / prereq_mapping[cc_name]
        
        summary_stats['by_cc'][cc_name] = {'success': 0, 'failed': 0}
        cc_results[cc_name] = []  # Initialize results list for this CC
        
        for uc_combo in uc_combinations:
            for ge_pattern in patterns_to_test:
                current_run += 1
                uc_combo_str = "+".join(sorted(uc_combo))
                
                print(f"  [{current_run}/{total_combinations}] {cc_name} -> {uc_combo_str} ({ge_pattern})")
                
                summary_stats['total_runs'] += 1
                
                # Run pathway generation
                result = generate_pathway_automated(
                    art_path, prereq_path, ge_path, COURSE_REQS_FILE,
                    cc_name, uc_combo, ge_pattern
                )
                
                if result and result.get('success'):
                    summary_stats['successful_runs'] += 1
                    summary_stats['by_cc'][cc_name]['success'] += 1
                    summary_stats['by_ge_pattern'][ge_pattern] = summary_stats['by_ge_pattern'].get(ge_pattern, 0) + 1
                    uc_count = len(uc_combo)
                    summary_stats['by_uc_count'][uc_count] = summary_stats['by_uc_count'].get(uc_count, 0) + 1
                    
                    # Store successful result
                    result_entry = {
                        'cc': cc_name,
                        'ucs': uc_combo_str,
                        'ge_pattern': ge_pattern,
                        'total_terms': result['total_terms'],
                        'total_units': result['total_units'],
                        'over_2_years': result['over_2_years'],
                        'terms_detail': result['terms'],
                        'status': 'success'
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
                        'ucs': uc_combo_str,
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
                cc_json_path, cc_csv_path = save_results_for_cc(cc_name, cc_result_list, ge_pattern_filter or "ALL", timestamp)
                if cc_json_path and cc_csv_path:  # Check if files were created successfully
                    print(f"  📁 {cc_name}: {len(cc_result_list)} combinations saved")
                else:
                    print(f"  ❌ {cc_name}: Failed to save files")
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
                'max_units_per_term': MAX_UNITS,
                'total_units_required': TOTAL_UNITS_REQUIRED,
                'terms_for_two_years': TERMS_FOR_TWO_YEARS,
                'over_2_years_explanation': f"True if total_terms > {TERMS_FOR_TWO_YEARS} (takes more than 2 years to complete)"
            }
        }, f, indent=2)
    
    # Save master/combined summary as CSV
    csv_path = RESULTS_DIR / f"pathway_summary{ge_suffix}_{timestamp}.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'cc', 'ucs', 'ge_pattern', 'status', 'total_terms', 'total_units', 
            'over_2_years', 'units_term_1', 'units_term_2', 'units_term_3', 
            'units_term_4', 'units_term_5', 'units_term_6', 'error'
        ])
        writer.writeheader()
        
        for result in results:
            row = {
                'cc': result['cc'],
                'ucs': result['ucs'],
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
    
    print(f"\n📁 Master Results saved to:")
    print(f"  JSON: {results_json_path}")
    print(f"  CSV:  {csv_path}")
    
    print(f"\n📂 Individual CC folders created in: {RESULTS_DIR}")
    print(f"   Each CC has its own folder with separate JSON/CSV files")
    
    print(f"\n🏫 CC Success Rates:")
    for cc, stats in summary_stats['by_cc'].items():
        total = stats['success'] + stats['failed']
        if total > 0:
            rate = stats['success'] / total * 100
            print(f"  {cc}: {rate:.1f}% ({stats['success']}/{total})")
    
    print(f"\n📋 Settings Used:")
    print(f"  Max units per term: {MAX_UNITS}")
    print(f"  Total units required: {TOTAL_UNITS_REQUIRED}")
    print(f"  Terms for 2 years: {TERMS_FOR_TWO_YEARS}")
    print(f"  'over_2_years' = True when total_terms > {TERMS_FOR_TWO_YEARS}")
    
    return results  # Return results so the function doesn't end early

if __name__ == "__main__":
    # Allow running separate GE patterns or both
    if len(sys.argv) > 1:
        ge_pattern = sys.argv[1].upper()
        if ge_pattern in ["IGETC", "7COURSEPATTERN"]:
            run_automation(ge_pattern)
        else:
            print("❌ Invalid GE pattern. Use 'IGETC' or '7CoursePattern'")
            print("Usage:")
            print("  python automated_pathway_generator.py IGETC")
            print("  python automated_pathway_generator.py 7CoursePattern") 
            print("  python automated_pathway_generator.py  # (runs both)")
    else:
        # Run both patterns
        print("🔄 Running IGETC first...")
        run_automation("IGETC")
        print("\n" + "="*80 + "\n")
        print("🔄 Now running 7CoursePattern...")
        run_automation("7CoursePattern")