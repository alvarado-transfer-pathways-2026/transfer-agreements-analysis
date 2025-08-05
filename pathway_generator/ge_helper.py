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
    """
    Given a list of reqId strings and a lookup dict, returns a list of
    GE-course dicts in the shape you need.

    ge_remaining: list of reqIds, e.g. ["GE_WrittenComm", "IG_1A", …]
    ge_lookup:    dict from load_ge_lookup()
    unit_count:   int, default 3 units per GE course
    """
    if ge_lookup is None:
        # fallback: load from default file path
        ge_lookup = load_ge_lookup()

    ge_courses = []
    for reqId in ge_remaining:
        name = ge_lookup.get(reqId, reqId)  # fallback to ID if missing
        ge_courses.append({
            "courseName": name,
            "reqIds":     [reqId],
            "units":      unit_count
        })
    return ge_courses
