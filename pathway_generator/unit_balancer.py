"""
UC CS Transfer Planner - Unit Balancer Module
============================================

Generates term-by-term course schedules for CCC students planning to transfer to UC for CS.
Balances unit loads based on semester (18 units) vs quarter (20 units) systems.

Key Features:
- Enforces prerequisite ordering via prereq_resolver.py
- Prioritizes required courses (Major Prep, GE) over electives  
- Respects unit caps per term based on CCC system type
- Optimizes course sequencing for transfer readiness

Author: UC Transfer Planner Project
Date: Aug 3, 2025
"""

from typing import Dict, List, Set, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_prerequisites_met(course_code: str, completed: Set[str], prereq_data: Dict) -> bool:
    """
    Wrapper function to handle prereq checking with proper data format.
    This handles the mismatch between our data format and prereq_resolver expectations.
    """
    if course_code not in prereq_data:
        return True  # No prerequisites
    
    course_info = prereq_data[course_code]
    prereqs = course_info.get("prerequisites")
    
    if not prereqs or prereqs == "":
        return True  # Empty prerequisites
    
    # Handle your actual prerequisite structure
    def check_prereq_structure(structure) -> bool:
        """Recursively check prerequisite structure"""
        if isinstance(structure, str):
            return structure in completed
        elif isinstance(structure, list):
            # For lists, all items must be satisfied (implicit AND)
            return all(check_prereq_structure(item) for item in structure)
        elif isinstance(structure, dict):
            for key, value in structure.items():
                key_lower = key.lower()
                if key_lower == "and":
                    # All conditions in AND must be true
                    return all(check_prereq_structure(item) for item in value)
                elif key_lower == "or":
                    # At least one condition in OR must be true
                    return any(check_prereq_structure(item) for item in value)
        return False
    
    return check_prereq_structure(prereqs)

try:
    from prereq_resolver import load_prereq_data
    PREREQ_RESOLVER_AVAILABLE = True
except ImportError:
    print("Warning: prereq_resolver.py not found. Using mock function.")
    PREREQ_RESOLVER_AVAILABLE = False
    def load_prereq_data(path: str) -> Dict:
        """Mock function"""
        return {}

def get_unit_cap(ccc_name: str, term_type_map: Dict[str, str]) -> int:
    """
    Determine unit cap based on CCC's term system.
    
    Args:
        ccc_name: Name of the community college
        term_type_map: Dictionary mapping CCC names to "semester" or "quarter"
    
    Returns:
        20 for quarter system, 18 for semester system
    """
    term_type = term_type_map.get(ccc_name, "semester").lower()
    return 20 if term_type == "quarter" else 18

def calculate_course_priority(course_code: str, course_data: Dict, required_tags: Set[str], 
                            prereq_data: Dict, unscheduled: Set[str]) -> Tuple[int, int, float]:
    """
    Calculate priority score for course scheduling.
    
    Priority factors (in order):
    1. Number of required tags matched (higher = more important)
    2. Number of unscheduled courses that depend on this one (prerequisites)
    3. Unit value (higher units = slight preference to balance terms)
    
    Args:
        course_code: Course identifier
        course_data: Course info including tags and units
        required_tags: Set of tags we need to fulfill
        prereq_data: Prerequisite relationships
        unscheduled: Set of courses not yet scheduled
        
    Returns:
        Tuple of (tag_matches, dependent_count, units) for sorting
    """
    # Count matching required tags
    course_tags = set(course_data.get("tags", []))
    tag_matches = len(course_tags.intersection(required_tags))
    
    # Count how many unscheduled courses depend on this one
    dependent_count = 0
    for other_course in unscheduled:
        if other_course != course_code and other_course in prereq_data:
            prereq_info = prereq_data[other_course]
            # Check if this course appears in the prerequisites
            if _course_in_prereqs(course_code, prereq_info):
                dependent_count += 1
    
    units = course_data.get("units", 0.0)
    
    return (tag_matches, dependent_count, units)

def _course_in_prereqs(course_code: str, prereq_info: Dict) -> bool:
    """
    Check if a course appears anywhere in prerequisite structure.
    Handles the actual format: {"and": [{"or": ["COURSE1", "COURSE2"]}]}
    """
    if not prereq_info:
        return False
    
    prereqs = prereq_info.get("prerequisites")
    if not prereqs or prereqs == "":
        return False
    
    def _search_prereq_structure(structure) -> bool:
        """Recursively search through prerequisite structure"""
        if isinstance(structure, str):
            return structure == course_code
        elif isinstance(structure, list):
            return any(_search_prereq_structure(item) for item in structure)
        elif isinstance(structure, dict):
            # Handle "and" and "or" keys (lowercase in your data)
            for key, value in structure.items():
                if key.lower() in ["and", "or"]:
                    if _search_prereq_structure(value):
                        return True
        return False
    
    return _search_prereq_structure(prereqs)

