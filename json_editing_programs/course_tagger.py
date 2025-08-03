#!/usr/bin/env python3
"""
course_tagger.py - UC CS Transfer Course Tagger

Creates comprehensive course tagging files for each CCC that include:
- Course names and units from prereqs
- Major Prep tags for UC CS requirements
- GE tags (IGETC and UC GE patterns)
- Fallback course names from UC articulations
"""

import json
import csv
import os
import re
from typing import Dict, List, Set, Tuple, Any

# Top CCCs for processing (15 priority colleges)
# Names match your existing file structure
SELECTED_CCCS = [
    "City_College_of_San_Francisco",
    "Cabrillo_College",
    "Chabot_College", 
    "Los_Angeles_Pierce_College",
    "Diablo_Valley_College",
    "Palomar_College",
    "Folsom_Lake_College",
    "Foothill_College",
    "Orange_Coast_College",
    "Mt._San_Jacinto_College",
    "MiraCosta_College",
    "Las_Positas_College",
    "Los_Angeles_City_College",
    "Cosumnes_River_College",
    "De_Anza_College"
]

def load_json(filepath: str) -> Dict:
    """Load JSON file with error handling."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filepath} not found, returning empty dict")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filepath}: {e}")
        return {}

def write_json(filepath: str, data: Dict) -> None:
    """Write JSON file with proper formatting."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def extract_cc_courses_from_csv(filepath: str) -> Set[str]:
    """Extract CCC course codes from filtered CSV."""
    courses = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'CC_Course' in row and row['CC_Course']:
                    courses.add(row['CC_Course'].strip())
    except FileNotFoundError:
        print(f"Warning: {filepath} not found")
    return courses

def parse_results_csv(filepath: str) -> List[Tuple[str, str]]:
    """Parse results CSV to get UC->CC course mappings."""
    articulations = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                uc_course = row.get('UC_Course', '').strip()
                cc_course = row.get('CC_Course', '').strip()
                if uc_course and cc_course:
                    articulations.append((uc_course, cc_course))
    except FileNotFoundError:
        print(f"Warning: {filepath} not found")
    return articulations

