#!/usr/bin/env python3
"""
Debug script to test GE tracker behavior
"""

import sys
from pathlib import Path

# Add the pathway_generator directory to the path
sys.path.append(str(Path(__file__).parent))

def debug_ge_tracker():
    """Debug the GE tracker behavior."""
    
    try:
        from ge_checker import GE_Tracker
        from pathway_generator import build_file_paths, load_json
        
        # Test with De Anza College and UCSD
        cc_id = "de_anza"
        uc_id = "ucsd"
        ge_id = "IGETC"
        
        # Build file paths
        paths = build_file_paths(cc_id, uc_id)
        
        # Load GE data
        ge_data = load_json(paths["ge_reqs_json"])
        
        # Test GE_Tracker initialization
        ge_tracker = GE_Tracker(ge_data)
        ge_tracker.load_pattern(ge_id)
        print("✅ GE_Tracker initialized and pattern loaded")
        
        # Test getting remaining requirements BEFORE adding course
        ge_remaining_before = ge_tracker.get_remaining_requirements(ge_id)
        print(f"✅ GE remaining requirements BEFORE: {list(ge_remaining_before.keys())}")
        
        # Check IG_2 specifically
        if "IG_2" in ge_remaining_before:
            print(f"IG_2 before: {ge_remaining_before['IG_2']}")
        
        # Test adding completed courses to GE tracker
        ge_tracker.add_completed_course("MATH 1A", ["IG_2"])
        print("✅ Successfully added completed course to GE tracker")
        
        # Test updated remaining requirements AFTER adding course
        ge_remaining_after = ge_tracker.get_remaining_requirements(ge_id)
        print(f"✅ GE remaining requirements AFTER: {list(ge_remaining_after.keys())}")
        
        # Check IG_2 specifically
        if "IG_2" in ge_remaining_after:
            print(f"IG_2 after: {ge_remaining_after['IG_2']}")
        else:
            print("✅ IG_2 was completed and removed from remaining requirements!")
        
        # Let's also check what courses are in the tracker
        print(f"Completed courses in tracker: {ge_tracker.completed_courses}")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_ge_tracker()
    if success:
        print("\n✅ Debug completed!")
    else:
        print("\n❌ Debug failed!")
        sys.exit(1) 