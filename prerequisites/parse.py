import json

def format_list(items, join_word="and"):
    """Format a list with natural language (Oxford comma style)."""
    if len(items) == 1:
        return items[0]
    elif len(items) == 2:
        return f"{items[0]} {join_word} {items[1]}"
    else:
        return ", ".join(items[:-1]) + f", {join_word} {items[-1]}"

def format_list(items, join_word="and"):
    """Oxford‑comma formatter for a list of strings."""
    # drop any falsy entries
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {join_word} {items[1]}"
    return ", ".join(items[:-1]) + f", {join_word} {items[-1]}"

def prereq_to_english(prereq):
    """Convert structured AND/OR prerequisite JSON into human‑readable English."""
    # 1) Empty or None
    if not prereq:
        return "None"
    # 2) Explicit “Not Articulated”
    if prereq == "Not Articulated":
        return "Not articulated"
    # 3) Simple string
    if isinstance(prereq, str):
        return prereq
    # 4) Flat list → AND
    if isinstance(prereq, list):
        return format_list(prereq, "and")

    # 5) Top‑level OR (flatten nested ORs)
    if isinstance(prereq, dict) and "or" in prereq:
        flat_opts = []
        for opt in prereq["or"]:
            if isinstance(opt, dict) and "or" in opt:
                flat_opts.extend(opt["or"])
            else:
                flat_opts.append(opt)
        return format_list(flat_opts, "or")

    # 6) Top‑level AND (with nested OR/AND)
    if isinstance(prereq, dict) and "and" in prereq:
        parts = []
        for item in prereq["and"]:
            # OR group inside AND
            if isinstance(item, dict) and "or" in item:
                # flatten nested ORs here too
                or_opts = []
                for opt in item["or"]:
                    if isinstance(opt, dict) and "or" in opt:
                        or_opts.extend(opt["or"])
                    elif isinstance(opt, dict) and "and" in opt:
                        # nested AND inside OR → parentheses
                        and_group = format_list(opt["and"], "and")
                        or_opts.append(f"({and_group})")
                    else:
                        or_opts.append(opt)
                parts.append(format_list(or_opts, "or"))
            # AND group inside AND (rare)
            elif isinstance(item, dict) and "and" in item:
                parts.append(f"({format_list(item['and'], 'and')})")
            else:
                parts.append(item)
        return format_list(parts, "and")

    # 7) Fallback
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
    parse_prereq_file("prerequisites/miracosta_prereqs.json")
    
    
