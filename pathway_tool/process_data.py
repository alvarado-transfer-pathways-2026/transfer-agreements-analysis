import os
import pandas as pd
import json
import re
from collections import defaultdict

# --- CONFIGURATION ---
# This script is designed to be run from the root of the project directory.
# Example: python pathway_tool/process_data.py

# Input directory
RAW_DATA_DIR = 'results/'

# Output files that will be created in the project's root directory
MASTER_ARTICULATION_OUTPUT_FILE = 'master_articulation_data.json'
COURSE_METADATA_OUTPUT_FILE = 'course_metadata.json'

# --- EMBEDDED UC REQUIREMENT MAPPING ---
# The uc_names_standardized.json content is now a Python dictionary here.
uc_name_map = {
  "UCB": {
    "REQUIRED_CORE": {
      "MATH 1A": "CALCULUS_1", "MATH 1B": "CALCULUS_2", "MATH 53": "CALCULUS_3_MULTI",
      "MATH 54": "LINALG_DIFFEQ_COMBINED", "PHYSICS 7A": "PHYSICS_1_MECHANICS",
      "PHYSICS 7B": "PHYSICS_2_EM", "ENGLISH R1A": "ENGLISH_COMP_1", "ENGLISH R1B": "ENGLISH_COMP_2"
    },
    "CHOOSE_ONE_FROM": [
      {
        "group_name": "Natural Science Elective",
        "courses": {
          "ASTRON 7A": "SCIENCE_ELECTIVE_ASTRON_1", "ASTRON 7B": "SCIENCE_ELECTIVE_ASTRON_2",
          "BIOLOGY 1A": "SCIENCE_ELECTIVE_BIO_1", "BIOLOGY 1AL": "SCIENCE_ELECTIVE_BIO_1_LAB",
          "BIOLOGY 1B": "SCIENCE_ELECTIVE_BIO_2", "CHEM 1A": "SCIENCE_ELECTIVE_CHEM_1",
          "CHEM 1AL": "SCIENCE_ELECTIVE_CHEM_1_LAB", "CHEM 1B": "SCIENCE_ELECTIVE_CHEM_2",
          "CHEM 3A": "SCIENCE_ELECTIVE_CHEM_ORGANIC_1", "CHEM 3AL": "SCIENCE_ELECTIVE_CHEM_ORGANIC_1_LAB",
          "CHEM 3B": "SCIENCE_ELECTIVE_CHEM_ORGANIC_2", "CHEM 3BL": "SCIENCE_ELECTIVE_CHEM_ORGANIC_2_LAB",
          "MCELLBI 32": "SCIENCE_ELECTIVE_MCELLBI", "MCELLBI 32L": "SCIENCE_ELECTIVE_MCELLBI_LAB",
          "PHYSICS 7C": "PHYSICS_3_WAVES_THERMO"
        }
      }
    ],
    "RECOMMENDED": {
      "COMPSCI 61A": "INTRO_CS_ADV_A", "COMPSCI 61B": "DATA_STRUCTURES_ADV",
      "COMPSCI 61C": "ASSEMBLY_LANGUAGE_ADV", "COMPSCI 70": "DISCRETE_MATH_ADV",
      "EECS 16A": "LINEAR_ALGEBRA_EECS", "EECS 16B": "DIFFERENTIAL_EQUATIONS_EECS"
    }
  },
  "UCD": {
    "REQUIRED_CORE": {
      "ECS 020": "DISCRETE_MATH", "ECS 036A": "INTRO_CS_1", "ECS 036B": "INTRO_CS_2_OOP",
      "ECS 036C": "DATA_STRUCTURES", "ECS 050": "ASSEMBLY_LANGUAGE", "MAT 021A": "CALCULUS_1",
      "MAT 021B": "CALCULUS_2", "MAT 021C": "CALCULUS_3_MULTI", "MAT 021D": "CALCULUS_4_VECTOR"
    },
    "CHOOSE_ONE_FROM": [
      {
        "group_name": "Linear Algebra",
        "courses": {
          "MAT 022A": "LINEAR_ALGEBRA", "MAT 027A": "LINEAR_ALGEBRA_BIO_APP",
          "MAT 067": "LINEAR_ALGEBRA_MODERN"
        }
      }
    ],
    "CHOOSE_SERIES_FROM": [
       {
        "group_name": "Science Electives (3 Courses)",
        "series_options": {
          "Biology Series": {
            "BIS 002A": "SCIENCE_ELECTIVE_BIO_1", "BIS 002B": "SCIENCE_ELECTIVE_BIO_2",
            "BIS 002C": "SCIENCE_ELECTIVE_BIO_3"
          },
          "Chemistry Series": {
            "CHE 002A": "SCIENCE_ELECTIVE_CHEM_1", "CHE 002B": "SCIENCE_ELECTIVE_CHEM_2",
            "CHE 002C": "SCIENCE_ELECTIVE_CHEM_3"
          },
          "Physics Series": {
            "PHY 009A": "PHYSICS_1_MECHANICS", "PHY 009B": "PHYSICS_2_EM",
            "PHY 009C": "PHYSICS_3_WAVES_THERMO"
          }
        }
      }
    ]
  },
  "UCI": {
    "REQUIRED_CORE": {
      "I&C SCI 31": "INTRO_CS_1", "I&C SCI 32": "INTRO_CS_2_LIBRARIES",
      "I&C SCI 33": "INTRO_CS_3_INTERMEDIATE", "MATH 2A": "CALCULUS_1", "MATH 2B": "CALCULUS_2"
    },
    "CHOOSE_ONE_FROM": [
        {
            "group_name": "Additional Approved Course",
            "courses": {
                "MATH 3A": "LINEAR_ALGEBRA", "I&C SCI 6N": "LINEAR_ALGEBRA_COMPUTATIONAL",
                "I&C SCI 6B": "BOOLEAN_ALGEBRA", "I&C SCI 6D": "DISCRETE_MATH",
                "I&C SCI 45C": "PROGRAMMING_IN_C", "I&C SCI 46": "DATA_STRUCTURES_IMPLEMENTATION",
                "I&C SCI 51": "ASSEMBLY_LANGUAGE", "I&C SCI 53": "SYSTEM_DESIGN",
                "IN4MATX 43": "SOFTWARE_ENGINEERING", "STATS 67": "PROBABILITY_STATS"
            }
        }
    ]
  },
  "UCLA": {
    "REQUIRED_CORE": {
      "COM SCI 31": "INTRO_CS_1", "COM SCI 32": "INTRO_CS_2_OOP", "COM SCI 33": "ASSEMBLY_LANGUAGE",
      "COM SCI 35L": "SOFTWARE_ENGINEERING_LAB", "MATH 31A": "CALCULUS_1", "MATH 31B": "CALCULUS_2",
      "MATH 32A": "CALCULUS_3_MULTI", "MATH 32B": "CALCULUS_4_VECTOR", "MATH 33A": "LINEAR_ALGEBRA",
      "MATH 33B": "DIFFERENTIAL_EQUATIONS", "MATH 61": "DISCRETE_MATH", "PHYSICS 1A": "PHYSICS_1_MECHANICS",
      "PHYSICS 1B": "PHYSICS_2_EM", "PHYSICS 1C": "PHYSICS_3_WAVES_THERMO", "ENGCOMP 3": "ENGLISH_COMP_1"
    },
    "CHOOSE_ONE_FROM": [
      {
        "group_name": "Logic Design",
        "courses": { "COM SCI M51A": "LOGIC_DESIGN", "EC ENGR M16": "LOGIC_DESIGN" }
      },
      {
        "group_name": "Physics Lab",
        "courses": { "PHYSICS 4AL": "PHYSICS_LAB_MECHANICS", "PHYSICS 4BL": "PHYSICS_LAB_EM" }
      }
    ],
    "CHOOSE_ONE_FROM_GROUP": {
        "group_name": "Second English Composition", "courses": {}
    }
  },
  "UCM": {
    "REQUIRED_CORE": {
      "CSE 022": "INTRO_CS_1", "CSE 030": "DATA_STRUCTURES", "MATH 021": "CALCULUS_1",
      "MATH 022": "CALCULUS_2", "MATH 023": "CALCULUS_3_VECTOR", "MATH 024": "LINALG_DIFFEQ_COMBINED",
      "PHYS 008": "PHYSICS_1_MECHANICS", "PHYS 008L": "PHYSICS_1_LAB", "PHYS 009": "PHYSICS_2_EM",
      "PHYS 009L": "PHYSICS_2_LAB", "WRI 001": "ENGLISH_COMP_1", "WRI 010": "ENGLISH_COMP_2"
    },
    "RECOMMENDED": {
      "CSE 015": "DISCRETE_MATH", "CSE 024": "INTRO_CS_2_ADVANCED", "CSE 031": "ASSEMBLY_LANGUAGE",
      "ENGR 065": "CIRCUIT_THEORY", "MATH 032": "PROBABILITY_STATS"
    }
  },
  "UCR": {
    "REQUIRED_CORE": {
      "CS 10A": "INTRO_CS_1", "CS 10B": "INTRO_CS_2_OOP", "MATH 9A": "CALCULUS_1",
      "MATH 9B": "CALCULUS_2", "MATH 9C": "CALCULUS_3_MULTI", "PHYS 40A": "PHYSICS_1_MECHANICS"
    },
    "CHOOSE_THREE_FROM": [
      {
        "group_name": "Additional Electives",
        "courses": {
          "CS 11": "DISCRETE_MATH", "CS 10C": "DATA_STRUCTURES", "CS 61": "ASSEMBLY_LANGUAGE",
          "MATH 10A": "CALCULUS_3_MULTI", "PHYS 40B": "PHYSICS_2_EM", "PHYS 40C": "PHYSICS_3_WAVES_THERMO"
        }
      }
    ],
    "RECOMMENDED": { "MATH 31": "LINEAR_ALGEBRA" }
  },
  "UCSD": {
    "REQUIRED_CORE": {
      "CSE 12": "DATA_STRUCTURES", "CSE 15L": "SOFTWARE_TOOLS_LAB", "CSE 20": "DISCRETE_MATH",
      "CSE 21": "MATH_FOR_ALGORITHMS", "CSE 30": "ASSEMBLY_LANGUAGE", "MATH 18": "LINEAR_ALGEBRA",
      "MATH 20A": "CALCULUS_1", "MATH 20B": "CALCULUS_2", "MATH 20C": "CALCULUS_3_MULTI"
    },
    "CHOOSE_ONE_FROM": [
      {
        "group_name": "Programming Sequence",
        "courses": {
          "CSE 8A": "INTRO_CS_1A", "CSE 8B": "INTRO_CS_1B", "CSE 11": "INTRO_CS_1_ACCELERATED"
        }
      }
    ],
    "CHOOSE_TWO_FROM": [
      {
        "group_name": "Science Electives",
        "courses": {
          "BILD 1": "SCIENCE_ELECTIVE_BIO_1", "BILD 2": "SCIENCE_ELECTIVE_BIO_2",
          "BILD 3": "SCIENCE_ELECTIVE_BIO_3", "CHEM 6A": "SCIENCE_ELECTIVE_CHEM_1",
          "CHEM 6B": "SCIENCE_ELECTIVE_CHEM_2", "PHYS 2A": "PHYSICS_1_MECHANICS",
          "PHYS 2B": "PHYSICS_2_EM", "PHYS 4A": "PHYSICS_1_MECHANICS_MAJORS",
          "PHYS 4B": "PHYSICS_2_THERMO_MAJORS"
        }
      }
    ]
  },
  "UCSB": {
    "REQUIRED_CORE": {
      "MATH 3A": "CALCULUS_1", "MATH 3B": "CALCULUS_2", "MATH 4A": "LINEAR_ALGEBRA",
      "MATH 4B": "DIFFERENTIAL_EQUATIONS", "CMPSC 16": "INTRO_CS_1", "CMPSC 24": "DATA_STRUCTURES",
      "CMPSC 40": "DISCRETE_MATH"
    },
    "RECOMMENDED": {
      "CMPSC 32": "OBJECT_ORIENTED_DESIGN", "CMPSC 64": "ASSEMBLY_LANGUAGE",
      "MATH 6A": "CALCULUS_3_VECTOR"
    },
    "RECOMMENDED_CHOOSE_UNITS": [
        {
            "group_name": "Science Electives (8 units)",
            "courses": {
                "PHYS 1": "PHYSICS_1_MECHANICS_ALGEBRA", "PHYS 2": "PHYSICS_2_EM_ALGEBRA",
                "PHYS 3": "PHYSICS_3_WAVES_THERMO_ALGEBRA", "PHYS 3L": "PHYSICS_LAB",
                "CHEM 1A": "SCIENCE_ELECTIVE_CHEM_1", "CHEM 1AL": "SCIENCE_ELECTIVE_CHEM_1_LAB",
                "CHEM 1B": "SCIENCE_ELECTIVE_CHEM_2", "CHEM 1BL": "SCIENCE_ELECTIVE_CHEM_2_LAB",
                "CHEM 1C": "SCIENCE_ELECTIVE_CHEM_3", "CHEM 1CL": "SCIENCE_ELECTIVE_CHEM_3_LAB",
                "MCDB 1A": "SCIENCE_ELECTIVE_BIO_1", "MCDB 1LL": "SCIENCE_ELECTIVE_BIO_1_LAB",
                "MCDB 1B": "SCIENCE_ELECTIVE_BIO_2"
            }
        }
    ]
  },
  "UCSC": {
    "REQUIRED_CORE": {
      "CSE 12": "ASSEMBLY_LANGUAGE_AND_SYSTEMS", "CSE 16": "DISCRETE_MATH",
      "CSE 30": "INTRO_CS_1_PYTHON", "MATH 19A": "CALCULUS_1", "MATH 19B": "CALCULUS_2"
    },
    "RECOMMENDED_CHOOSE_ONE_FROM": [
      {
        "group_name": "Linear Algebra",
        "courses": { "AM 10": "LINEAR_ALGEBRA", "MATH 21": "LINEAR_ALGEBRA" }
      },
      {
        "group_name": "Multivariable Calculus",
        "courses": { "AM 30": "CALCULUS_3_MULTI", "MATH 23A": "CALCULUS_3_VECTOR" }
      }
    ]
  }
}