def schedule_courses(completed: Set[str], 
                    tagged_courses: Dict[str, Dict], 
                    prereq_data: Dict[str, Dict],
                    required_tags: Set[str],
                    ccc_name: str,
                    term_type_map: Dict[str, str],
                    max_terms: int = 6) -> List[Dict]:
    """
    Generate term-by-term course schedule for transfer planning.
    
    Args:
        completed: Set of course codes already completed
        tagged_courses: Dict of {course_code: {"units": float, "tags": List[str]}}
        prereq_data: Prerequisite data from *_prereqs.json
        required_tags: Set of required tags (e.g., {"Major Prep", "GE-A1"})
        ccc_name: Name of community college
        term_type_map: Maps CCC names to "semester"/"quarter"
        max_terms: Maximum number of terms to schedule
        
    Returns:
        List of dicts, one per term:
        {
            "term_index": int,
            "courses": List[str], 
            "total_units": float
        }
    """
    unit_cap = get_unit_cap(ccc_name, term_type_map)
    current_completed = set(completed)
    
    # Find unscheduled courses that match required tags
    unscheduled = set()
    for course_code, course_data in tagged_courses.items():
        if course_code in completed:
            continue
        course_tags = set(course_data.get("tags", []))
        if course_tags.intersection(required_tags):
            unscheduled.add(course_code)
    
    schedule = []
    
    for term_index in range(max_terms):
        if not unscheduled:
            break  # No more courses to schedule
            
        # Get eligible courses (prerequisites met)
        eligible = []
        for course in unscheduled:
            if check_prerequisites_met(course, current_completed, prereq_data):
                eligible.append(course)
        
        if not eligible:
            break  # No eligible courses (prerequisite deadlock)
        
        # Sort eligible courses by priority
        eligible_with_priority = []
        for course in eligible:
            course_data = tagged_courses[course]
            priority = calculate_course_priority(
                course, course_data, required_tags, prereq_data, unscheduled
            )
            eligible_with_priority.append((course, priority, course_data))
        
        # Sort by priority (descending for all factors)
        eligible_with_priority.sort(key=lambda x: x[1], reverse=True)
        
        # Select courses for this term up to unit cap
        term_courses = []
        term_units = 0.0
        
        for course, priority, course_data in eligible_with_priority:
            course_units = course_data.get("units", 0.0)
            
            # Check if adding this course would exceed unit cap
            if term_units + course_units <= unit_cap:
                term_courses.append(course)
                term_units += course_units
                
                # Remove from unscheduled and add to completed
                unscheduled.remove(course)
                current_completed.add(course)
        
        # If no courses were scheduled this term, we're done
        if not term_courses:
            break
            
        # Add term to schedule
        schedule.append({
            "term_index": term_index,
            "courses": term_courses,
            "total_units": term_units
        })
    
    return schedule

def print_schedule(schedule: List[Dict], ccc_name: str, term_type_map: Dict[str, str]) -> None:
    """
    Pretty print the course schedule for debugging/testing.
    
    Args:
        schedule: Output from schedule_courses()
        ccc_name: Community college name
        term_type_map: Term system mapping
    """
    term_type = term_type_map.get(ccc_name, "semester")
    unit_cap = get_unit_cap(ccc_name, term_type_map)
    
    print(f"\n=== Course Schedule for {ccc_name} ({term_type} system, {unit_cap} unit cap) ===")
    
    if not schedule:
        print("No courses scheduled.")
        return
    
    total_units = 0
    total_courses = 0
    
    for term in schedule:
        term_num = term["term_index"] + 1
        courses = term["courses"]
        units = term["total_units"]
        
        print(f"\nTerm {term_num}: {units}/{unit_cap} units")
        for course in courses:
            print(f"  - {course}")
        
        total_units += units
        total_courses += len(courses)
    
    print(f"\nSummary:")
    print(f"  Total terms: {len(schedule)}")
    print(f"  Total courses: {total_courses}")
    print(f"  Total units: {total_units}")

