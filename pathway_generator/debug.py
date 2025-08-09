#!/usr/bin/env python3
"""
Focused debugging script for problematic CCs.
This script will deep-dive into the major requirements loading process.
"""

import json
import sys
from pathlib import Path

# Add the project paths
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
ARTICULATION_DIR = PROJECT_ROOT / "articulated_courses_json"
PREREQS_DIR = PROJECT_ROOT / "prerequisites"
COURSE_REQS_FILE = PROJECT_ROOT / "scraping" / "files" / "course_reqs.json"

# Import modules
sys.path.append(str(PROJECT_ROOT))
from major_checker import MajorRequirements, get_major_requirements
from prereq_resolver import load_prereq_data

def load_json(path):
    """Load JSON file with error handling."""
    try:
        with open(path, "r", encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {path}: {e}")
        return None

def debug_cc(cc_name, debug_all=False):
    """Deep debug analysis for a specific CC."""
    print(f"\n{'='*60}")
    print(f"🔍 DEEP DEBUG ANALYSIS: {cc_name}")
    print(f"{'='*60}")
    
    # 1. Check file existence
    print(f"\n1️⃣ FILE EXISTENCE CHECK:")
    
    # Find articulation file
    art_files = list(ARTICULATION_DIR.glob(f"*{cc_name}*articulation.json"))
    if not art_files:
        # Try variations
        variations = [
            f"{cc_name}_college_articulation.json",
            f"{cc_name.replace('_', ' ')}_articulation.json",
            f"{cc_name.title()}_articulation.json"
        ]
        for var in variations:
            art_files.extend(ARTICULATION_DIR.glob(var))
    
    if not art_files:
        print(f"❌ No articulation file found for {cc_name}")
        print(f"   Available articulation files:")
        for f in sorted(ARTICULATION_DIR.glob("*articulation.json"))[:10]:
            print(f"     {f.name}")
        return False
    
    art_file = art_files[0]
    print(f"✅ Articulation file: {art_file.name}")
    
    # Find prerequisite file
    prereq_files = list(PREREQS_DIR.glob(f"*{cc_name}*prereqs.json"))
    if not prereq_files:
        variations = [
            f"{cc_name}_college_prereqs.json",
            f"{cc_name.replace('_', ' ')}_prereqs.json"
        ]
        for var in variations:
            prereq_files.extend(PREREQS_DIR.glob(var))
    
    if not prereq_files:
        print(f"❌ No prerequisite file found for {cc_name}")
        return False
    
    prereq_file = prereq_files[0]
    print(f"✅ Prerequisite file: {prereq_file.name}")
    
    # 2. Load and analyze articulation data
    print(f"\n2️⃣ ARTICULATION DATA ANALYSIS:")
    articulated = load_json(art_file)
    if not articulated:
        return False
    
    print(f"✅ Loaded articulation data")
    print(f"   Total UCs: {len(articulated)}")
    print(f"   Sample UCs: {list(articulated.keys())[:5]}")
    
    # Check each UC's data
    for uc in list(articulated.keys())[:3]:
        uc_data = articulated[uc]
        print(f"   📊 {uc}: {len(uc_data)} courses")
        if debug_all and uc_data:
            sample_course = list(uc_data.keys())[0]
            print(f"      Sample: {sample_course} -> {uc_data[sample_course]}")
    
    # 3. Load and analyze prerequisites
    print(f"\n3️⃣ PREREQUISITE DATA ANALYSIS:")
    prereqs = load_prereq_data(prereq_file)
    print(f"✅ Loaded prerequisites for {len(prereqs)} courses")
    
    if debug_all:
        print(f"   Sample prereq courses: {list(prereqs.keys())[:10]}")
    
    # 4. Test major requirements loading
    print(f"\n4️⃣ MAJOR REQUIREMENTS LOADING:")
    
    # Test with common UC combinations
    test_ucs = [
        ["UCLA"],
        ["UCSD"],
        ["UCLA", "UCSD"],
        ["UCI", "UCR", "UCSB"]
    ]
    
    for uc_list in test_ucs:
        print(f"\n   🎯 Testing with UCs: {uc_list}")
        
        try:
            # Test the major requirements loading
            major_reqs = get_major_requirements(
                str(COURSE_REQS_FILE),
                cc_name,
                uc_list,
                str(ARTICULATION_DIR)
            )
            
            print(f"   ✅ Major requirements object created")
            
            # Check if it has the expected attributes
            if hasattr(major_reqs, 'cc_to_uc_map'):
                print(f"   ✅ Has cc_to_uc_map attribute")
                
                # Check the mapping
                map_data = major_reqs.cc_to_uc_map
                if isinstance(map_data, dict):
                    print(f"   ✅ cc_to_uc_map is dict with {len(map_data)} entries")
                    if debug_all:
                        print(f"      Keys: {list(map_data.keys())[:5]}")
                else:
                    print(f"   ⚠️ cc_to_uc_map is not a dict: {type(map_data)}")
            else:
                print(f"   ❌ No cc_to_uc_map attribute found")
            
            # Test getting remaining courses
            completed = set()  # Empty set for fresh start
            remaining_courses = major_reqs.get_remaining_courses(completed, articulated)
            
            print(f"   📊 Remaining courses: {len(remaining_courses)}")
            
            if len(remaining_courses) == 0:
                print(f"   🚨 NO REMAINING COURSES! This is the problem.")
                
                # Debug why no courses are remaining
                print(f"   🔍 Debugging get_remaining_courses...")
                
                # Check if the method exists and what it returns
                if hasattr(major_reqs, 'get_remaining_courses'):
                    print(f"      ✅ Method exists")
                    
                    # Let's inspect the major_reqs object more deeply
                    print(f"      🔍 Major requirements object attributes:")
                    for attr in dir(major_reqs):
                        if not attr.startswith('_'):
                            print(f"         {attr}: {type(getattr(major_reqs, attr, None))}")
                
                # Try to get the CC-to-UC mapping directly
                try:
                    major_map = MajorRequirements.get_cc_to_uc_map(cc_name, uc_list, art_file)
                    print(f"   🔍 Direct CC-to-UC mapping:")
                    for uc, courses in major_map.items():
                        print(f"      {uc}: {len(courses)} course mappings")
                        if debug_all and courses:
                            sample_courses = list(courses.keys())[:3]
                            print(f"         Sample courses: {sample_courses}")
                except Exception as e:
                    print(f"   ❌ Error getting CC-to-UC mapping: {e}")
                    
            else:
                print(f"   ✅ Found remaining courses")
                if debug_all:
                    sample_remaining = remaining_courses[:3]
                    for course in sample_remaining:
                        print(f"      {course.get('courseCode', 'NO_CODE')}: {course.get('units', 'NO_UNITS')} units")
            
        except Exception as e:
            print(f"   ❌ Error loading major requirements: {e}")
            import traceback
            print(f"   📍 Traceback: {traceback.format_exc()}")
    
    # 5. Check course requirements file
    print(f"\n5️⃣ COURSE REQUIREMENTS FILE CHECK:")
    if not COURSE_REQS_FILE.exists():
        print(f"❌ Course requirements file not found: {COURSE_REQS_FILE}")
        return False
    
    course_reqs = load_json(COURSE_REQS_FILE)
    if not course_reqs:
        print(f"❌ Failed to load course requirements")
        return False
    
    print(f"✅ Course requirements loaded")
    print(f"   Structure: {type(course_reqs)}")
    
    if isinstance(course_reqs, dict):
        print(f"   Keys: {list(course_reqs.keys())[:10]}")
        
        # Look for our CC in the course requirements
        cc_variations = [cc_name, cc_name.replace('_', ' '), cc_name.replace('_', '').lower()]
        found_cc = False
        
        for variation in cc_variations:
            if variation in course_reqs:
                print(f"   ✅ Found CC in course requirements: {variation}")
                cc_data = course_reqs[variation]
                print(f"      Data type: {type(cc_data)}")
                if isinstance(cc_data, dict):
                    print(f"      Keys: {list(cc_data.keys())[:5]}")
                found_cc = True
                break
        
        if not found_cc:
            print(f"   ⚠️ CC not found in course requirements")
            print(f"   🔍 Similar CC names in file:")
            for key in course_reqs.keys():
                if isinstance(key, str) and any(part in key.lower() for part in cc_name.split('_')[:2]):
                    print(f"      {key}")
    
    return True

def main():
    """Main debugging function."""
    print("🔍 CC-Specific Debug Tool")
    print("=" * 40)
    
    # Debug problematic CCs
    problematic_ccs = [
        "cosumnes_river",
        "los_angeles_city_college",
        "foothill_college",
        "chabot_college"
    ]
    
    debug_all = len(sys.argv) > 1 and sys.argv[1].lower() == "verbose"
    
    for cc_name in problematic_ccs:
        success = debug_cc(cc_name, debug_all)
        if not success:
            print(f"\n❌ Failed to debug {cc_name}")
        
        print(f"\n{'='*80}\n")
    
    print("\n💡 SUMMARY AND RECOMMENDATIONS:")
    print("1. Check if the CC names match exactly between files")
    print("2. Verify the articulation file format is correct")
    print("3. Ensure the CC exists in course_reqs.json")
    print("4. Check if major_checker.py can handle the CC name format")
    print("5. Verify prerequisite courses exist in articulation data")

if __name__ == "__main__":
    main()