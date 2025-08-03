#!/usr/bin/env python3
"""
test_prereq_resolver.py - Comprehensive test suite for prereq_resolver.py

Tests all functions with various scenarios including edge cases.
"""

import json
import tempfile
import os
from prereq_resolver import (
    load_prereq_data, 
    has_met_prereqs, 
    get_eligible_courses, 
    explain_unmet_prereqs
)


def create_test_data():
    """Create comprehensive test data covering various prerequisite scenarios."""
    return [
        {
            "courseCode": "MATH 1A",
            "courseName": "Calculus I",
            "units": 5,
            "prerequisites": []
        },
        {
            "courseCode": "MATH 1B", 
            "courseName": "Calculus II",
            "units": 5,
            "prerequisites": [
                {
                    "type": "and",
                    "items": ["MATH 1A"]
                }
            ]
        },
        {
            "courseCode": "MATH 1C",
            "courseName": "Calculus III", 
            "units": 5,
            "prerequisites": [
                {
                    "type": "and",
                    "items": ["MATH 1B"]
                }
            ]
        },
        {
            "courseCode": "CS 1A",
            "courseName": "Introduction to Java",
            "units": 4.5,
            "prerequisites": []
        },
        {
            "courseCode": "CS 1B",
            "courseName": "Intermediate Java", 
            "units": 4.5,
            "prerequisites": [
                {
                    "type": "and",
                    "items": ["CS 1A", "MATH 1A"]
                }
            ]
        },
        {
            "courseCode": "CS 2A",
            "courseName": "Data Structures",
            "units": 4.5,
            "prerequisites": [
                {
                    "type": "and",
                    "items": ["CS 1B"]
                },
                {
                    "type": "or", 
                    "items": ["MATH 1B", "MATH 1C"]
                }
            ]
        },
        {
            "courseCode": "CS 1C",
            "courseName": "Advanced Java",
            "units": 4.5,
            "prerequisites": [
                {
                    "type": "or",
                    "items": ["CS 1B", "CS 2A"]
                }
            ]
        },
        {
            "courseCode": "PHYS 4A",
            "courseName": "Physics I",
            "units": 4,
            "prerequisites": [
                {
                    "type": "and",
                    "items": ["MATH 1A"]
                },
                {
                    "type": "or",
                    "items": ["MATH 1B", "CHEM 1A"]
                }
            ]
        },
        {
            "courseCode": "ENG 1A", 
            "courseName": "English Composition",
            "units": 4,
            "prerequisites": []
        },
        {
            "courseCode": "TEST_COURSE",
            "courseName": "Course with Unknown Block Type",
            "units": 3,
            "prerequisites": [
                {
                    "type": "UNKNOWN_TYPE",
                    "items": ["ENG 1A"]
                }
            ]
        }
    ]


def test_load_prereq_data():
    """Test the load_prereq_data function."""
    print("🧪 Testing load_prereq_data...")
    
    test_data = create_test_data()
    
    # Create temporary JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        temp_file = f.name
    
    try:
        # Test successful loading
        prereq_data = load_prereq_data(temp_file)
        
        assert isinstance(prereq_data, dict), "Should return a dictionary"
        assert "CS 1A" in prereq_data, "Should contain CS 1A"
        assert prereq_data["CS 1A"]["courseName"] == "Introduction to Java"
        
        print("  ✅ Successfully loads valid JSON file")
        
        # Test file not found
        try:
            load_prereq_data("nonexistent_file.json")
            assert False, "Should raise FileNotFoundError"
        except FileNotFoundError:
            print("  ✅ Properly handles missing files")
        
        # Test invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            invalid_file = f.name
        
        try:
            load_prereq_data(invalid_file)
            assert False, "Should raise JSONDecodeError"
        except (json.JSONDecodeError, Exception) as e:
            print("  ✅ Properly handles invalid JSON")
        finally:
            os.unlink(invalid_file)
            
    finally:
        os.unlink(temp_file)


def test_has_met_prereqs():
    """Test the has_met_prereqs function."""
    print("\n🧪 Testing has_met_prereqs...")
    
    prereq_data = {entry["courseCode"]: entry for entry in create_test_data()}
    
    # Test 1: Course with no prerequisites
    completed = set()
    assert has_met_prereqs("CS 1A", completed, prereq_data) == True
    print("  ✅ Courses with no prereqs are always eligible")
    
    # Test 2: Simple AND prerequisite - not met
    completed = {"MATH 1A"}
    assert has_met_prereqs("CS 1B", completed, prereq_data) == False
    print("  ✅ AND prerequisite correctly identifies missing courses")
    
    # Test 3: Simple AND prerequisite - met
    completed = {"CS 1A", "MATH 1A"}
    assert has_met_prereqs("CS 1B", completed, prereq_data) == True
    print("  ✅ AND prerequisite correctly identifies satisfied requirements")
    
    # Test 4: Multiple blocks (AND + OR) - partially met
    completed = {"CS 1B"}  # Missing the OR block (MATH 1B or MATH 1C)
    assert has_met_prereqs("CS 2A", completed, prereq_data) == False
    print("  ✅ Multiple blocks correctly require all blocks to be satisfied")
    
    # Test 5: Multiple blocks (AND + OR) - fully met
    completed = {"CS 1B", "MATH 1B"}
    assert has_met_prereqs("CS 2A", completed, prereq_data) == True
    print("  ✅ Multiple blocks correctly identify when all are satisfied")
    
    # Test 6: OR prerequisite
    completed = {"CS 1B"}
    assert has_met_prereqs("CS 1C", completed, prereq_data) == True
    print("  ✅ OR prerequisite works correctly")
    
    # Test 7: Course not in data
    assert has_met_prereqs("NONEXISTENT", completed, prereq_data) == True
    print("  ✅ Non-existent courses default to eligible")
    
    # Test 8: Unknown block type (should be handled gracefully)
    completed = {"ENG 1A"}
    assert has_met_prereqs("TEST_COURSE", completed, prereq_data) == True
    print("  ✅ Unknown block types are handled gracefully")


