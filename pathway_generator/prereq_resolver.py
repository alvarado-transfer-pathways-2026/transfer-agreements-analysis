import json

def load_prereq_data(json_path):
    """Load JSON prereq data from file."""
    with open(json_path, "r") as f:
        data = json.load(f)
    # Convert list to dict keyed by courseCode for quick lookup
    return {course["courseCode"]: course for course in data}

def add_missing_prereqs(major_cands, prereqs, completed=None, default_units=3):
        if completed is None:
            completed = set()

        existing = {c['courseCode'] for c in major_cands}
        i = 0

        while i < len(major_cands):
            code = major_cands[i]['courseCode']
            raw = prereqs.get(code, {}).get('prerequisites', [])

            # 1) Normalize raw prereqs into a flat list of codes
            req_list = []
            if isinstance(raw, dict):
                # handle {"and": […]}
                req_list = raw.get('and', [])
            elif isinstance(raw, list):
                req_list = raw
            # now req_list may contain strings or {"or": […]} dicts

            # 2) Iterate through normalized list
            for entry in req_list:
                if isinstance(entry, dict) and 'or' in entry:
                    # pull in each option in the OR‐group
                    candidates = entry['or']
                elif isinstance(entry, str):
                    candidates = [entry]
                else:
                    # unexpected shape—skip
                    continue
                
                for pre in candidates:
                    # only add real CC codes we haven’t done or queued
                    if pre in prereqs and pre not in existing and pre not in completed:
                        units = prereqs[pre].get('units', default_units)
                        major_cands.append({
                            'courseCode': pre,
                            'units':      units
                        })
                        existing.add(pre)
    
            i += 1

        return major_cands

def prereq_block_satisfied(block, completed_courses):
    # 1) Base case: plain string → check membership
    if isinstance(block, str):
        return block in completed_courses

    # 2) Empty block (None or {}) → trivially satisfied
    if not block:
        return True

    # 3) "AND" group
    if isinstance(block, dict) and "and" in block:
        return all(prereq_block_satisfied(sub, completed_courses)
                   for sub in block["and"])

    # 4) "OR" group
    if isinstance(block, dict) and "or" in block:
        for item in block["or"]:
            if prereq_block_satisfied(item, completed_courses):
                return True
        return False

    # 5) Anything else → not satisfied
    return False

def course_prereqs_satisfied(course, completed_courses):
    prereqs = course.get("prerequisites", None)
    if prereqs is None or prereqs == []:
        return True

    # Handle block format
    if isinstance(prereqs, dict):
        return prereq_block_satisfied(prereqs, completed_courses)
    # Handle list format (new logic for OR and AND with semicolon)
    elif isinstance(prereqs, list):
        # If any item has ';' treat as AND, else OR
        if any(';' in item for item in prereqs):
            # AND: split each string by ';' and check all parts
            for and_group in prereqs:
                parts = [part.strip() for part in and_group.split(';')]
                if not all(part in completed_courses for part in parts):
                    return False
            return True
        else:
            # OR: at least one in completed_courses
            return any(item in completed_courses for item in prereqs)
    else:
        # Unknown format - assume no prereqs
        return True

def get_eligible_courses(completed_courses, major_cands, prereqs, default_units=3):
    eligible = []
    for cand in major_cands:
        code = cand["courseCode"]
        raw_pr = prereqs.get(code, {}).get("prerequisites", None)
        print(f"[ELIGIBILITY] Checking {code!r}: prereqs={raw_pr!r}, completed={sorted(completed_courses)}")

        if code in completed_courses:
            print(f"   → skip {code}: already completed")
            continue

        if course_prereqs_satisfied({"prerequisites": raw_pr}, completed_courses):
            print(f"   ✔ {code} is eligible")
            eligible.append({"courseCode": code, "units": cand.get("units", default_units)})
        else:
            print(f"   ✖ {code} blocked by prereqs")
    return eligible
