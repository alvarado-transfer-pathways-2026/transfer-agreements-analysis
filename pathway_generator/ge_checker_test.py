#!/usr/bin/env python3
"""
GE_Tracker Testing Suite
Tests all functionality of ge_checker.py with realistic data scenarios
"""

import json
import sys
from pathlib import Path

# Add the pathway_generator directory to path for imports
sys.path.append(str(Path(__file__).parent / "pathway_generator"))

try:
    from ge_checker import GE_Tracker
except ImportError:
    print("❌ Could not import GE_Tracker. Make sure ge_checker.py is in pathway_generator/")
    sys.exit(1)

class GE_TrackerTest:
    def __init__(self):
        self.test_count = 0
        self.passed_count = 0
        self.failed_tests = []
        
        # Sample GE requirements data (simplified version)
        self.sample_ge_data = {
            "requirementPatterns": [
                {
                    "patternId": "IGETC",
                    "requirements": [
                        {
                            "reqId": "GE_1A",
                            "name": "English Composition",
                            "minCourses": 1,
                            "minUnits": 3
                        },
                        {
                            "reqId": "GE_2A",
                            "name": "Mathematical Concepts",
                            "minCourses": 1,
                            "minUnits": 3
                        },
                        {
                            "reqId": "GE_3",
                            "name": "Arts and Humanities",
                            "minCourses": 3,
                            "minUnits": 9,
                            "subRequirements": [
                                {
                                    "reqId": "GE_3A",
                                    "name": "Arts",
                                    "minCourses": 1,
                                    "minUnits": 3
                                },
                                {
                                    "reqId": "GE_3B",
                                    "name": "Humanities", 
                                    "minCourses": 1,
                                    "minUnits": 3
                                }
                            ]
                        },
                        {
                            "reqId": "GE_4",
                            "name": "Social and Behavioral Sciences",
                            "minCourses": 2,
                            "minUnits": 6,
                            "subRequirements": [
                                {
                                    "reqId": "GE_4B",
                                    "name": "Economics",
                                    "minCourses": 1,
                                    "minUnits": 3
                                },
                                {
                                    "reqId": "GE_4C", 
                                    "name": "Ethnic Studies",
                                    "minCourses": 1,
                                    "minUnits": 3
                                }
                            ]
                        }
                    ]
                },
                {
                    "patternId": "7CoursePattern",
                    "requirements": [
                        {
                            "reqId": "GE_General",
                            "name": "General Education", 
                            "minCourses": 7,
                            "subRequirements": [
                                {
                                    "reqId": "GE_Area_A",
                                    "name": "English Communication",
                                    "maxCourses": 2
                                },
                                {
                                    "reqId": "GE_Area_B", 
                                    "name": "Scientific Inquiry",
                                    "maxCourses": 2
                                },
                                {
                                    "reqId": "GE_Area_C",
                                    "name": "Arts and Humanities", 
                                    "maxCourses": 2
                                },
                                {
                                    "reqId": "GE_Area_D",
                                    "name": "Social Sciences",
                                    "maxCourses": 2
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        # Sample term types data
        self.sample_term_types = {
            "De Anza College": "quarter",
            "Santa Monica College": "semester", 
            "Foothill College": "quarter",
            "Los Angeles Pierce College": "semester"
        }

    def assert_equal(self, actual, expected, test_name):
        """Helper method for assertions"""
        self.test_count += 1
        if actual == expected:
            print(f"✅ {test_name}")
            self.passed_count += 1
        else:
            print(f"❌ {test_name}")
            print(f"   Expected: {expected}")
            print(f"   Actual: {actual}")
            self.failed_tests.append(test_name)

    def assert_true(self, condition, test_name):
        """Helper method for boolean assertions"""
        self.test_count += 1
        if condition:
            print(f"✅ {test_name}")
            self.passed_count += 1
        else:
            print(f"❌ {test_name}")
            self.failed_tests.append(test_name)

    def assert_contains_key(self, dictionary, key, test_name):
        """Helper method to check if dictionary contains key"""
        self.test_count += 1
        if key in dictionary:
            print(f"✅ {test_name}")
            self.passed_count += 1
        else:
            print(f"❌ {test_name}")
            print(f"   Key '{key}' not found in: {list(dictionary.keys())}")
            self.failed_tests.append(test_name)

    def test_initialization(self):
        """Test GE_Tracker initialization"""
        print("\n🧪 Testing Initialization...")
        
        tracker = GE_Tracker(self.sample_ge_data, self.sample_term_types)
        
        self.assert_equal(len(tracker.completed_courses), 0, "Empty completed courses on init")
        self.assert_equal(len(tracker.ge_patterns), 0, "Empty GE patterns on init")
        self.assert_true(hasattr(tracker, 'ccc_term_types'), "Has ccc_term_types attribute")

    def test_load_pattern(self):
        """Test pattern loading functionality"""
        print("\n🧪 Testing Pattern Loading...")
        
        tracker = GE_Tracker(self.sample_ge_data, self.sample_term_types)
        
        # Test IGETC loading
        tracker.load_pattern("IGETC")
        self.assert_true("IGETC" in tracker.ge_patterns, "IGETC pattern loaded")
        self.assert_equal(len(tracker.ge_patterns["IGETC"]), 4, "IGETC has 4 requirements")
        
        # Test 7-Course Pattern loading
        tracker.load_pattern("7CoursePattern")
        self.assert_true("7CoursePattern" in tracker.ge_patterns, "7CoursePattern loaded")
        
        # Test invalid pattern
        tracker.load_pattern("NonExistent")
        self.assert_true("NonExistent" not in tracker.ge_patterns, "Invalid pattern not loaded")

    def test_add_completed_course(self):
        """Test adding completed courses"""
        print("\n🧪 Testing Add Completed Course...")
        
        tracker = GE_Tracker(self.sample_ge_data, self.sample_term_types)
        
        # Add some courses
        tracker.add_completed_course("ENGL 100", ["GE_1A"], 3)
        tracker.add_completed_course("MATH 120", ["GE_2A"], 4)
        
        self.assert_equal(len(tracker.completed_courses), 2, "Two courses added")
        self.assert_equal(tracker.completed_courses[0]["name"], "ENGL 100", "First course name correct")
        self.assert_equal(tracker.completed_courses[0]["units"], 3, "First course units correct")
        self.assert_equal(tracker.completed_courses[1]["units"], 4, "Second course units correct")

    def test_unit_scaling(self):
        """Test quarter/semester unit scaling"""
        print("\n🧪 Testing Unit Scaling...")
        
        tracker = GE_Tracker(self.sample_ge_data, self.sample_term_types)
        
        semester_scale = tracker._get_unit_scale("Santa Monica College")
        quarter_scale = tracker._get_unit_scale("De Anza College")
        unknown_scale = tracker._get_unit_scale("Unknown College")
        
        self.assert_equal(semester_scale, 1.0, "Semester scale is 1.0")
        self.assert_equal(quarter_scale, 0.67, "Quarter scale is 0.67")
        self.assert_equal(unknown_scale, 1.0, "Unknown defaults to semester (1.0)")

    def test_simple_requirements(self):
        """Test simple requirement evaluation"""
        print("\n🧪 Testing Simple Requirements...")
        
        tracker = GE_Tracker(self.sample_ge_data, self.sample_term_types)
        tracker.load_pattern("IGETC")
        
        # Test unfulfilled requirement
        remaining = tracker.get_remaining_requirements("IGETC")
        self.assert_contains_key(remaining, "GE_1A", "GE_1A appears in remaining (unfulfilled)")
        self.assert_equal(remaining["GE_1A"]["courses_remaining"], 1, "GE_1A needs 1 course")
        self.assert_equal(remaining["GE_1A"]["tags"], ["GE_1A"], "GE_1A has correct tags")
        
        # Add a course and test again
        tracker.add_completed_course("ENGL 100", ["GE_1A"], 3)
        remaining = tracker.get_remaining_requirements("IGETC")
        self.assert_true("GE_1A" not in remaining, "GE_1A no longer in remaining (fulfilled)")

    def test_subrequirements_igetc(self):
        """Test IGETC subrequirement logic"""
        print("\n🧪 Testing IGETC Subrequirements...")
        
        tracker = GE_Tracker(self.sample_ge_data, self.sample_term_types)
        tracker.load_pattern("IGETC")
        
        # Add courses for subrequirements
        tracker.add_completed_course("ART 100", ["GE_3A"], 3)
        tracker.add_completed_course("ECON 101", ["GE_4B"], 3)
        
        remaining = tracker.get_remaining_requirements("IGETC")
        
        # GE_3A should be fulfilled
        self.assert_true("GE_3A" not in remaining, "GE_3A fulfilled")
        # GE_3B should still be needed
        self.assert_contains_key(remaining, "GE_3B", "GE_3B still needed")
        # GE_4B should be fulfilled  
        self.assert_true("GE_4B" not in remaining, "GE_4B fulfilled")
        # GE_4C should still be needed
        self.assert_contains_key(remaining, "GE_4C", "GE_4C still needed")

    def test_seven_course_pattern(self):
        """Test 7-Course Pattern special logic"""
        print("\n🧪 Testing 7-Course Pattern...")
        
        tracker = GE_Tracker(self.sample_ge_data, self.sample_term_types)
        tracker.load_pattern("7CoursePattern")
        
        # Add courses respecting maxCourses limits
        tracker.add_completed_course("ENGL 100", ["GE_Area_A"], 3)
        tracker.add_completed_course("ENGL 101", ["GE_Area_A"], 3)  # 2 in Area A (max)
        tracker.add_completed_course("CHEM 101", ["GE_Area_B"], 4)
        tracker.add_completed_course("ART 100", ["GE_Area_C"], 3)
        tracker.add_completed_course("PSYC 100", ["GE_Area_D"], 3)
        # Total: 5 courses, need 2 more
        
        remaining = tracker.get_remaining_requirements("7CoursePattern")
        
        # Should need 2 more general courses
        self.assert_contains_key(remaining, "GE_General", "GE_General still has remaining")
        self.assert_equal(remaining["GE_General"]["courses_remaining"], 2, "Need 2 more courses")
        
        # Should show taken counts per area
        self.assert_contains_key(remaining, "GE_Area_A_taken", "Shows Area A taken count")
        self.assert_contains_key(remaining, "GE_Area_B_taken", "Shows Area B taken count")

    def test_quarter_system_units(self):
        """Test unit calculations with quarter system"""
        print("\n🧪 Testing Quarter System Units...")
        
        tracker = GE_Tracker(self.sample_ge_data, self.sample_term_types)
        tracker.load_pattern("IGETC")
        
        # Add course at De Anza (quarter system)
        tracker.add_completed_course("MATH 1A", ["GE_2A"], 5)  # 5 quarter units
        
        remaining = tracker.get_remaining_requirements("IGETC", "De Anza College")
        
        # With quarter scaling, 5 quarter units = ~3.35 semester units, so should fulfill 3-unit requirement
        self.assert_true("GE_2A" not in remaining, "GE_2A fulfilled with quarter units")

    def test_is_fulfilled(self):
        """Test completion checking"""
        print("\n🧪 Testing Completion Checking...")
        
        tracker = GE_Tracker(self.sample_ge_data, self.sample_term_types)
        tracker.load_pattern("IGETC")
        
        # Initially not fulfilled
        self.assert_equal(tracker.is_fulfilled("IGETC"), False, "IGETC not initially fulfilled")
        
        # Add minimum required courses
        tracker.add_completed_course("ENGL 100", ["GE_1A"], 3)
        tracker.add_completed_course("MATH 120", ["GE_2A"], 3)
        tracker.add_completed_course("ART 100", ["GE_3A"], 3)
        tracker.add_completed_course("HIST 100", ["GE_3B"], 3)
        tracker.add_completed_course("ECON 101", ["GE_4B"], 3)
        tracker.add_completed_course("ETHN 100", ["GE_4C"], 3)
        
        # Should now be fulfilled
        self.assert_equal(tracker.is_fulfilled("IGETC"), True, "IGETC fulfilled after adding all courses")

    def test_alias_methods(self):
        """Test alias methods for pathway_generator compatibility"""
        print("\n🧪 Testing Alias Methods...")
        
        tracker = GE_Tracker(self.sample_ge_data, self.sample_term_types)
        tracker.load_pattern("IGETC")
        
        # Test check_ge_progress
        result = tracker.check_ge_progress("ENGL 100", ["GE_1A"], 3)
        self.assert_equal(result["course_added"], "ENGL 100", "check_ge_progress adds course")
        self.assert_equal(len(tracker.completed_courses), 1, "Course actually added")
        
        # Test get_remaining_ge (alias)
        remaining1 = tracker.get_remaining_ge("IGETC")
        remaining2 = tracker.get_remaining_requirements("IGETC")
        self.assert_equal(remaining1, remaining2, "get_remaining_ge aliases correctly")
        
        # Test ge_is_complete (alias)
        complete1 = tracker.ge_is_complete("IGETC")
        complete2 = tracker.is_fulfilled("IGETC")
        self.assert_equal(complete1, complete2, "ge_is_complete aliases correctly")

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n🧪 Testing Edge Cases...")
        
        tracker = GE_Tracker(self.sample_ge_data, self.sample_term_types)
        
        # Test with invalid pattern
        remaining = tracker.get_remaining_requirements("InvalidPattern")
        self.assert_equal(remaining, {}, "Invalid pattern returns empty dict")
        
        # Test with no courses
        tracker.load_pattern("IGETC")
        remaining = tracker.get_remaining_requirements("IGETC")
        self.assert_true(len(remaining) > 0, "Empty tracker has remaining requirements")
        
        # Test course with no tags
        tracker.add_completed_course("RANDOM 100", [], 3)
        remaining_after = tracker.get_remaining_requirements("IGETC")
        self.assert_equal(len(remaining), len(remaining_after), "Course with no tags doesn't affect requirements")

    def run_all_tests(self):
        """Run the complete test suite"""
        print("🚀 Starting GE_Tracker Test Suite")
        print("=" * 50)
        
        self.test_initialization()
        self.test_load_pattern()
        self.test_add_completed_course()
        self.test_unit_scaling()
        self.test_simple_requirements()
        self.test_subrequirements_igetc()
        self.test_seven_course_pattern()
        self.test_quarter_system_units()
        self.test_is_fulfilled()
        self.test_alias_methods()
        self.test_edge_cases()
        
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {self.passed_count}/{self.test_count} passed")
        
        if self.failed_tests:
            print(f"❌ Failed tests: {', '.join(self.failed_tests)}")
            return False
        else:
            print("✅ All tests passed!")
            return True

def test_with_real_data():
    """Test with actual project data files if available"""
    print("\n🔄 Testing with Real Project Data...")
    
    # Try to load actual ge_reqs.json
    ge_reqs_path = Path("prerequisites/ge_reqs.json")
    if ge_reqs_path.exists():
        print(f"✅ Found {ge_reqs_path}")
        with open(ge_reqs_path, 'r') as f:
            real_ge_data = json.load(f)
            
        tracker = GE_Tracker(real_ge_data)
        tracker.load_pattern("IGETC")
        
        print(f"✅ Loaded IGETC with {len(tracker.ge_patterns['IGETC'])} requirements")
        
        # Try loading 7-Course Pattern
        tracker.load_pattern("7CoursePattern")
        if "7CoursePattern" in tracker.ge_patterns:
            print(f"✅ Loaded 7CoursePattern with {len(tracker.ge_patterns['7CoursePattern'])} requirements")
        else:
            print("⚠️  7CoursePattern not found in real data")
            
    else:
        print(f"⚠️  {ge_reqs_path} not found, skipping real data test")
    
    # Try to load actual ccc_term_types.json
    term_types_path = Path("ccc_term_types.json")
    if term_types_path.exists():
        print(f"✅ Found {term_types_path}")
        with open(term_types_path, 'r') as f:
            real_term_types = json.load(f)
        print(f"✅ Loaded term types for {len(real_term_types)} colleges")
    else:
        print(f"⚠️  {term_types_path} not found")

if __name__ == "__main__":
    # Run the main test suite
    test_suite = GE_TrackerTest()
    success = test_suite.run_all_tests()
    
    # Try testing with real data
    test_with_real_data()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)