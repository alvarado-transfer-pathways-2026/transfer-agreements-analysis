"""
UC CS Transfer Planner - Master Pathway Generator (IMPROVED v2)
==============================================================

The main orchestrator that combines all modules to generate complete 
transfer pathways from CCC to UC for Computer Science majors.

Key Improvements in v2:
- Fixed math course overload (prevents duplicate calc courses)
- Prioritized GE requirements alongside major prep
- Improved course selection with balanced scheduling
- Better prerequisite enforcement for math sequences
- Enhanced course filtering with GE priority weighting
- More realistic transfer planning with mixed course types

Author: UC Transfer Planner Project
Date: Aug 4, 2025
"""

import json
import os
import sys
from typing import Dict, List, Set, Tuple, Optional, Any
from pathlib import Path

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules
try:
    from unit_balancer import schedule_courses, get_unit_cap, load_prereq_data
    from ge_checker import GE_Tracker
    from major_checker import MajorChecker
    from prereq_resolver import load_prereq_data as load_prereqs_alt
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    print("Make sure all modules (unit_balancer.py, ge_checker.py, major_checker.py, prereq_resolver.py) are in the same directory.")


class PathwayGenerator:
    """
    Main pathway generator that coordinates all components to create
    comprehensive transfer plans.
    """
    
    def __init__(self, base_dir: str = "."):
        """
        Initialize the pathway generator.
        
        Args:
            base_dir: Base directory containing data files
        """
        self.base_dir = Path(base_dir)
        self.ge_data = None
        self.term_types = {}
        self.cached_tagged_courses = {}
        self.cached_prereqs = {}
        
        # Course priority weights for balanced scheduling
        self.course_priorities = {
            # Highest priority - essential foundations
            "english": 10,
            "math_calc": 9,
            "major_programming": 8,
            
            # High priority - core requirements
            "critical_thinking": 7,
            "major_other": 6,
            "science": 5,
            
            # Medium priority - breadth requirements
            "arts": 4,
            "humanities": 4,
            "social_science": 4,
            "language": 3,
            
            # Lower priority - electives and advanced
            "elective": 2,
            "advanced_math": 1
        }
        
        # Load common data files
        self._load_common_data()
    
    def _load_common_data(self):
        """Load commonly used data files."""
        try:
            # Load GE requirements from prerequisites directory
            ge_path = self.base_dir / "prerequisites" / "ge_reqs.json"
            if ge_path.exists():
                with open(ge_path, 'r') as f:
                    self.ge_data = json.load(f)
                print(f"✅ Loaded GE requirements from {ge_path}")
            else:
                print(f"Warning: {ge_path} not found")
            
            # Load term types from root directory
            term_path = self.base_dir / "ccc_term_types.json"
            if term_path.exists():
                with open(term_path, 'r') as f:
                    self.term_types = json.load(f)
                print(f"✅ Loaded term types from {term_path}")
            else:
                print(f"Warning: {term_path} not found")
                
        except Exception as e:
            print(f"Error loading common data: {e}")
    
    def _load_ccc_data(self, ccc_name: str, include_all_courses: bool = True) -> Tuple[Dict, Dict]:
        """
        Load tagged courses and prerequisites for a specific CCC.
        
        Args:
            ccc_name: Community college name
            include_all_courses: If True, include all courses, not just those with required tags
            
        Returns:
            Tuple of (tagged_courses, prereq_data)
        """
        if ccc_name in self.cached_tagged_courses and not include_all_courses:
            return self.cached_tagged_courses[ccc_name], self.cached_prereqs[ccc_name]
        
        # Convert display name to file format
        ccc_file_name = ccc_name.lower().replace(" ", "_").replace(".", "")
        
        # Load tagged courses
        tagged_courses = {}
        tagged_path = self.base_dir / "course_tags" / f"{ccc_file_name}_tags.json"
        if tagged_path.exists():
            with open(tagged_path, 'r') as f:
                tagged_courses = json.load(f)
        else:
            print(f"Warning: {tagged_path} not found")
        
        # If we don't have many courses, try to load from articulated_courses_json as backup
        if len(tagged_courses) < 50:
            print(f"⚠️  Only {len(tagged_courses)} tagged courses found. Attempting to load additional courses...")
            articulation_path = self.base_dir / "articulated_courses_json" / f"{ccc_file_name}.json"
            if articulation_path.exists():
                try:
                    with open(articulation_path, 'r') as f:
                        articulation_data = json.load(f)
                    
                    # Add courses from articulation data with basic tags
                    for course_code, course_info in articulation_data.items():
                        if course_code not in tagged_courses:
                            # Assign basic tags based on course code/name patterns
                            basic_tags = self._assign_basic_tags(course_code, course_info)
                            tagged_courses[course_code] = {
                                "courseName": course_info.get("courseName", "Unknown Course"),
                                "units": course_info.get("units", 3),
                                "tags": basic_tags
                            }
                    
                    print(f"✅ Added {len(articulation_data)} courses from articulation data")
                except Exception as e:
                    print(f"Error loading articulation data: {e}")
        
        # Load prerequisites
        prereqs = {}
        prereq_path = self.base_dir / "prerequisites" / f"{ccc_file_name}_prereqs.json"
        if prereq_path.exists():
            try:
                prereqs = load_prereq_data(str(prereq_path))
            except:
                # Fallback to direct JSON loading
                with open(prereq_path, 'r') as f:
                    raw_prereqs = json.load(f)
                    prereqs = {entry["courseCode"]: entry for entry in raw_prereqs}
        else:
            print(f"Warning: {prereq_path} not found")
        
        # Cache the results
        if not include_all_courses:
            self.cached_tagged_courses[ccc_name] = tagged_courses
            self.cached_prereqs[ccc_name] = prereqs
        
        return tagged_courses, prereqs
    
    def _assign_basic_tags(self, course_code: str, course_info: Dict) -> List[str]:
        """
        Assign basic tags to courses based on course code and name patterns.
        
        Args:
            course_code: Course code (e.g., "ENGL 1A")
            course_info: Course information dictionary
            
        Returns:
            List of basic tags
        """
        tags = []
        course_name = course_info.get("courseName", "").upper()
        subject = course_code.split()[0].upper() if " " in course_code else course_code.upper()
        
        # English courses
        if subject in ["ENGL", "ENGLISH"]:
            if any(term in course_name for term in ["COMPOSITION", "WRITING", "ENGLISH"]):
                tags.extend(["IGETC-1A", "7CP-English"])
            if any(term in course_name for term in ["CRITICAL", "THINKING", "ARGUMENT"]):
                tags.extend(["IGETC-1B", "7CP-English"])
        
        # Math courses
        elif subject in ["MATH", "MATHEMATICS"]:
            if any(term in course_name for term in ["CALCULUS", "CALC"]):
                tags.extend(["IGETC-2", "7CP-Math", "GE-B4", "Major Prep"])
            elif any(term in course_name for term in ["STATISTICS", "STAT", "ALGEBRA"]):
                tags.extend(["IGETC-2", "7CP-Math", "GE-B4"])
        
        # Computer Science courses
        elif subject in ["CS", "CIS", "COMP", "COMPSCI"]:
            tags.append("Major Prep")
        
        # Science courses
        elif subject in ["PHYS", "PHYSICS", "CHEM", "CHEMISTRY", "BIO", "BIOLOGY"]:
            tags.extend(["IGETC-5A", "IGETC-5B", "7CP-Science"])
            if "LAB" in course_name:
                tags.append("IGETC-5C")
        
        # Arts courses
        elif subject in ["ART", "ARTS", "MUSIC", "THEATRE", "THEATER", "DANCE"]:
            tags.extend(["IGETC-3A", "7CP-Arts"])
        
        # Humanities courses
        elif subject in ["HIST", "HISTORY", "PHIL", "PHILOSOPHY", "LIT", "LITERATURE"]:
            tags.extend(["IGETC-3B", "7CP-Humanities"])
        
        # Social Sciences
        elif subject in ["PSYC", "PSYCHOLOGY", "SOC", "SOCIOLOGY", "POLI", "ECON", "ECONOMICS"]:
            tags.extend(["IGETC-4", "7CP-Social"])
        
        # Languages
        elif subject in ["SPAN", "FRENCH", "GERMAN", "JAPANESE", "CHINESE"]:
            tags.append("IGETC-6")
        
        return tags if tags else ["Elective"]
    
    def _get_course_priority(self, course_code: str, course_data: Dict, completed_courses: Set[str]) -> int:
        """
        Calculate priority score for a course based on its importance and type.
        
        Args:
            course_code: Course code
            course_data: Course information
            completed_courses: Already completed courses
            
        Returns:
            Priority score (higher = more important)
        """
        tags = course_data.get("tags", [])
        course_name = course_data.get("courseName", "").upper()
        subject = course_code.split()[0].upper() if " " in course_code else course_code.upper()
        
        # Base priority from course type
        base_priority = 0
        
        # English composition (highest priority)
        if any(tag in tags for tag in ["IGETC-1A", "7CP-English"]) and "COMPOSITION" in course_name:
            base_priority = self.course_priorities["english"]
        
        # Critical thinking
        elif any(tag in tags for tag in ["IGETC-1B"]) or "CRITICAL" in course_name:
            base_priority = self.course_priorities["critical_thinking"]
        
        # Calculus sequence (high priority, but prevent duplicates)
        elif subject == "MATH" and "CALC" in course_name:
            # Check if we already have calculus courses
            calc_completed = any("CALC" in self.cached_tagged_courses.get("default", {}).get(cc, {}).get("courseName", "") 
                               for cc in completed_courses)
            if not calc_completed:
                base_priority = self.course_priorities["math_calc"]
            else:
                base_priority = self.course_priorities["advanced_math"]  # Lower priority for additional calc
        
        # Programming courses
        elif "Major Prep" in tags and subject in ["CS", "CIS", "COMP"]:
            if any(term in course_name for term in ["PROGRAMMING", "JAVA", "PYTHON", "C++"]):
                base_priority = self.course_priorities["major_programming"]
            else:
                base_priority = self.course_priorities["major_other"]
        
        # Science courses
        elif any(tag in tags for tag in ["IGETC-5A", "IGETC-5B", "IGETC-5C", "7CP-Science"]):
            base_priority = self.course_priorities["science"]
        
        # Arts and Humanities
        elif any(tag in tags for tag in ["IGETC-3A", "7CP-Arts"]):
            base_priority = self.course_priorities["arts"]
        elif any(tag in tags for tag in ["IGETC-3B", "7CP-Humanities"]):
            base_priority = self.course_priorities["humanities"]
        
        # Social Sciences
        elif any(tag in tags for tag in ["IGETC-4", "7CP-Social"]):
            base_priority = self.course_priorities["social_science"]
        
        # Language
        elif "IGETC-6" in tags:
            base_priority = self.course_priorities["language"]
        
        # Default to elective priority
        else:
            base_priority = self.course_priorities["elective"]
        
        # Boost priority for prerequisite courses
        if self._is_prerequisite_for_other_courses(course_code):
            base_priority += 2
        
        # Reduce priority for advanced courses if basics aren't done
        if self._is_advanced_course(course_code, course_name) and not self._has_prerequisites_completed(course_code, completed_courses):
            base_priority -= 3
        
        return max(0, base_priority)
    
    def _is_prerequisite_for_other_courses(self, course_code: str) -> bool:
        """Check if this course is a prerequisite for other courses."""
        # Common prerequisite patterns
        subject = course_code.split()[0].upper() if " " in course_code else ""
        number = course_code.split()[-1] if " " in course_code else ""
        
        # First courses in sequences are usually prerequisites
        if number in ["1A", "1", "100", "101"]:
            return True
        
        # English composition and calculus are prerequisites for many courses
        if subject in ["ENGL", "MATH"] and any(n in number for n in ["1", "A"]):
            return True
        
        return False
    
    def _is_advanced_course(self, course_code: str, course_name: str) -> bool:
        """Check if this is an advanced course that should be taken later."""
        # Advanced indicators
        advanced_terms = ["ADVANCED", "INTERMEDIATE", "II", "III", "2B", "2C", "3B", "3C"]
        return any(term in course_name.upper() or term in course_code.upper() for term in advanced_terms)
    
    def _has_prerequisites_completed(self, course_code: str, completed_courses: Set[str]) -> bool:
        """Check if prerequisites for this course are completed."""
        # Simplified prerequisite checking
        # In a full implementation, this would check the actual prerequisite data
        
        # For calculus sequence
        if "1B" in course_code and not any("1A" in cc for cc in completed_courses):
            return False
        if "1C" in course_code and not any("1B" in cc for cc in completed_courses):
            return False
        
        # For programming sequence
        if any(term in course_code for term in ["2A", "1B", "3A"]):
            return any("1A" in cc for cc in completed_courses)
        
        return True  # Assume prerequisites are met for other courses
    
    def _get_required_tags(self, ge_pattern: str, target_ucs: List[str]) -> Set[str]:
        """
        Determine which course tags are required based on GE pattern and UC targets.
        Include ALL necessary tags for a complete transfer pathway.
        
        Args:
            ge_pattern: GE pattern being followed
            target_ucs: List of target UC campuses
            
        Returns:
            Set of required tags for course filtering
        """
        required_tags = {"Major Prep", "Elective"}  # Always need major prep and allow electives
        
        # Add GE tags based on pattern - be more inclusive
        if ge_pattern == "IGETC":
            required_tags.update([
                "IGETC-1A", "IGETC-1B", "IGETC-1C",  # English/Critical Thinking
                "IGETC-2", "IGETC-2A",               # Mathematical Concepts
                "IGETC-3A", "IGETC-3B",              # Arts and Humanities
                "IGETC-4", "IGETC-4A",               # Social and Behavioral Sciences
                "IGETC-5A", "IGETC-5B", "IGETC-5C",  # Physical and Biological Sciences
                "IGETC-6"                            # Language Other Than English
            ])
        elif ge_pattern == "7CoursePattern":
            required_tags.update([
                "7CP-English", "7CP-Math", "7CP-Arts", "7CP-Humanities",
                "7CP-Social", "7CP-Science", "7CP-Multicultural"
            ])
        
        # Also include GE-B4 and other common tags to capture more courses
        required_tags.update(["GE-B4", "GE-A1", "GE-A2", "GE-C1", "GE-C2", "GE-D1", "GE-E1"])
        
        # Add UC-specific tags (if we had them)
        for uc in target_ucs:
            if uc == "UCI":
                required_tags.update(["UCI_CS1", "UCI_CS2", "UCI_MATH"])
            elif uc == "UCSB":
                required_tags.update(["UCSB_CS8", "UCSB_CS16", "UCSB_MATH"])
        
        return required_tags
    
    def _filter_courses_intelligently(self, tagged_courses: Dict, required_tags: Set[str], 
                                    completed_courses: Set[str]) -> Dict:
        """
        Intelligently filter and prioritize courses for balanced scheduling.
        
        Args:
            tagged_courses: All available courses
            required_tags: Required tags
            completed_courses: Already completed courses
            
        Returns:
            Filtered and prioritized course dictionary
        """
        # First pass: collect all relevant courses
        relevant_courses = {}
        math_courses = []
        
        for course_code, course_data in tagged_courses.items():
            if course_code in completed_courses:
                continue
                
            course_tags = set(course_data.get("tags", []))
            course_name = course_data.get("courseName", "").upper()
            
            # Include if matches required tags OR is a basic course we might need
            if (course_tags.intersection(required_tags) or 
                self._is_basic_required_course(course_code, course_name)):
                
                # Special handling for math courses
                if any(tag in course_tags for tag in ["7CP-Math", "GE-B4", "IGETC-2"]) or "MATH" in course_code:
                    math_courses.append((course_code, course_data))
                else:
                    relevant_courses[course_code] = course_data
        
        # Intelligent math course selection
        filtered_math = self._filter_math_courses_intelligently(math_courses, completed_courses)
        relevant_courses.update(filtered_math)
        
        # Priority-based filtering to ensure we have a good mix
        prioritized_courses = self._prioritize_courses_for_balance(relevant_courses, completed_courses)
        
        return prioritized_courses
    
    def _is_basic_required_course(self, course_code: str, course_name: str) -> bool:
        """Check if this is a basic required course we should include."""
        subject = course_code.split()[0].upper() if " " in course_code else ""
        
        # Always include basic English, Math, Science courses
        if subject in ["ENGL", "ENGLISH"] and any(term in course_name for term in ["COMPOSITION", "WRITING"]):
            return True
        if subject in ["MATH"] and any(term in course_name for term in ["CALCULUS", "ALGEBRA", "STATISTICS"]):
            return True
        if subject in ["PHYS", "CHEM", "BIO"] and any(term in course_name for term in ["GENERAL", "INTRO"]):
            return True
        
        return False
    
    def _filter_math_courses_intelligently(self, math_courses: List[Tuple], completed_courses: Set[str]) -> Dict:
        """
        Filter math courses to prevent overload and duplicates.
        
        Args:
            math_courses: List of (course_code, course_data) tuples
            completed_courses: Already completed courses
            
        Returns:
            Filtered math courses dictionary
        """
        filtered_math = {}
        
        # Group by type
        calculus_courses = []
        stats_courses = []
        algebra_courses = []
        other_math = []
        
        for course_code, course_data in math_courses:
            course_name = course_data.get("courseName", "").upper()
            
            if "CALC" in course_name:
                calculus_courses.append((course_code, course_data))
            elif "STAT" in course_name:
                stats_courses.append((course_code, course_data))
            elif "ALGEBRA" in course_name:
                algebra_courses.append((course_code, course_data))
            else:
                other_math.append((course_code, course_data))
        
        # For calculus: only include the sequence, avoid duplicates
        calc_sequence = self._select_calculus_sequence(calculus_courses, completed_courses)
        filtered_math.update(calc_sequence)
        
        # Include one statistics course if available
        if stats_courses and not any("STAT" in cc for cc in completed_courses):
            # Pick the first/basic statistics course
            stats_courses.sort(key=lambda x: x[0])  # Sort by course code
            filtered_math[stats_courses[0][0]] = stats_courses[0][1]
        
        # Include prerequisite algebra if needed and calculus not complete
        if algebra_courses and not calc_sequence and not any("CALC" in cc for cc in completed_courses):
            algebra_courses.sort(key=lambda x: x[0])
            filtered_math[algebra_courses[0][0]] = algebra_courses[0][1]
        
        # Limit total math courses to 3-4 maximum
        if len(filtered_math) > 4:
            # Keep highest priority math courses
            priority_sorted = sorted(filtered_math.items(), 
                                   key=lambda x: self._get_course_priority(x[0], x[1], completed_courses),
                                   reverse=True)
            filtered_math = dict(priority_sorted[:4])
        
        return filtered_math
    
    def _select_calculus_sequence(self, calculus_courses: List[Tuple], completed_courses: Set[str]) -> Dict:
        """
        Select appropriate calculus sequence, avoiding duplicates.
        
        Args:
            calculus_courses: Available calculus courses
            completed_courses: Already completed courses
            
        Returns:
            Selected calculus courses
        """
        if not calculus_courses:
            return {}
        
        selected = {}
        
        # Group by level (1A, 1B, 1C, etc.)
        calc_by_level = {}
        for course_code, course_data in calculus_courses:
            # Extract level from course code or name
            if "1A" in course_code or "I" in course_data.get("courseName", ""):
                level = "1A"
            elif "1B" in course_code or "II" in course_data.get("courseName", ""):
                level = "1B"
            elif "1C" in course_code or "III" in course_data.get("courseName", ""):
                level = "1C"
            elif "1D" in course_code or "IV" in course_data.get("courseName", ""):
                level = "1D"
            else:
                level = "other"
            
            if level not in calc_by_level:
                calc_by_level[level] = []
            calc_by_level[level].append((course_code, course_data))
        
        # Select one course per level, preferring regular over honors
        for level in ["1A", "1B", "1C", "1D"]:
            if level in calc_by_level:
                courses_at_level = calc_by_level[level]
                
                # Prefer regular over honors (no "H" in course code)
                regular_courses = [c for c in courses_at_level if "H" not in c[0]]
                if regular_courses:
                    selected[regular_courses[0][0]] = regular_courses[0][1]
                else:
                    selected[courses_at_level[0][0]] = courses_at_level[0][1]
                
                # Only include 3-4 calculus courses maximum
                if len(selected) >= 3:
                    break
        
        return selected
    
    def _prioritize_courses_for_balance(self, courses: Dict, completed_courses: Set[str]) -> Dict:
        """
        Prioritize courses to ensure balanced mix of GE and major prep.
        
        Args:
            courses: Available courses
            completed_courses: Already completed courses
            
        Returns:
            Prioritized courses dictionary
        """
        # Calculate priority for each course
        prioritized = []
        for course_code, course_data in courses.items():
            priority = self._get_course_priority(course_code, course_data, completed_courses)
            prioritized.append((priority, course_code, course_data))
        
        # Sort by priority (highest first)
        prioritized.sort(key=lambda x: x[0], reverse=True)
        
        # Ensure we have a good balance by category
        selected = {}
        category_counts = {
            "english": 0,
            "math": 0,
            "major": 0,
            "science": 0,
            "arts": 0,
            "social": 0,
            "other": 0
        }
        
        # Limits per category to ensure balance
        category_limits = {
            "english": 3,
            "math": 4,
            "major": 8,
            "science": 4,
            "arts": 3,
            "social": 3,
            "other": 10
        }
        
        for priority, course_code, course_data in prioritized:
            category = self._get_course_category(course_code, course_data)
            
            if category_counts[category] < category_limits[category]:
                selected[course_code] = course_data
                category_counts[category] += 1
            
            # Don't make the selection too large
            if len(selected) >= 50:
                break
        
        return selected
    
    def _get_course_category(self, course_code: str, course_data: Dict) -> str:
        """Get the category of a course for balancing purposes."""
        tags = course_data.get("tags", [])
        subject = course_code.split()[0].upper() if " " in course_code else ""
        
        if any(tag in tags for tag in ["IGETC-1A", "IGETC-1B", "7CP-English"]):
            return "english"
        elif any(tag in tags for tag in ["IGETC-2", "7CP-Math", "GE-B4"]) or subject == "MATH":
            return "math"
        elif "Major Prep" in tags or subject in ["CS", "CIS", "COMP"]:
            return "major"
        elif any(tag in tags for tag in ["IGETC-5A", "IGETC-5B", "IGETC-5C", "7CP-Science"]):
            return "science"
        elif any(tag in tags for tag in ["IGETC-3A", "7CP-Arts"]):
            return "arts"
        elif any(tag in tags for tag in ["IGETC-4", "7CP-Social"]):
            return "social"
        else:
            return "other"
    
    def _add_electives_if_needed(self, schedule: List[Dict], tagged_courses: Dict, 
                                completed_courses: Set[str], target_units: int = 60) -> List[Dict]:
        """
        Add elective courses if the pathway doesn't reach minimum transfer units.
        
        Args:
            schedule: Current schedule
            tagged_courses: Available courses
            completed_courses: Already completed courses
            target_units: Minimum units needed for transfer
            
        Returns:
            Modified schedule with electives added if needed
        """
        total_units = sum(term["total_units"] for term in schedule)
        
        if total_units >= target_units:
            return schedule  # Already have enough units
        
        print(f"📝 Current total: {total_units} units, need {target_units}. Adding electives...")
        
        # Find courses not in current schedule that could be electives
        scheduled_courses = set()
        for term in schedule:
            scheduled_courses.update(term["courses"])
        
        available_electives = []
        for course_code, course_data in tagged_courses.items():
            if (course_code not in completed_courses and 
                course_code not in scheduled_courses):
                available_electives.append((course_code, course_data))
        
        # Prioritize electives: GE courses first, then others
        available_electives.sort(key=lambda x: (
            -self._get_course_priority(x[0], x[1], completed_courses),
            -x[1].get("units", 0)
        ))
        
        # Add electives to fill out the schedule
        unit_cap = get_unit_cap("Foothill College", self.term_types)  # Get actual unit cap
        
        modified_schedule = schedule.copy()
        elective_index = 0
        
         # First, try to fill existing terms
        for term_idx, term in enumerate(modified_schedule):
            current_units = term["total_units"]

            # Try to fill this term to capacity
            while (current_units < unit_cap and
                   elective_index < len(available_electives) and
                   total_units < target_units):
                
                elective_code, elective_data = available_electives[elective_index]
                elective_units = elective_data.get("units", 3)

                if current_units + elective_units <= unit_cap:
                    modified_schedule[term_idx]["courses"].append(elective_code)
                    modified_schedule[term_idx]["total_units"] += elective_units
                    current_units += elective_units
                    total_units += elective_units
                    print(f"  Added {elective_code} to Term {term_idx + 1}")

                elective_index += 1
        
        # If we still need more units, add new terms
        while total_units < target_units and elective_index < len(available_electives):
            new_term = {
                "term_index": len(modified_schedule),
                "courses": [],
                "total_units": 0.0
            }
            
            # Fill the new term
            term_units = 0.0
            while (term_units < unit_cap and 
                   elective_index < len(available_electives) and
                   total_units < target_units):
                
                elective_code, elective_data = available_electives[elective_index]
                elective_units = elective_data.get("units", 3)
                
                if term_units + elective_units <= unit_cap:
                    new_term["courses"].append(elective_code)
                    new_term["total_units"] += elective_units
                    term_units += elective_units
                    total_units += elective_units
                    print(f"  Added {elective_code} to new Term {len(modified_schedule) + 1}")
                
                elective_index += 1
            
            if new_term["courses"]:  # Only add if we found courses
                modified_schedule.append(new_term)
            else:
                break
        
        print(f"✅ Final total: {total_units} units")
        return modified_schedule
    
    def generate_pathway(self, 
                        ccc_name: str,
                        target_ucs: List[str],
                        ge_pattern: str = "IGETC",
                        completed_courses: Set[str] = None,
                        max_terms: int = 20) -> Dict[str, Any]:
        """
        Generate a complete transfer pathway for a student.
        
        Args:
            ccc_name: Community college name
            target_ucs: List of target UC campuses (e.g., ["UCI", "UCSB"])
            ge_pattern: GE pattern to follow ("IGETC" or "7CoursePattern")
            completed_courses: Set of already completed courses
            max_terms: Maximum terms to plan
            
        Returns:
            Complete pathway dictionary with schedule, requirements, and analysis
        """
        if completed_courses is None:
            completed_courses = set()
        
        print(f"\n🎯 Generating pathway for {ccc_name} → {', '.join(target_ucs)}")
        print(f"   GE Pattern: {ge_pattern}, Max Terms: {max_terms}")
        
        # Load CCC-specific data with all courses
        tagged_courses, prereq_data = self._load_ccc_data(ccc_name, include_all_courses=True)
        
        if not tagged_courses:
            return {"error": f"No course data found for {ccc_name}"}
        
        print(f"   Total courses available: {len(tagged_courses)}")
        
        # Initialize trackers
        ge_tracker = GE_Tracker(self.ge_data, self.term_types) if self.ge_data else None
        major_checker = MajorChecker()
        
        if ge_tracker:
            ge_tracker.load_pattern(ge_pattern)
        
        # Add already completed courses to trackers
        for course_code in completed_courses:
            if course_code in tagged_courses:
                course_data = tagged_courses[course_code]
                tags = course_data.get("tags", [])
                units = course_data.get("units", 3)
                
                if ge_tracker:
                    ge_tracker.add_completed_course(course_code, tags, units)
                major_checker.add_completed_course(course_code, tags)
        
        # Determine required tags for scheduling
        required_tags = self._get_required_tags(ge_pattern, target_ucs)
        
        # Filter courses intelligently with improved logic
        filtered_courses = self._filter_courses_intelligently(
            tagged_courses, required_tags, completed_courses
        )
        
        print(f"   Required tags: {len(required_tags)} tags")
        print(f"   Filtered courses: {len(filtered_courses)} courses")
        print(f"   Course breakdown:")
        
        # Show breakdown by category
        category_counts = {}
        for course_code, course_data in filtered_courses.items():
            category = self._get_course_category(course_code, course_data)
            category_counts[category] = category_counts.get(category, 0) + 1
        
        for category, count in sorted(category_counts.items()):
            print(f"     {category}: {count} courses")
        
        # Generate term-by-term schedule using improved course selection
        try:
            schedule = schedule_courses(
                completed=completed_courses,
                tagged_courses=filtered_courses,
                prereq_data=prereq_data,
                required_tags=required_tags,
                ccc_name=ccc_name,
                term_type_map=self.term_types,
                max_terms=max_terms
            )
        except Exception as e:
            print(f"Error in schedule_courses: {e}")
            # Create a basic schedule if the unit_balancer fails
            schedule = self._create_basic_schedule(filtered_courses, completed_courses, max_terms)
        
        # Add electives if needed to reach 60 units
        schedule = self._add_electives_if_needed(
            schedule, tagged_courses, completed_courses, target_units=60
        )
        
        # Track progress as courses are scheduled
        current_completed = set(completed_courses)
        ge_progress = {}
        major_progress = {}
        
        for term in schedule:
            term_courses = term["courses"]
            
            # Update trackers with this term's courses
            for course_code in term_courses:
                if course_code in tagged_courses:
                    course_data = tagged_courses[course_code]
                    tags = course_data.get("tags", [])
                    units = course_data.get("units", 3)
                    
                    if ge_tracker:
                        ge_tracker.add_completed_course(course_code, tags, units)
                    major_checker.add_completed_course(course_code, tags)
            
            current_completed.update(term_courses)
            
            # Capture progress after this term
            if ge_tracker:
                ge_remaining = ge_tracker.get_remaining_requirements(ge_pattern, ccc_name)
                ge_progress[term["term_index"]] = {
                    "remaining_reqs": len([k for k in ge_remaining.keys() if not k.endswith("_taken")]),
                    "is_complete": ge_tracker.is_fulfilled(ge_pattern, ccc_name)
                }
            
            # Check major progress for each target UC
            major_progress[term["term_index"]] = {}
            for uc in target_ucs:
                major_remaining = major_checker.get_remaining_requirements(uc)
                major_progress[term["term_index"]][uc] = {
                    "remaining_reqs": len(major_remaining),
                    "is_complete": major_checker.is_fulfilled(uc)
                }
        
        # Final analysis
        final_ge_remaining = {}
        ge_complete = False
        if ge_tracker:
            final_ge_remaining = ge_tracker.get_remaining_requirements(ge_pattern, ccc_name)
            ge_complete = ge_tracker.is_fulfilled(ge_pattern, ccc_name)
        
        final_major_status = {}
        for uc in target_ucs:
            final_major_status[uc] = major_checker.get_fulfillment_status(uc)
        
        # Calculate totals
        total_units = sum(term["total_units"] for term in schedule)
        total_courses = sum(len(term["courses"]) for term in schedule)
        
        # Determine readiness
        major_complete = {uc: major_checker.is_fulfilled(uc) for uc in target_ucs}
        transfer_ready = ge_complete and any(major_complete.values()) and total_units >= 60
        
        return {
            "ccc_name": ccc_name,
            "target_ucs": target_ucs,
            "ge_pattern": ge_pattern,
            "schedule": schedule,
            "summary": {
                "total_terms": len(schedule),
                "total_courses": total_courses,
                "total_units": total_units,
                "transfer_ready": transfer_ready,
                "ge_complete": ge_complete,
                "major_complete": major_complete,
                "unit_cap": get_unit_cap(ccc_name, self.term_types),
                "term_type": self.term_types.get(ccc_name, "semester")
            },
            "requirements_analysis": {
                "ge_remaining": final_ge_remaining,
                "major_status": final_major_status,
                "ge_progress": ge_progress,
                "major_progress": major_progress
            },
            "course_details": self._enrich_schedule_with_details(schedule, tagged_courses)
        }
    
    def _create_basic_schedule(self, courses: Dict, completed_courses: Set[str], max_terms: int) -> List[Dict]:
        """
        Create a basic schedule if the main scheduling function fails.
        
        Args:
            courses: Available courses
            completed_courses: Already completed courses
            max_terms: Maximum terms
            
        Returns:
            Basic schedule structure
        """
        print("⚠️  Creating basic schedule as fallback...")
        
        # Sort courses by priority
        prioritized = []
        for course_code, course_data in courses.items():
            if course_code not in completed_courses:
                priority = self._get_course_priority(course_code, course_data, completed_courses)
                prioritized.append((priority, course_code, course_data))
        
        prioritized.sort(key=lambda x: x[0], reverse=True)
        
        # Create terms
        schedule = []
        unit_cap = 18  # Default to semester
        course_index = 0
        
        for term_index in range(max_terms):
            if course_index >= len(prioritized):
                break
                
            term = {
                "term_index": term_index,
                "courses": [],
                "total_units": 0.0
            }
            
            # Fill term to capacity
            while (term["total_units"] < unit_cap and 
                   course_index < len(prioritized)):
                
                priority, course_code, course_data = prioritized[course_index]
                units = course_data.get("units", 3)
                
                if term["total_units"] + units <= unit_cap:
                    term["courses"].append(course_code)
                    term["total_units"] += units
                
                course_index += 1
            
            if term["courses"]:
                schedule.append(term)
        
        return schedule
    
    def _enrich_schedule_with_details(self, schedule: List[Dict], tagged_courses: Dict) -> List[Dict]:
        """
        Add detailed course information to the schedule.
        
        Args:
            schedule: Basic schedule from unit_balancer
            tagged_courses: Course data with names, units, tags
            
        Returns:
            Enriched schedule with full course details
        """
        enriched_schedule = []
        
        for term in schedule:
            enriched_term = {
                "term_index": term["term_index"],
                "total_units": term["total_units"],
                "courses": []
            }
            
            for course_code in term["courses"]:
                course_data = tagged_courses.get(course_code, {})
                enriched_course = {
                    "course_code": course_code,
                    "course_name": course_data.get("courseName", "Unknown Course"),
                    "units": course_data.get("units", 3),
                    "tags": course_data.get("tags", []),
                    "category": self._get_course_category(course_code, course_data)
                }
                enriched_term["courses"].append(enriched_course)
            
            enriched_schedule.append(enriched_term)
        
        return enriched_schedule
    
    def print_pathway_summary(self, pathway: Dict[str, Any]):
        """
        Print a formatted summary of the generated pathway.
        
        Args:
            pathway: Pathway dictionary from generate_pathway()
        """
        if "error" in pathway:
            print(f"❌ Error: {pathway['error']}")
            return
        
        summary = pathway["summary"]
        
        print(f"\n📋 PATHWAY SUMMARY")
        print(f"   CCC: {pathway['ccc_name']}")
        print(f"   Target UCs: {', '.join(pathway['target_ucs'])}")
        print(f"   GE Pattern: {pathway['ge_pattern']}")
        print(f"   Term System: {summary['term_type']} ({summary['unit_cap']} unit cap)")
        
        print(f"\n📊 COMPLETION STATUS")
        print(f"   Terms: {summary['total_terms']}")
        print(f"   Courses: {summary['total_courses']}")
        print(f"   Units: {summary['total_units']}")
        print(f"   Transfer Ready: {'✅ YES' if summary['transfer_ready'] else '❌ NO'}")
        print(f"   GE Complete: {'✅' if summary['ge_complete'] else '❌'}")
        
        print(f"   Major Prep Complete:")
        for uc, complete in summary['major_complete'].items():
            print(f"     {uc}: {'✅' if complete else '❌'}")
        
        print(f"\n📅 TERM-BY-TERM SCHEDULE")
        for term in pathway["course_details"]:
            term_num = term["term_index"] + 1
            units = term["total_units"]
            cap = summary["unit_cap"]
            
            print(f"\n   Term {term_num}: {units}/{cap} units")
            
            # Group courses by category for better readability
            courses_by_category = {}
            for course in term["courses"]:
                category = course.get("category", "other")
                if category not in courses_by_category:
                    courses_by_category[category] = []
                courses_by_category[category].append(course)
            
            # Display courses grouped by category
            for category, courses in courses_by_category.items():
                if len(courses_by_category) > 1:
                    print(f"     {category.upper()}:")
                    prefix = "       "
                else:
                    prefix = "     "
                
                for course in courses:
                    tags_str = ", ".join(course["tags"][:2])  # Show first 2 tags
                    if len(course["tags"]) > 2:
                        tags_str += f" (+{len(course['tags'])-2} more)"
                    
                    print(f"{prefix}{course['course_code']}: {course['course_name']}")
                    print(f"{prefix}  {course['units']} units | {tags_str}")
        
        # Show remaining requirements if not complete
        if not summary["transfer_ready"]:
            print(f"\n⚠️  REMAINING REQUIREMENTS")
            
            ge_remaining = pathway["requirements_analysis"]["ge_remaining"]
            actual_ge_remaining = {k: v for k, v in ge_remaining.items() if not k.endswith("_taken")}
            
            if actual_ge_remaining:
                print(f"   GE Requirements ({len(actual_ge_remaining)} remaining):")
                for req_id, req_info in list(actual_ge_remaining.items())[:5]:  # Show first 5
                    if isinstance(req_info, dict):
                        courses_needed = req_info.get('courses_remaining', 0)
                        units_needed = req_info.get('units_remaining', 0)
                        req_name = req_info.get('name', req_id)
                        if courses_needed > 0 or units_needed > 0:
                            print(f"     {req_name}: {courses_needed} courses, {units_needed} units")
            
            major_status = pathway["requirements_analysis"]["major_status"]
            for uc, status in major_status.items():
                if not status.get("is_complete", False):
                    remaining = status.get("remaining_details", {})
                    if remaining:
                        print(f"   {uc} Major Requirements ({len(remaining)} remaining):")
                        for req_id, req_info in list(remaining.items())[:3]:  # Show first 3
                            req_name = req_info.get('name', req_id) if isinstance(req_info, dict) else str(req_info)
                            print(f"     {req_name}")
        
        # Enhanced transfer readiness analysis
        print(f"\n🎓 TRANSFER READINESS ANALYSIS")
        ge_ok = "✅" if summary['ge_complete'] else "❌"
        major_ok = "✅" if any(summary['major_complete'].values()) else "❌"
        units_ok = "✅" if summary['total_units'] >= 60 else "❌"
        
        print(f"   GE Requirements: {ge_ok}")
        print(f"   Major Prep: {major_ok}")
        print(f"   60+ Units: {units_ok} ({summary['total_units']} units)")
        
        if summary['transfer_ready']:
            ready_ucs = [uc for uc, complete in summary['major_complete'].items() if complete]
            print(f"   🎉 Ready to transfer to: {ready_ucs}")
        else:
            missing = []
            if not summary['ge_complete']:
                missing.append("GE requirements")
            if not any(summary['major_complete'].values()):
                missing.append("major prep")
            if summary['total_units'] < 60:
                missing.append(f"{60 - summary['total_units']:.0f} more units")
            print(f"   📝 Still need: {', '.join(missing)}")
        
        # Show course distribution summary
        print(f"\n📈 COURSE DISTRIBUTION")
        total_by_category = {}
        for term in pathway["course_details"]:
            for course in term["courses"]:
                category = course.get("category", "other")
                total_by_category[category] = total_by_category.get(category, 0) + 1
        
        for category, count in sorted(total_by_category.items()):
            percentage = (count / summary['total_courses']) * 100
            print(f"   {category.title()}: {count} courses ({percentage:.1f}%)")


def main():
    """Main function for testing and demonstration."""
    # Initialize pathway generator with parent directory as base
    # Since pathway_generator.py is in pathway_generator/ subdirectory
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generator = PathwayGenerator(base_dir=parent_dir)
    
    # Test with Foothill College
    print("🚀 UC CS Transfer Pathway Generator (IMPROVED v2)")
    print("=" * 60)
    
    # Generate pathway for Foothill College → UCI/UCSB
    pathway = generator.generate_pathway(
        ccc_name="Foothill College",
        target_ucs=["UCI", "UCSB"],
        ge_pattern="IGETC",
        completed_courses=set(),  # Starting fresh
        max_terms=6
    )
    
    # Print results
    generator.print_pathway_summary(pathway)
    
    # Test with some completed courses
    print("\n" + "=" * 60)
    print("🔄 Testing with some completed courses...")
    
    pathway2 = generator.generate_pathway(
        ccc_name="Foothill College",
        target_ucs=["UCI"],
        ge_pattern="IGETC",
        completed_courses={"MATH 1A", "CS 1A"},  # Some prerequisites done
        max_terms=5
    )
    
    generator.print_pathway_summary(pathway2)


if __name__ == "__main__":
    main()
                