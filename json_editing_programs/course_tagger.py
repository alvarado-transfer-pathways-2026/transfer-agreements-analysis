import json
import sys
import re
from typing import List, Dict, Set

# Keyword → list of tags
KEYWORD_TAG_MAP = {
    "Calculus": ["Major Prep", "IG_2", "GE_QuantReason"],
    "Discrete": ["Major Prep"],
    "Data Structures": ["Major Prep"],
    "Linear Algebra": ["Major Prep"],
    "Differential Equations": ["Major Prep"],
    "Computer Architecture": ["Major Prep"],
    "Composition": ["IG_1A", "GE_WrittenComm"],
    "Critical Thinking": ["IG_1B", "GE_WrittenComm"],
    "Speech": ["IG_1C", "GE_WrittenComm"],
    "Statistics": ["IG_2", "GE_QuantReason"],
    "Art": ["IG_3A", "GE_ArtsHum"],
    "Music": ["IG_3A", "GE_ArtsHum"],
    "Philosophy": ["IG_3B", "GE_ArtsHum"],
    "History": ["IG_4", "GE_SocBeh"],
    "Psychology": ["IG_4", "GE_SocBeh"],
    "Sociology": ["IG_4", "GE_SocBeh"],
    "Political Science": ["IG_4", "GE_SocBeh"],
    "Physics": ["IG_Physical", "IG_5", "GE_PhyBio"],
    "Biology": ["IG_Biological", "IG_5", "GE_PhyBio"],
    "Chemistry": ["IG_Physical", "IG_5", "GE_PhyBio"],
    "Lab": ["IG_Lab"],
    "Ethnic": ["IG_7"],
    "Spanish": ["IG_6"],
    "French": ["IG_6"],
    "Japanese": ["IG_6"],
    "German": ["IG_6"]
}

def extract_valid_ge_tags(ge_json_path: str) -> Set[str]:
    with open(ge_json_path, "r") as f:
        ge_data = json.load(f)

    tags = set()

    def collect_reqs(req_list):
        for req in req_list:
            tags.add(req["reqId"])
            if "subRequirements" in req:
                collect_reqs(req["subRequirements"])

    for pattern in ge_data["requirementPatterns"]:
        collect_reqs(pattern["requirements"])

    return tags

def infer_tags(course_name: str, keyword_map: Dict[str, List[str]], valid_ge_tags: Set[str]) -> List[str]:
    tags = set()
    for keyword, tag_list in keyword_map.items():
        if re.search(rf"\b{re.escape(keyword)}\b", course_name, re.IGNORECASE):
            for tag in tag_list:
                if tag == "Major Prep" or tag in valid_ge_tags:
                    tags.add(tag)
    return list(tags)

def tag_courses(input_file: str, output_file: str, ge_json_path: str):
    valid_ge_tags = extract_valid_ge_tags(ge_json_path)

    with open(input_file, "r", encoding="utf-8") as f:
        courses = json.load(f)

    for course in courses:
        name = course.get("courseName", "")
        tags = infer_tags(name, KEYWORD_TAG_MAP, valid_ge_tags)
        course["tags"] = tags

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(courses, f, indent=2)

    print(f"✅ Tagged {len(courses)} courses → {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python course_tagger.py <input_courses.json> <output_courses.json> <ge_reqs.json>")
        sys.exit(1)

    input_json = sys.argv[1]
    output_json = sys.argv[2]
    ge_reqs_json = sys.argv[3]

    tag_courses(input_json, output_json, ge_reqs_json)
