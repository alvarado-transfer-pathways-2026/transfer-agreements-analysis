"""
UC CS Transfer Major Checker Module

This module evaluates whether a community college student has satisfied
the major preparation requirements for one or more UC campuses based on
completed courses and their associated tags from the course_tags directory.

Author: UC CS Transfer Planner
Updated: Aug 3, 2025
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Set


class MajorChecker:
    """
    Tracks major preparation requirements for multiple UC campuses using course tags.
    
    Attributes:
        uc_major_reqs (dict): UC major requirements mapping
        completed_courses (list): List of completed courses with tags
        course_tags_cache (dict): Cached course tag data
    """
    
    def __init__(self, uc_major_reqs: Optional[Dict[str, Any]] = None):
        """
        Initialize MajorChecker with UC major requirements.
        
        Args:
            uc_major_reqs: Dictionary mapping UC names to their requirements.
                If None, loads default CS requirements.
        """
        if uc_major_reqs is None:
            self.uc_major_reqs = self._load_default_cs_requirements()
        else:
            self.uc_major_reqs = uc_major_reqs
            
        self.completed_courses = []  # Each course: {name: str, tags: List[str]}
        self.course_tags_cache = {}  # Cache for course tag lookups
    
    def _load_default_cs_requirements(self) -> Dict[str, Any]:
        """
        Load default CS major requirements for UC campuses.
        
        Returns:
            Dictionary of UC CS major requirements
        """
        return {
            "UCI": {
                "CS1": {
                    "name": "Introduction to Computer Science I",
                    "tags": ["UCI_CS1", "Major Prep"],
                    "description": "First programming course"
                },
                "CS2": {
                    "name": "Introduction to Computer Science II", 
                    "tags": ["UCI_CS2", "Major Prep"],
                    "description": "Second programming course"
                },
                "MATH": {
                    "name": "Calculus I",
                    "tags": ["UCI_MATH", "General_Calculus1", "Major Prep"],
                    "description": "Single variable calculus"
                }
            },
            "UCSB": {
                "CS8": {
                    "name": "Introduction to Computer Science",
                    "tags": ["UCSB_CS8", "Major Prep"],
                    "description": "First programming course"
                },
                "CS16": {
                    "name": "Problem Solving with Computers I",
                    "tags": ["UCSB_CS16", "Major Prep"],
                    "description": "Advanced programming"
                },
                "MATH": {
                    "name": "Calculus with Applications",
                    "tags": ["UCSB_MATH", "General_Calculus1", "Major Prep"],
                    "description": "Calculus for CS"
                }
            },
            "UCLA": {
                "CS31": {
                    "name": "Introduction to Computer Science I",
                    "tags": ["UCLA_CS31", "Major Prep"],
                    "description": "First programming course"
                },
                "CS32": {
                    "name": "Introduction to Computer Science II",
                    "tags": ["UCLA_CS32", "Major Prep"],
                    "description": "Data structures and algorithms"
                },
                "MATH": {
                    "name": "Calculus of Several Variables",
                    "tags": ["UCLA_MATH", "General_Calculus1", "Major Prep"],
                    "description": "Multivariable calculus"
                }
            },
            "UCSD": {
                "CSE8A": {
                    "name": "Introduction to Computer Science: Java I",
                    "tags": ["UCSD_CSE8A", "Major Prep"],
                    "description": "Java programming basics"
                },
                "CSE8B": {
                    "name": "Introduction to Computer Science: Java II",
                    "tags": ["UCSD_CSE8B", "Major Prep"],
                    "description": "Advanced Java programming"
                },
                "MATH": {
                    "name": "Calculus and Analytic Geometry",
                    "tags": ["UCSD_MATH", "General_Calculus1", "Major Prep"],
                    "description": "Single and multivariable calculus"
                }
            },
            "UCB": {
                "CS61A": {
                    "name": "Structure and Interpretation of Computer Programs",
                    "tags": ["UCB_CS61A", "Major Prep"],
                    "description": "Programming paradigms"
                },
                "CS61B": {
                    "name": "Data Structures",
                    "tags": ["UCB_CS61B", "Major Prep"],
                    "description": "Data structures and algorithms"
                },
                "MATH": {
                    "name": "Calculus",
                    "tags": ["UCB_MATH", "General_Calculus1", "Major Prep"],
                    "description": "Single variable calculus"
                }
            }
        }
    
    def load_course_tags_from_file(self, cc_name: str, course_tags_dir: str = "course_tags") -> Dict[str, Dict[str, Any]]:
        """
        Load course tags for a specific community college from the course_tags directory.
        
        Args:
            cc_name: Community college name (normalized)
            course_tags_dir: Directory containing course tag files
            
        Returns:
            Dictionary mapping course codes to their full course info (name, units, tags)
        """
        if cc_name in self.course_tags_cache:
            return self.course_tags_cache[cc_name]
        
        # Normalize CC name for filename - match course_tagger.py format
        normalized_name = cc_name.lower().replace(" ", "_").replace(".", "").replace("'", "")
        filename = f"{normalized_name}_tags.json"
        filepath = Path(course_tags_dir) / filename
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                course_data = json.load(f)
                
            # course_data is already in the format we need from course_tagger.py:
            # {
            #   "CIS 22A": {
            #     "courseName": "Programming Concepts and Methodology I",
            #     "units": 4,
            #     "tags": ["Major Prep", "IGETC-2"]
            #   }
            # }
            self.course_tags_cache[cc_name] = course_data
            return course_data
            
        except FileNotFoundError:
            print(f"Warning: Course tags file not found: {filepath}")
            return {}
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in file: {filepath}")
            return {}
    
    def add_completed_course(self, course_name: str, tags: List[str]) -> None:
        """
        Store a completed course with its tags for future matching.
        
        Args:
            course_name: Name of the completed course
            tags: List of tags associated with the course
        """
        self.completed_courses.append({
            "name": course_name,
            "tags": tags
        })
    
    def _is_req_fulfilled(self, required_tags: List[str]) -> bool:
        """
        Check if a requirement is fulfilled by any completed course.
        
        Args:
            required_tags: List of tags that can fulfill this requirement
            
        Returns:
            True if any completed course has at least one matching tag
        """
        for course in self.completed_courses:
            for tag in course["tags"]:
                if tag in required_tags:
                    return True
        return False
    
    def get_remaining_requirements(self, uc_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Get unfulfilled major requirements for a specific UC.
        
        Args:
            uc_name: Name of the UC (e.g., "UCI", "UCSB")
            
        Returns:
            Dictionary of unfulfilled requirements with their details
        """
        if uc_name not in self.uc_major_reqs:
            return {}  # UC not found
        
        remaining = {}
        for req_id, req_info in self.uc_major_reqs[uc_name].items():
            if not self._is_req_fulfilled(req_info["tags"]):
                remaining[req_id] = req_info  # requirement not met
        
        return remaining
    
    def is_fulfilled(self, uc_name: str) -> bool:
        """
        Check if all major prep requirements are satisfied for a UC.
        
        Args:
            uc_name: Name of the UC
            
        Returns:
            True if all major requirements are fulfilled
        """
        return len(self.get_remaining_requirements(uc_name)) == 0
    
    def get_fulfillment_status(self, uc_name: str) -> Dict[str, Any]:
        """
        Get detailed fulfillment status for a UC.
        
        Args:
            uc_name: Name of the UC
            
        Returns:
            Dictionary with completion status and progress details
        """
        if uc_name not in self.uc_major_reqs:
            return {"error": f"UC '{uc_name}' not found in requirements"}
        
        total_reqs = len(self.uc_major_reqs[uc_name])
        remaining_reqs = self.get_remaining_requirements(uc_name)
        completed_reqs = total_reqs - len(remaining_reqs)
        
        return {
            "uc_name": uc_name,
            "is_complete": self.is_fulfilled(uc_name),
            "total_requirements": total_reqs,
            "completed_requirements": completed_reqs,
            "remaining_requirements": len(remaining_reqs),
            "completion_percentage": round((completed_reqs / total_reqs) * 100, 1) if total_reqs > 0 else 0,
            "remaining_details": remaining_reqs
        }
    
    def get_courses_fulfilling_req(self, uc_name: str, req_id: str) -> List[Dict[str, Any]]:
        """
        Get all completed courses that fulfill a specific requirement.
        
        Args:
            uc_name: Name of the UC
            req_id: Requirement ID (e.g., "CS1", "CS2")
            
        Returns:
            List of courses that fulfill this requirement
        """
        if uc_name not in self.uc_major_reqs or req_id not in self.uc_major_reqs[uc_name]:
            return []
        
        required_tags = self.uc_major_reqs[uc_name][req_id]["tags"]
        fulfilling_courses = []
        
        for course in self.completed_courses:
            for tag in course["tags"]:
                if tag in required_tags:
                    fulfilling_courses.append(course)
                    break  # Don't add the same course multiple times
        
        return fulfilling_courses
    
    def load_and_check_cc_courses(self, cc_name: str, completed_course_codes: List[str], 
                                  course_tags_dir: str = "course_tags") -> Dict[str, Any]:
        """
        Load course tags for a CC and check completion status for given courses.
        
        Args:
            cc_name: Community college name
            completed_course_codes: List of completed course codes (e.g., ["CIS 22A", "MATH 1A"])
            course_tags_dir: Directory containing course tag files
            
        Returns:
            Dictionary with loaded courses and their fulfillment status
        """
        course_data = self.load_course_tags_from_file(cc_name, course_tags_dir)
        
        # Add completed courses with their tags
        loaded_courses = []
        for course_code in completed_course_codes:
            if course_code in course_data:
                course_info = course_data[course_code]
                course_name = course_info.get('courseName', course_code)
                tags = course_info.get('tags', [])
                units = course_info.get('units', 0)
                
                self.add_completed_course(course_code, tags)
                loaded_courses.append({
                    "courseCode": course_code,
                    "courseName": course_name,
                    "units": units,
                    "tags": tags
                })
            else:
                # Course not found in tags, add with minimal info
                self.add_completed_course(course_code, ["Unknown"])
                loaded_courses.append({
                    "courseCode": course_code,
                    "courseName": "UNKNOWN COURSE",
                    "units": 0,
                    "tags": ["Unknown"]
                })
        
        # Get fulfillment status for all UCs
        all_status = {}
        for uc_name in self.uc_major_reqs.keys():
            all_status[uc_name] = self.get_fulfillment_status(uc_name)
        
        return {
            "cc_name": cc_name,
            "loaded_courses": loaded_courses,
            "total_completed": len(completed_course_codes),
            "total_units": sum(course['units'] for course in loaded_courses),
            "uc_fulfillment_status": all_status
        }
    
    # === Public Interface Functions (for pathway_generator.py compatibility) ===
    
    def check_major_progress(self, course_name: str, tags: List[str]) -> Dict[str, Any]:
        """
        Add a course and track its tags for major progress.
        
        Args:
            course_name: Name of the course to add
            tags: List of tags associated with the course
            
        Returns:
            Dictionary confirming the course was added
        """
        self.add_completed_course(course_name, tags)
        return {
            "course_added": course_name,
            "tags_applied": tags,
            "total_courses": len(self.completed_courses)
        }
    
    def get_remaining_major(self, uc_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Get remaining major requirements for a specific UC.
        
        Args:
            uc_name: Name of the UC
            
        Returns:
            Dictionary of remaining requirements
        """
        return self.get_remaining_requirements(uc_name)
    
    def major_is_complete(self, uc_name: str) -> bool:
        """
        Check if all major preparation is complete for a UC.
        
        Args:
            uc_name: Name of the UC
            
        Returns:
            True if all major requirements are fulfilled
        """
        return self.is_fulfilled(uc_name)


def load_major_checker_from_existing_data(course_tags_dir: str = "course_tags") -> MajorChecker:
    """
    Create a MajorChecker instance using the existing project structure.
    
    Args:
        course_tags_dir: Directory containing course tag files
        
    Returns:
        Initialized MajorChecker instance
    """
    return MajorChecker()


# === Example Usage ===
if __name__ == "__main__":
    # Initialize checker with default CS requirements
    checker = MajorChecker()
    
    # Example: Load and check De Anza courses
    cc_name = "De_Anza_College"  # Match your SELECTED_CCCS format
    completed_courses = ["CIS 22A", "CIS 22B", "MATH 1A"]
    
    # Load course data and check fulfillment
    result = checker.load_and_check_cc_courses(cc_name, completed_courses)
    
    print(f"Loaded {result['total_completed']} courses from {result['cc_name']}")
    print(f"Total units: {result['total_units']}")
    print("\nCompleted Courses:")
    for course in result['loaded_courses']:
        print(f"  {course['courseCode']}: {course['courseName']} ({course['units']} units)")
        print(f"    Tags: {', '.join(course['tags'])}")
    
    print("\nUC Fulfillment Status:")
    for uc, status in result['uc_fulfillment_status'].items():
        if 'error' not in status:
            print(f"{uc}: {status['completed_requirements']}/{status['total_requirements']} "
                  f"({status['completion_percentage']}% complete)")
    
    # Test direct interface functions
    print(f"\nUCI Major Complete: {checker.major_is_complete('UCI')}")
    
    remaining = checker.get_remaining_major("UCI")
    if remaining:
        print("UCI Remaining Requirements:")
        for req_id, req_info in remaining.items():
            print(f"  {req_id}: {req_info['name']}")
    
    # Example of adding individual courses (for pathway_generator.py integration)
    checker.check_major_progress("PHYS 4A", ["Major Prep", "IGETC-5A"])
    print(f"\nAfter adding PHYS 4A - UCI Complete: {checker.major_is_complete('UCI')}")