def create_comprehensive_ge_tag_map() -> Dict[str, List[str]]:
    """
    Create comprehensive GE tag mapping based on UC requirements and IGETC.
    Returns dict mapping keywords to applicable GE tags.
    """
    return {
        # English Composition - IGETC 1A/1B, UC 7-Course Pattern
        "composition": ["IGETC-1A", "GE-A", "7CP-English"],
        "english composition": ["IGETC-1A", "GE-A", "7CP-English"],
        "writing": ["IGETC-1A", "GE-A", "7CP-English"],
        "rhetoric": ["IGETC-1A", "GE-A", "7CP-English"],
        "critical thinking": ["IGETC-1B", "GE-A", "7CP-English"],
        "reading and composition": ["IGETC-1A", "GE-A", "7CP-English"],
        "academic writing": ["IGETC-1A", "GE-A", "7CP-English"],
        
        # Mathematics - IGETC 2, UC GE B4, 7-Course Pattern
        "calculus": ["IGETC-2", "GE-B4", "7CP-Math", "Major Prep"],
        "precalculus": ["IGETC-2", "GE-B4", "7CP-Math"],
        "algebra": ["IGETC-2", "GE-B4", "7CP-Math"],
        "trigonometry": ["IGETC-2", "GE-B4", "7CP-Math"],
        "statistics": ["IGETC-2", "GE-B4", "7CP-Math"],
        "finite mathematics": ["IGETC-2", "GE-B4", "7CP-Math"],
        "mathematical concepts": ["IGETC-2", "GE-B4", "7CP-Math"],
        "quantitative reasoning": ["IGETC-2", "GE-B4", "7CP-Math"],
        "linear algebra": ["IGETC-2", "GE-B4", "7CP-Math", "Major Prep"],
        "differential equations": ["IGETC-2", "GE-B4", "7CP-Math", "Major Prep"],
        "discrete math": ["IGETC-2", "GE-B4", "7CP-Math", "Major Prep"],
        "vector analysis": ["IGETC-2", "GE-B4", "7CP-Math", "Major Prep"],
        
        # Arts and Humanities - IGETC 3A/3B, UC GE C1/C2, 7-Course Pattern
        "art history": ["IGETC-3A", "GE-C1", "7CP-AH"],
        "music": ["IGETC-3A", "GE-C1", "7CP-AH"],
        "theater": ["IGETC-3A", "GE-C1", "7CP-AH"],
        "philosophy": ["IGETC-3B", "GE-C2", "7CP-AH"],
        "literature": ["IGETC-3B", "GE-C2", "7CP-AH"],
        "history": ["IGETC-3B", "GE-C2", "7CP-AH"],
        "foreign language": ["IGETC-6", "GE-C2", "7CP-AH"],
        "humanities": ["IGETC-3B", "GE-C2", "7CP-AH"],
        "comparative literature": ["IGETC-3B", "GE-C2", "7CP-AH"],
        "religious studies": ["IGETC-3B", "GE-C2", "7CP-AH"],
        "cultural studies": ["IGETC-3B", "GE-C2", "7CP-AH"],
        
        # Social and Behavioral Sciences - IGETC 4, UC GE D, 7-Course Pattern
        "psychology": ["IGETC-4", "GE-D", "7CP-SBS"],
        "sociology": ["IGETC-4", "GE-D", "7CP-SBS"],
        "anthropology": ["IGETC-4", "GE-D", "7CP-SBS"],
        "economics": ["IGETC-4", "GE-D", "7CP-SBS"],
        "political science": ["IGETC-4", "GE-D", "7CP-SBS"],
        "geography": ["IGETC-4", "GE-D", "7CP-SBS"],
        "ethnic studies": ["IGETC-7", "GE-D", "7CP-SBS"],
        "women's studies": ["IGETC-4", "GE-D", "7CP-SBS"],
        "gender studies": ["IGETC-4", "GE-D", "7CP-SBS"],
        "social science": ["IGETC-4", "GE-D", "7CP-SBS"],
        "criminology": ["IGETC-4", "GE-D", "7CP-SBS"],
        
        # Physical and Biological Sciences - IGETC 5A/5B/5C, UC GE B1/B2/B3, 7-Course Pattern
        "physics": ["IGETC-5A", "GE-B1", "7CP-PBS", "Major Prep"],
        "chemistry": ["IGETC-5A", "GE-B1", "7CP-PBS"],
        "biology": ["IGETC-5B", "GE-B2", "7CP-PBS"],
        "geology": ["IGETC-5A", "GE-B1", "7CP-PBS"],
        "astronomy": ["IGETC-5A", "GE-B1", "7CP-PBS"],
        "environmental science": ["IGETC-5A", "GE-B1", "7CP-PBS"],
        "general chemistry": ["IGETC-5A", "GE-B1", "7CP-PBS"],
        "organic chemistry": ["IGETC-5A", "GE-B1", "7CP-PBS"],
        "microbiology": ["IGETC-5B", "GE-B2", "7CP-PBS"],
        "anatomy": ["IGETC-5B", "GE-B2", "7CP-PBS"],
        "physiology": ["IGETC-5B", "GE-B2", "7CP-PBS"],
        "marine biology": ["IGETC-5B", "GE-B2", "7CP-PBS"],
        "lab": ["IGETC-5C", "GE-B3"],  # Lab component
        "laboratory": ["IGETC-5C", "GE-B3"],
        
        # Computer Science Major Prep Keywords
        "programming": ["Major Prep"],
        "computer science": ["Major Prep"],
        "data structures": ["Major Prep"],
        "algorithms": ["Major Prep"],
        "computer organization": ["Major Prep"],
        "machine organization": ["Major Prep"],
        "assembly language": ["Major Prep"],
        "software engineering": ["Major Prep"],
        "object-oriented": ["Major Prep"],
        "c++": ["Major Prep"],
        "java": ["Major Prep"],
        "python": ["Major Prep"],
        "discrete structures": ["Major Prep"],
        "boolean logic": ["Major Prep"],
        "logic design": ["Major Prep"],
        "digital systems": ["Major Prep"],
        "computer systems": ["Major Prep"],
        "software construction": ["Major Prep"],
        "software tools": ["Major Prep"],
        "system design": ["Major Prep"],
        
        # Language Other Than English - IGETC 6
        "spanish": ["IGETC-6"],
        "french": ["IGETC-6"],
        "german": ["IGETC-6"],
        "italian": ["IGETC-6"],
        "chinese": ["IGETC-6"],
        "japanese": ["IGETC-6"],
        "korean": ["IGETC-6"],
        "arabic": ["IGETC-6"],
        "american sign language": ["IGETC-6"],
        "asl": ["IGETC-6"],
    }

def apply_ge_tags(course_name: str, course_code: str, tag_map: Dict[str, List[str]]) -> List[str]:
    """Apply GE tags based on course name and code using keyword matching."""
    tags = []
    search_text = f"{course_name} {course_code}".lower()
    
    # Apply tags based on keyword matches
    for keyword, applicable_tags in tag_map.items():
        if keyword in search_text:
            for tag in applicable_tags:
                if tag not in tags:
                    tags.append(tag)
    
    # Special handling for lab courses
    if re.search(r'\b(lab|laboratory)\b', search_text, re.IGNORECASE):
        if "IGETC-5C" not in tags:
            tags.append("IGETC-5C")
        if "GE-B3" not in tags:
            tags.append("GE-B3")
    
    # Special handling for ethnic studies requirement
    if re.search(r'\b(ethnic|multicultural|diversity)\b', search_text, re.IGNORECASE):
        if "IGETC-7" not in tags:
            tags.append("IGETC-7")
    
    return tags

