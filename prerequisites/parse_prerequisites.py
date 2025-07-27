import json

def format_list(items, join_word="and"):
    """Format a list with natural language (Oxford comma style)."""
    if len(items) == 1:
        return items[0]
    elif len(items) == 2:
        return f"{items[0]} {join_word} {items[1]}"
    else:
        return ", ".join(items[:-1]) + f", {join_word} {items[-1]}"

def prereq_to_english(prereq):
    if prereq == "Not Articulated":
        return "Not articulated"
    if isinstance(prereq, str):
        return prereq

    # Handle AND at top level
    if isinstance(prereq, dict) and "and" in prereq:
        parts = []
        for item in prereq["and"]:
            # OR group inside AND
            if isinstance(item, dict) and "or" in item:
                or_parts = []
                for opt in item["or"]:
                    # nested AND inside OR
                    if isinstance(opt, dict) and "and" in opt:
                        and_group = " and ".join(opt["and"])
                        or_parts.append(f"({and_group})")
                    else:
                        or_parts.append(opt)
                parts.append(" or ".join(or_parts))
            else:
                parts.append(item)
        return " and ".join(parts)

    # Fallback
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
    parse_prereq_file("prerequisites/folsom_lake_prereqs.json")
    parse_prereq_file("prerequisites/foothill_college_prereqs.json")
    parse_prereq_file("prerequisites/orange_coast_college_prereqs.json")
    
