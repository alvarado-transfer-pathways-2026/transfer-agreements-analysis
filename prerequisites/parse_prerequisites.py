import json

def format_list(items, join_word="and"):
    """Oxford‑comma formatter for a list of strings."""
    # ensure everything is a string and drop empties
    strs = [str(i) for i in items if i]
    if not strs:
        return ""
    if len(strs) == 1:
        return strs[0]
    if len(strs) == 2:
        return f"{strs[0]} {join_word} {strs[1]}"
    return ", ".join(strs[:-1]) + f", {join_word} {strs[-1]}"

def prereq_to_english(prereq):
    """Recursively convert structured AND/OR prerequisite JSON into English."""
    # 1) Empty or None
    if not prereq:
        return "None"
    # 2) Literal
    if prereq == "Not Articulated":
        return "Not articulated"
    if isinstance(prereq, str):
        return prereq

    # 3) Flat list: assume AND between all elements
    if isinstance(prereq, list):
        parts = [prereq_to_english(item) for item in prereq]
        return format_list(parts, "and")

    # 4) Dict: check OR first
    if isinstance(prereq, dict) and "or" in prereq:
        # flatten any nested OR dicts
        opts = []
        for opt in prereq["or"]:
            if isinstance(opt, dict) and "or" in opt:
                opts.extend(opt["or"])
            else:
                opts.append(opt)
        # recursively render each option
        readable_opts = [prereq_to_english(opt) for opt in opts]
        return format_list(readable_opts, "or")

    # 5) Dict: then AND
    if isinstance(prereq, dict) and "and" in prereq:
        parts = []
        for item in prereq["and"]:
            parts.append(prereq_to_english(item))
        return format_list(parts, "and")

    # 6) Fallback
    return "Unknown format"



def parse_prereq_file(filename):
    with open(filename, "r") as f:
        courses = json.load(f)

    for course in courses:
        code = course.get("courseCode", "Unknown Code")
        name = course.get("courseName", "Unknown Course")
        units = course.get("units", "N/A")
        prereqs = prereq_to_english(course.get("prerequisites"))

        print(f"{code} ({units} units): {name}")
        print(f"  Prerequisites: {prereqs}")
        print()

if __name__ == "__main__":
    parse_prereq_file("prerequisites/cosumnes_river_college_prereqs.json")
    
    