# Real data integration and testing
if __name__ == "__main__":
    import json
    import os
    
    # Use actual file paths matching your repo structure
    def load_real_data(ccc_name_key):
        """Load real data files from your repo structure"""
        try:
            # Convert display name to file format (based on your actual files)
            ccc_file_name = ccc_name_key.lower().replace(" ", "_").replace(".", "")
            
            # Load tagged courses
            tagged_path = f"course_tags/{ccc_file_name}_tags.json"
            if os.path.exists(tagged_path):
                with open(tagged_path, "r") as f:
                    tagged_courses = json.load(f)
            else:
                print(f"Warning: {tagged_path} not found")
                return None, None, None
            
            # Load prerequisites using your prereq_resolver
            prereq_path = f"prerequisites/{ccc_file_name}_prereqs.json"
            if os.path.exists(prereq_path):
                prereqs = load_prereq_data(prereq_path)
            else:
                print(f"Warning: {prereq_path} not found")
                prereqs = {}
            
            # Load term types
            if os.path.exists("ccc_term_types.json"):
                with open("ccc_term_types.json", "r") as f:
                    term_types = json.load(f)
            else:
                print("Warning: ccc_term_types.json not found")
                term_types = {}
            
            return tagged_courses, prereqs, term_types
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return None, None, None
    
    # Test with Foothill College (your sample data)
    print("="*60)
    print("TESTING: Foothill College (Real Data)")
    print("="*60)
    
    tagged_courses, prereqs, term_types = load_real_data("Foothill College")
    
    if tagged_courses is not None:
        # Realistic CS transfer scenario
        completed = set()  # Starting fresh
        
        # Comprehensive required tags based on your data structure
        required_tags = {
            "Major Prep",
            "7CP-Math",     # For 7-course pattern math
            "GE-B4",        # Math/Science
            "IGETC-2"       # IGETC math
        }
        
        print(f"Available courses: {len(tagged_courses)}")
        print(f"Courses with prereqs: {len(prereqs)}")
        
        # Show sample course structure
        sample_course = list(tagged_courses.keys())[0]
        print(f"Sample course structure: {sample_course}")
        print(f"  Data: {tagged_courses[sample_course]}")
        
        if sample_course in prereqs:
            print(f"  Prerequisites: {prereqs[sample_course].get('prerequisites', 'None')}")
        
        # Filter courses matching our tags
        matching_courses = {
            course: data for course, data in tagged_courses.items()
            if any(tag in data.get("tags", []) for tag in required_tags)
        }
        print(f"Courses matching required tags: {len(matching_courses)}")
        
        # Run the scheduler
        schedule = schedule_courses(
            completed=completed,
            tagged_courses=tagged_courses,
            prereq_data=prereqs,
            required_tags=required_tags,
            ccc_name="Foothill College",
            term_type_map=term_types,
            max_terms=6
        )
        
        print_schedule(schedule, "Foothill College", term_types)
        
        # Show some scheduled courses with details
        if schedule:
            print(f"\nDetailed Course Information:")
            for term in schedule[:2]:  # First 2 terms
                print(f"\nTerm {term['term_index'] + 1}:")
                for course in term['courses']:
                    course_data = tagged_courses[course]
                    print(f"  {course} ({course_data['courseName']})")
                    print(f"    Units: {course_data['units']}")
                    print(f"    Tags: {course_data['tags']}")
                    if course in prereqs and prereqs[course].get('prerequisites'):
                        print(f"    Prerequisites: {prereqs[course]['prerequisites']}")
    
    else:
        print("Could not load Foothill College data - using mock test...")
        
        # Fallback mock test with correct data structure
        sample_tagged_courses = {
            "MATH 1A": {"courseName": "Calculus I", "units": 5.0, "tags": ["Major Prep", "GE-B4"]},
            "MATH 1B": {"courseName": "Calculus II", "units": 5.0, "tags": ["Major Prep", "GE-B4"]},
            "CS 1A": {"courseName": "Java I", "units": 4.5, "tags": ["Major Prep"]},
            "CS 1B": {"courseName": "Java II", "units": 4.5, "tags": ["Major Prep"]},
        }
        
        sample_prereqs = {
            "MATH 1B": {
                "courseCode": "MATH 1B",
                "prerequisites": {"and": [{"or": ["MATH 1A"]}]}
            },
            "CS 1B": {
                "courseCode": "CS 1B", 
                "prerequisites": {"and": [{"or": ["CS 1A"]}]}
            }
        }
        
        sample_term_types = {"Foothill College": "quarter"}
        required_tags = {"Major Prep", "GE-B4"}
        
        schedule = schedule_courses(
            completed=set(),
            tagged_courses=sample_tagged_courses,
            prereq_data=sample_prereqs,
            required_tags=required_tags,
            ccc_name="Foothill College",
            term_type_map=sample_term_types,
            max_terms=4
        )
        
        print_schedule(schedule, "Foothill College", sample_term_types)