def identify_major_prep_courses(course_name: str, course_code: str) -> bool:
    """
    Identify if a course is likely major prep based on comprehensive UC CS requirements.
    Based on the detailed requirements from all UC campuses.
    """
    search_text = f"{course_name} {course_code}".lower()
    
    # Core CS concepts
    cs_keywords = [
        "programming", "computer science", "data structures", "algorithms",
        "object-oriented", "software", "c++", "java", "python", "discrete",
        "boolean", "logic design", "computer organization", "assembly",
        "machine organization", "system programming", "software construction"
    ]
    
    # Mathematics for CS
    math_keywords = [
        "calculus", "linear algebra", "differential equations", "discrete math",
        "vector analysis", "multivariable calculus", "vector calculus"
    ]
    
    # Physics for engineering programs
    physics_keywords = [
        "physics for scientists", "mechanics", "electricity", "magnetism",
        "electrodynamics", "classical physics"
    ]
    
    # Check for CS keywords
    for keyword in cs_keywords:
        if keyword in search_text:
            return True
    
    # Check for math keywords (higher level math)
    for keyword in math_keywords:
        if keyword in search_text:
            return True
    
    # Check for physics keywords
    for keyword in physics_keywords:
        if keyword in search_text:
            return True
    
    # Course code patterns that indicate major prep
    if re.search(r'\b(cs|cis|cse|compsci|math|phys)\s*\d', course_code.lower()):
        # Additional validation for math - exclude basic math
        if 'math' in course_code.lower():
            if re.search(r'\b(basic|fundamental|elementary|developmental)\b', search_text):
                return False
            # Look for calc, linear algebra, etc.
            if any(kw in search_text for kw in ['calculus', 'linear', 'differential', 'discrete', 'vector']):
                return True
        else:
            return True
    
    return False

def process_ccc(ccc_name: str) -> None:
    """Process a single CCC and generate its course tags file."""
    print(f"Processing {ccc_name}...")
    
    # File paths - match your existing directory structure
    prereq_path = f"prerequisites/{ccc_name.lower().replace('_', '_')}_prereqs.json"
    filtered_csv = f"filtered_results/{ccc_name}_filtered.csv"
    results_csv = f"results/{ccc_name}_allUC.csv"
    output_path = f"course_tags/{ccc_name.lower().replace('_', '_')}_tags.json"
    
    # Load supporting data
    uc_course_names = load_json("uc_course_names.json")
    ge_tag_map = create_comprehensive_ge_tag_map()
    
    # Initialize course info from prereqs
    course_info = {}
    prereq_courses = load_json(prereq_path)
    
    if isinstance(prereq_courses, list):
        for course in prereq_courses:
            if isinstance(course, dict) and 'courseCode' in course:
                course_code = course['courseCode']
                course_info[course_code] = {
                    "courseName": course.get('courseName', 'UNKNOWN'),
                    "units": course.get('units', 0),
                    "tags": []
                }
    
    # Tag Major Prep courses from filtered results
    major_courses = extract_cc_courses_from_csv(filtered_csv)
    for cc_course in major_courses:
        if cc_course not in course_info:
            course_info[cc_course] = {
                "courseName": "UNKNOWN",
                "units": 0,
                "tags": []
            }
        if "Major Prep" not in course_info[cc_course]["tags"]:
            course_info[cc_course]["tags"].append("Major Prep")
    
    # Add courses from full articulation results with UC name fallback
    articulations = parse_results_csv(results_csv)
    for uc_course, cc_course in articulations:
        if cc_course not in course_info:
            uc_name = uc_course_names.get(uc_course, None)
            inferred_name = f"[from UC match] {uc_name}" if uc_name else "UNKNOWN"
            course_info[cc_course] = {
                "courseName": inferred_name,
                "units": 0,
                "tags": [],
                "inferredName": True
            }
    
    # Apply GE tags and additional major prep detection
    for course_code, course_data in course_info.items():
        course_name = course_data["courseName"]
        
        # Apply GE tags
        ge_tags = apply_ge_tags(course_name, course_code, ge_tag_map)
        for tag in ge_tags:
            if tag not in course_data["tags"]:
                course_data["tags"].append(tag)
        
        # Additional major prep detection for courses not already tagged
        if "Major Prep" not in course_data["tags"]:
            if identify_major_prep_courses(course_name, course_code):
                course_data["tags"].append("Major Prep")
    
    # Sort tags for consistency
    for course_data in course_info.values():
        course_data["tags"].sort()
    
    # Write output
    write_json(output_path, course_info)
    print(f"✓ Generated {output_path} with {len(course_info)} courses")

def main():
    """Main function to process all selected CCCs."""
    print("🏷️  UC CS Transfer Course Tagger")
    print("=" * 50)
    
    # Ensure output directory exists
    os.makedirs("course_tags", exist_ok=True)
    
    # Process each CCC
    for ccc in SELECTED_CCCS:
        try:
            process_ccc(ccc)
        except Exception as e:
            print(f"❌ Error processing {ccc}: {e}")
    
    print("\n✅ Course tagging complete!")
    print(f"Generated tags for {len(SELECTED_CCCS)} CCCs")
    print("📁 Output files saved to course_tags/ directory")

if __name__ == "__main__":
    main()