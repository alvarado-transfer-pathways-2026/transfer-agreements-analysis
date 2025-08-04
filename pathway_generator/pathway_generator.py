"""
UC CS Transfer Planner - Master Pathway Generator (IMPROVED)
===========================================================

The main orchestrator that combines all modules to generate complete 
transfer pathways from CCC to UC for Computer Science majors.

Key Improvements:
- Better GE course filtering to avoid math overload
- Improved course prioritization for balanced scheduling
- Enhanced elective filling when required courses run out
- Better duplicate course handling
- More realistic transfer planning

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
    
    def _load_ccc_data(self, ccc_name: str) -> Tuple[Dict, Dict]:
        """
        Load tagged courses and prerequisites for a specific CCC.
        
        Args:
            ccc_name: Community college name
            
        Returns:
            Tuple of (tagged_courses, prereq_data)
        """
        if ccc_name in self.cached_tagged_courses:
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
        self.cached_tagged_courses[ccc_name] = tagged_courses
        self.cached_prereqs[ccc_name] = prereqs
        
        return tagged_courses, prereqs
    
    def _get_required_tags(self, ge_pattern: str, target_ucs: List[str]) -> Set[str]:
        """
        Determine which course tags are required based on GE pattern and UC targets.
        
        Args:
            ge_pattern: GE pattern being followed
            target_ucs: List of target UC campuses
            
        Returns:
            Set of required tags for course filtering
        """
        required_tags = {"Major Prep"}  # Always need major prep
        
        # Add GE tags based on pattern
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
        
        # Add UC-specific tags (if we had them)
        for uc in target_ucs:
            if uc == "UCI":
                required_tags.update(["UCI_CS1", "UCI_CS2", "UCI_MATH"])
            elif uc == "UCSB":
                required_tags.update(["UCSB_CS8", "UCSB_CS16", "UCSB_MATH"])
            # Add more UC-specific tags as needed
        
        return required_tags
    
    def _filter_courses_intelligently(self, tagged_courses: Dict, required_tags: Set[str], 
                                    completed_courses: Set[str]) -> Dict:
        """
        Intelligently filter courses to avoid scheduling issues like too many math courses.
        
        Args:
            tagged_courses: All available courses
            required_tags: Required tags
            completed_courses: Already completed courses
            
        Returns:
            Filtered course dictionary
        """
        filtered_courses = {}
        math_courses = []
        
        for course_code, course_data in tagged_courses.items():
            if course_code in completed_courses:
                continue
                
            course_tags = set(course_data.get("tags", []))
            
            # Check if course matches any required tags
            if course_tags.intersection(required_tags):
                # Special handling for math courses to prevent overloading
                if any(tag in course_tags for tag in ["7CP-Math", "GE-B4", "IGETC-2"]):
                    math_courses.append((course_code, course_data))
                else:
                    filtered_courses[course_code] = course_data
        
        # Limit math courses to prevent the overloading issue we saw
        # Keep only the most essential math courses (typically calc sequence)
        essential_math_keywords = ["Calculus", "MATH 1A", "MATH 1B", "MATH 1C"]
        math_courses.sort(key=lambda x: (
            # Prioritize courses with essential keywords
            -sum(1 for keyword in essential_math_keywords if keyword in x[1].get("courseName", "")),
            # Then by course code (to get sequence order)
            x[0]
        ))
        
        # Add only first 4-5 math courses to prevent overload
        for course_code, course_data in math_courses[:5]:
            filtered_courses[course_code] = course_data
        
        return filtered_courses
    
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
        
        # Find courses not in current schedule that could be electives
        scheduled_courses = set()
        for term in schedule:
            scheduled_courses.update(term["courses"])
        
        available_electives = []
        for course_code, course_data in tagged_courses.items():
            if (course_code not in completed_courses and 
                course_code not in scheduled_courses):
                available_electives.append((course_code, course_data))
        
        # Sort electives by units (prefer higher unit courses for efficiency)
        available_electives.sort(key=lambda x: -x[1].get("units", 0))
        
        # Add electives to fill out the schedule
        unit_cap = 20 if self.term_types.get("Foothill College", "quarter") == "quarter" else 18
        
        modified_schedule = schedule.copy()
        elective_index = 0
        
        for term_idx, term in enumerate(modified_schedule):
            current_units = term["total_units"]
            
            # Try to fill this term to capacity
            while (current_units < unit_cap and 
                   elective_index < len(available_electives) and
                   total_units < target_units):
                
                elective_code, elective_data = available_electives[elective_index]
                elective_units = elective_data.get("units", 0)
                
                if current_units + elective_units <= unit_cap:
                    # Add this elective to the term
                    modified_schedule[term_idx]["courses"].append(elective_code)
                    modified_schedule[term_idx]["total_units"] += elective_units
                    current_units += elective_units
                    total_units += elective_units
                
                elective_index += 1
        
        # If we still need more units, add a new term
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
                elective_units = elective_data.get("units", 0)
                
                if term_units + elective_units <= unit_cap:
                    new_term["courses"].append(elective_code)
                    new_term["total_units"] += elective_units
                    term_units += elective_units
                    total_units += elective_units
                
                elective_index += 1
            
            if new_term["courses"]:  # Only add if we found courses
                modified_schedule.append(new_term)
            else:
                break
        
        return modified_schedule
    
    def generate_pathway(self, 
                        ccc_name: str,
                        target_ucs: List[str],
                        ge_pattern: str = "IGETC",
                        completed_courses: Set[str] = None,
                        max_terms: int = 6) -> Dict[str, Any]:
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
        
        # Load CCC-specific data
        tagged_courses, prereq_data = self._load_ccc_data(ccc_name)
        
        if not tagged_courses:
            return {"error": f"No course data found for {ccc_name}"}
        
        # Initialize trackers
        ge_tracker = GE_Tracker(self.ge_data, self.term_types)
        ge_tracker.load_pattern(ge_pattern)
        
        major_checker = MajorChecker()
        
        # Add already completed courses to trackers
        for course_code in completed_courses:
            if course_code in tagged_courses:
                course_data = tagged_courses[course_code]
                tags = course_data.get("tags", [])
                units = course_data.get("units", 3)
                
                ge_tracker.add_completed_course(course_code, tags, units)
                major_checker.add_completed_course(course_code, tags)
        
        # Determine required tags for scheduling
        required_tags = self._get_required_tags(ge_pattern, target_ucs)
        
        # Filter courses intelligently to avoid issues
        filtered_courses = self._filter_courses_intelligently(
            tagged_courses, required_tags, completed_courses
        )
        
        print(f"   Required tags: {len(required_tags)} tags")
        print(f"   Available courses: {len(tagged_courses)} total, {len(filtered_courses)} filtered")
        
        # Generate term-by-term schedule
        schedule = schedule_courses(
            completed=completed_courses,
            tagged_courses=filtered_courses,  # Use filtered courses
            prereq_data=prereq_data,
            required_tags=required_tags,
            ccc_name=ccc_name,
            term_type_map=self.term_types,
            max_terms=max_terms
        )
        
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
                    
                    ge_tracker.add_completed_course(course_code, tags, units)
                    major_checker.add_completed_course(course_code, tags)
            
            current_completed.update(term_courses)
            
            # Capture progress after this term
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
        final_ge_remaining = ge_tracker.get_remaining_requirements(ge_pattern, ccc_name)
        final_major_status = {}
        for uc in target_ucs:
            final_major_status[uc] = major_checker.get_fulfillment_status(uc)
        
        # Calculate totals
        total_units = sum(term["total_units"] for term in schedule)
        total_courses = sum(len(term["courses"]) for term in schedule)
        
        # Determine readiness
        ge_complete = ge_tracker.is_fulfilled(ge_pattern, ccc_name)
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
                    "units": course_data.get("units", 0),
                    "tags": course_data.get("tags", [])
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
            for course in term["courses"]:
                tags_str = ", ".join(course["tags"][:3])  # Show first 3 tags
                if len(course["tags"]) > 3:
                    tags_str += f" (+{len(course['tags'])-3} more)"
                
                print(f"     {course['course_code']}: {course['course_name']}")
                print(f"       {course['units']} units | {tags_str}")
        
        # Show remaining requirements if not complete
        if not summary["transfer_ready"]:
            print(f"\n⚠️  REMAINING REQUIREMENTS")
            
            ge_remaining = pathway["requirements_analysis"]["ge_remaining"]
            actual_ge_remaining = {k: v for k, v in ge_remaining.items() if not k.endswith("_taken")}
            
            if actual_ge_remaining:
                print(f"   GE Requirements ({len(actual_ge_remaining)} remaining):")
                for req_id, req_info in list(actual_ge_remaining.items())[:5]:  # Show first 5
                    courses_needed = req_info.get('courses_remaining', 0)
                    units_needed = req_info.get('units_remaining', 0)
                    if courses_needed > 0 or units_needed > 0:
                        print(f"     {req_info['name']}: {courses_needed} courses, {units_needed} units")
            
            major_status = pathway["requirements_analysis"]["major_status"]
            for uc, status in major_status.items():
                if not status.get("is_complete", False):
                    remaining = status.get("remaining_details", {})
                    if remaining:
                        print(f"   {uc} Major Requirements ({len(remaining)} remaining):")
                        for req_id, req_info in list(remaining.items())[:3]:  # Show first 3
                            print(f"     {req_info['name']}")
        
        # Show what makes this transfer ready or not
        print(f"\n🎓 TRANSFER READINESS ANALYSIS")
        ge_ok = "✅" if summary['ge_complete'] else "❌"
        major_ok = "✅" if any(summary['major_complete'].values()) else "❌"
        units_ok = "✅" if summary['total_units'] >= 60 else "❌"
        
        print(f"   GE Requirements: {ge_ok}")
        print(f"   Major Prep: {major_ok}")
        print(f"   60+ Units: {units_ok} ({summary['total_units']} units)")
        
        if summary['transfer_ready']:
            print(f"   🎉 Ready to transfer to: {[uc for uc, complete in summary['major_complete'].items() if complete]}")
        else:
            missing = []
            if not summary['ge_complete']:
                missing.append("GE requirements")
            if not any(summary['major_complete'].values()):
                missing.append("major prep")
            if summary['total_units'] < 60:
                missing.append(f"{60 - summary['total_units']} more units")
            print(f"   📝 Still need: {', '.join(missing)}")


def main():
    """Main function for testing and demonstration."""
    # Initialize pathway generator with parent directory as base
    # Since pathway_generator.py is in pathway_generator/ subdirectory
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generator = PathwayGenerator(base_dir=parent_dir)
    
    # Test with Foothill College
    print("🚀 UC CS Transfer Pathway Generator (IMPROVED)")
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