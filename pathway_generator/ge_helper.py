# ge_helper.py

import json
from pathlib import Path

def load_ge_lookup(ge_json_path="ge_reqs.json"):
    """
    Reads the GE requirements file and returns a dict mapping every reqId
    (including subRequirements) to its human-readable name.
    """
    ge_path = Path(ge_json_path)
    data = json.loads(ge_path.read_text())
    lookup = {}

    for pattern in data.get("requirementPatterns", []):
        for req in pattern.get("requirements", []):
            lookup[req["reqId"]] = req["name"]
            # flatten any subRequirements too
            for sub in req.get("subRequirements", []):
                lookup[sub["reqId"]] = sub["name"]

    return lookup


def build_ge_courses(ge_remaining, ge_lookup=None, unit_count=3):
    ge_lookup = ge_lookup or load_ge_lookup()
    ge_courses = []
    for reqId in ge_remaining:
        name = ge_lookup.get(reqId, reqId)
        ge_courses.append({
            'courseCode': reqId,          # ← ensure this exists
            'courseName': name,
            'reqIds':     [reqId],
            'units':      unit_count
        })
    return ge_courses