# --- HELPER FUNCTIONS ---

def find_standard_name(uc_name, uc_course, uc_name_map):
    """
    Searches the nested uc_name_map to find the standard name for a given UC course.
    Returns the standard name or None if not found.
    """
    uc_abbr_map = {
        "University of California Berkeley": "UCB", "University of California Davis": "UCD",
        "University of California Irvine": "UCI", "University of California Los Angeles": "UCLA",
        "University of California Merced": "UCM", "University of California Riverside": "UCR",
        "University of California San Diego": "UCSD", "University of California Santa Barbara": "UCSB",
        "University of California Santa Cruz": "UCSC"
    }
    uc_abbr = uc_abbr_map.get(uc_name)
    if not uc_abbr: return None

    if uc_abbr in uc_name_map:
        for req_type, content in uc_name_map[uc_abbr].items():
            if req_type in ["REQUIRED_CORE", "RECOMMENDED"]:
                if uc_course in content: return content[uc_course]
            elif req_type in ["CHOOSE_ONE_FROM", "CHOOSE_TWO_FROM", "CHOOSE_THREE_FROM", "RECOMMENDED_CHOOSE_UNITS", "RECOMMENDED_CHOOSE_ONE_FROM"]:
                for group in content:
                    if 'courses' in group and uc_course in group['courses']: return group['courses'][uc_course]
            elif req_type == "CHOOSE_SERIES_FROM":
                 for group in content:
                    for series_name, series_courses in group['series_options'].items():
                        if uc_course in series_courses: return series_courses[uc_course]
    return None