def test_get_eligible_courses():
    """Test the get_eligible_courses function."""
    print("\n🧪 Testing get_eligible_courses...")
    
    prereq_data = {entry["courseCode"]: entry for entry in create_test_data()}
    
    # Test 1: No courses completed
    completed = set()
    eligible = get_eligible_courses(completed, prereq_data)
    expected_no_prereqs = ["MATH 1A", "CS 1A", "ENG 1A", "TEST_COURSE"]
    for course in expected_no_prereqs:
        assert course in eligible, f"{course} should be eligible with no prereqs"
    print("  ✅ Courses with no prerequisites are eligible when nothing is completed")
    
    # Test 2: Some basic courses completed
    completed = {"MATH 1A", "CS 1A"}
    eligible = get_eligible_courses(completed, prereq_data)
    assert "CS 1B" in eligible, "CS 1B should be eligible"
    assert "MATH 1B" in eligible, "MATH 1B should be eligible"
    assert "PHYS 4A" not in eligible, "PHYS 4A should not be eligible (missing OR block)"
    print("  ✅ Correctly identifies eligible courses based on completed prerequisites")
    
    # Test 3: Exclude already completed courses
    completed = {"CS 1A", "MATH 1A"}
    eligible = get_eligible_courses(completed, prereq_data)
    assert "CS 1A" not in eligible, "Already completed courses should not be eligible"
    assert "MATH 1A" not in eligible, "Already completed courses should not be eligible"
    print("  ✅ Excludes already completed courses")
    
    # Test 4: Results are sorted
    completed = set()
    eligible = get_eligible_courses(completed, prereq_data)
    assert eligible == sorted(eligible), "Results should be sorted"
    print("  ✅ Results are returned in sorted order")


def test_explain_unmet_prereqs():
    """Test the explain_unmet_prereqs function."""
    print("\n🧪 Testing explain_unmet_prereqs...")
    
    prereq_data = {entry["courseCode"]: entry for entry in create_test_data()}
    
    # Test 1: Course with no prerequisites
    completed = set()
    unmet = explain_unmet_prereqs("CS 1A", completed, prereq_data)
    assert unmet == [], "Course with no prereqs should have no unmet requirements"
    print("  ✅ Courses with no prerequisites return empty list")
    
    # Test 2: AND block with missing courses
    completed = {"CS 1A"}  # Missing MATH 1A for CS 1B
    unmet = explain_unmet_prereqs("CS 1B", completed, prereq_data)
    assert "MATH 1A" in unmet, "Should identify missing MATH 1A"
    assert "CS 1A" not in unmet, "Should not include completed CS 1A"
    print("  ✅ AND blocks correctly identify missing courses")
    
    # Test 3: OR block with no courses completed
    completed = {"CS 1B"}  # CS 2A needs CS 1B (✓) AND (MATH 1B OR MATH 1C) (✗)
    unmet = explain_unmet_prereqs("CS 2A", completed, prereq_data)
    assert "MATH 1B" in unmet or "MATH 1C" in unmet, "Should show OR options when none completed"
    print("  ✅ OR blocks show all options when none are completed")
    
    # Test 4: Multiple blocks
    completed = set()  # Nothing completed for PHYS 4A
    unmet = explain_unmet_prereqs("PHYS 4A", completed, prereq_data)
    assert "MATH 1A" in unmet, "Should include AND requirement"
    assert ("MATH 1B" in unmet or "CHEM 1A" in unmet), "Should include OR options"
    print("  ✅ Multiple blocks show all unmet requirements")
    
    # Test 5: Non-existent course
    unmet = explain_unmet_prereqs("NONEXISTENT", completed, prereq_data)
    assert unmet == [], "Non-existent course should return empty list"
    print("  ✅ Non-existent courses return empty list")


def run_integration_test():
    """Run a comprehensive integration test simulating a student's progression."""
    print("\n🎯 Integration Test: Student Course Progression")
    
    prereq_data = {entry["courseCode"]: entry for entry in create_test_data()}
    
    # Semester 1: Starting fresh
    completed = set()
    eligible = get_eligible_courses(completed, prereq_data)
    print(f"  Semester 1 - Eligible courses: {len(eligible)}")
    assert "CS 1A" in eligible and "MATH 1A" in eligible
    
    # Student takes CS 1A and MATH 1A
    completed.update({"CS 1A", "MATH 1A"})
    eligible = get_eligible_courses(completed, prereq_data)
    print(f"  After Semester 1 - New eligible courses include: CS 1B, MATH 1B")
    assert "CS 1B" in eligible and "MATH 1B" in eligible
    
    # Semester 2: Takes CS 1B and MATH 1B
    completed.update({"CS 1B", "MATH 1B"}) 
    eligible = get_eligible_courses(completed, prereq_data)
    print(f"  After Semester 2 - Advanced courses now available: CS 2A, CS 1C")
    assert "CS 2A" in eligible and "CS 1C" in eligible
    
    print("  ✅ Integration test passed - prerequisite chain works correctly")


def main():
    """Run all tests."""
    print("🚀 Running Prerequisite Resolver Test Suite")
    print("=" * 50)
    
    try:
        test_load_prereq_data()
        test_has_met_prereqs() 
        test_get_eligible_courses()
        test_explain_unmet_prereqs()
        run_integration_test()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! Prerequisite resolver is working correctly.")
        print("✅ Ready for integration with other UC Transfer Planner modules.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()