def parse_cc_course_string(course_string):
    """
    Parses a string like 'MATH 181 (4.00); MATH 182 (4.00)' into a list of course objects.
    """
    if pd.isna(course_string) or 'Not Articulated' in course_string: return []
    courses = []
    pattern = re.compile(r'([A-Z]+\s+[0-9A-Z]+)\s*\((\d+\.\d+)\)')
    matches = pattern.findall(course_string)
    for match in matches:
        course_id = match[0].strip()
        try:
            units = float(match[1])
            courses.append({'id': course_id, 'units': units})
        except ValueError:
            print(f"Warning: Could not parse units for '{match[0]}'")
    return courses

# --- MAIN SCRIPT LOGIC ---

print("--- Starting Data Processing Script ---")

master_articulation_data = []
course_metadata = {}

print(f"\n-> Reading raw data from '{RAW_DATA_DIR}'...")
for filename in os.listdir(RAW_DATA_DIR):
    if filename.endswith('_allUC.csv'):
        file_path = os.path.join(RAW_DATA_DIR, filename)
        try:
            df = pd.read_csv(file_path)
            for index, row in df.iterrows():
                uc_name_full = row['UC Campus'].strip()
                cc_name = row['CC'].strip()
                uc_courses_raw = str(row['UC Course Requirement']).strip()
                uc_courses = [c.strip() for c in uc_courses_raw.split(';') if c.strip()]
                all_articulated_cc_courses = []
                for col in df.columns:
                    if 'Courses Group' in col and pd.notna(row[col]):
                        parsed = parse_cc_course_string(str(row[col]))
                        if parsed: all_articulated_cc_courses.append(parsed)
                if not all_articulated_cc_courses: continue
                for uc_course in uc_courses:
                    standard_name = find_standard_name(uc_name_full, uc_course, uc_name_map)
                    if not standard_name: continue
                    master_articulation_data.append({
                        "ccc_name": cc_name,
                        "uc_name": uc_name_full.split(" ")[-1],
                        "uc_course": uc_course,
                        "standard_name": standard_name,
                        "ccc_courses_required": all_articulated_cc_courses
                    })
                    for course_group in all_articulated_cc_courses:
                        for course in course_group:
                            metadata_key = f"{cc_name}_{course['id']}"
                            if metadata_key not in course_metadata:
                                course_metadata[metadata_key] = {
                                    "course_id": course['id'],
                                    "ccc_name": cc_name,
                                    "units": course['units'],
                                    "fulfills_standard_names": []
                                }
                            if standard_name not in course_metadata[metadata_key]["fulfills_standard_names"]:
                                course_metadata[metadata_key]["fulfills_standard_names"].append(standard_name)
        except Exception as e:
            print(f"ERROR: Could not process {filename}: {e}")

print(f"\n-> Writing final output files...")
with open(MASTER_ARTICULATION_OUTPUT_FILE, 'w') as f:
    json.dump(master_articulation_data, f, indent=2)
print(f"✅ Wrote {len(master_articulation_data)} records to '{MASTER_ARTICULATION_OUTPUT_FILE}'")

with open(COURSE_METADATA_OUTPUT_FILE, 'w') as f:
    json.dump(course_metadata, f, indent=2, sort_keys=True)
print(f"✅ Wrote metadata for {len(course_metadata)} unique CC courses to '{COURSE_METADATA_OUTPUT_FILE}'")

print("\n--- Processing Complete ---")
