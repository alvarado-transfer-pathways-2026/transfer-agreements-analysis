import json
from typing import Dict, List, Set, Tuple

# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------

def load_prereq_data(json_path: str) -> Dict[str, dict]:
    """Load JSON prereq data from file -> dict keyed by courseCode."""
    with open(json_path, "r") as f:
        data = json.load(f)
    return {course["courseCode"]: course for course in data}

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def _dedupe_by_code(items: List[dict]) -> List[dict]:
    """Stable, first-wins dedupe by 'courseCode'."""
    seen: Set[str] = set()
    out: List[dict] = []
    for it in items:
        code = it.get("courseCode")
        if code and code not in seen:
            seen.add(code)
            out.append(it)
    return out

# -----------------------------------------------------------------------------
# Prereq satisfaction logic
# -----------------------------------------------------------------------------

def prereq_block_satisfied(block, completed_courses: Set[str]) -> bool:
    """
    Recursively check a structured prerequisite block against completed courses.
    Supported shapes:
      - str: leaf course code
      - {"and": [...]}: all must be satisfied
      - {"or":  [...]}: at least one must be satisfied
      - [] / None: trivially satisfied
    """
    # 1) Base case: plain string → membership
    if isinstance(block, str):
        return block in completed_courses

    # 2) Empty block → trivially satisfied
    if not block:
        return True

    # 3) AND group
    if isinstance(block, dict) and "and" in block:
        return all(prereq_block_satisfied(sub, completed_courses) for sub in block["and"])

    # 4) OR group
    if isinstance(block, dict) and "or" in block:
        return any(prereq_block_satisfied(sub, completed_courses) for sub in block["or"])

    # 5) Unknown -> not satisfied
    return False


def course_prereqs_satisfied(course: dict, completed_courses: Set[str]) -> bool:
    """
    Evaluate whether a course's prereqs are satisfied.
    Accepts either a minimal dict {"prerequisites": ...} or a full prereq record.

    List handling rule (legacy support):
      - If any item in the list contains ';', treat the list as AND-of-groups,
        and each group's parts (split by ';') are AND within the group.
      - Otherwise the list is a simple OR of course codes.
    """
    prereqs = course.get("prerequisites", None)
    if prereqs is None or prereqs == []:
        return True

    if isinstance(prereqs, dict):
        return prereq_block_satisfied(prereqs, completed_courses)

    if isinstance(prereqs, list):
        if any(isinstance(x, str) and ";" in x for x in prereqs):
            # AND: every group must be satisfied
            for and_group in prereqs:
                parts = [p.strip() for p in str(and_group).split(";")]
                if not all(part in completed_courses for part in parts):
                    return False
            return True
        else:
            # OR: at least one item present
            return any(str(item) in completed_courses for item in prereqs)

    # Unknown format → assume satisfied
    return True

# -----------------------------------------------------------------------------
# Missing prereq enumeration (for unlocker detection)
# -----------------------------------------------------------------------------

def _collect_missing_from_block(block, completed: Set[str]) -> Set[str]:
    """Return the set of *leaf* course codes still missing to satisfy `block`.

    Semantics:
      - For OR: if any option is already satisfied → nothing missing for that group
        (since the OR is satisfied). Otherwise, union of missing leaves from each option.
      - For AND: union of missing leaves across all parts.
    """
    missing: Set[str] = set()

    if isinstance(block, str):
        return set() if block in completed else {block}

    if not block:
        return set()

    if isinstance(block, dict) and "and" in block:
        for sub in block["and"]:
            missing |= _collect_missing_from_block(sub, completed)
        return missing

    if isinstance(block, dict) and "or" in block:
        # If ANY option satisfied → nothing missing for this OR
        if any(prereq_block_satisfied(opt, completed) for opt in block["or"]):
            return set()
        # otherwise union of missing for each option
        for opt in block["or"]:
            missing |= _collect_missing_from_block(opt, completed)
        return missing

    # Lists (legacy shapes): interpret per course_prereqs_satisfied rules
    if isinstance(block, list):
        if any(isinstance(x, str) and ";" in x for x in block):
            # AND-of-groups
            for and_group in block:
                parts = [p.strip() for p in str(and_group).split(";")]
                for p in parts:
                    if p not in completed:
                        missing.add(p)
            return missing
        else:
            # OR of plain strings
            if any(str(item) in completed for item in block):
                return set()
            return {str(item) for item in block if str(item) not in completed}

    return set()

# -----------------------------------------------------------------------------
# Candidate expansion & eligibility
# -----------------------------------------------------------------------------

def add_missing_prereqs(
    major_cands: List[dict],
    prereqs: Dict[str, dict],
    completed: Set[str] | None = None,
    default_units: int = 3,
    dedupe: bool = True,
) -> List[dict]:
    """
    Scan current major candidates and append any *direct* prerequisite courses that
    exist in `prereqs` but aren't completed or already in the queue.

    Keeps behavior compatible with the previous implementation, but adds an
    optional stable-dedupe pass to avoid repeated clones of the same course.
    """
    if completed is None:
        completed = set()

    existing = {c.get('courseCode') for c in major_cands}
    i = 0

    while i < len(major_cands):
        code = major_cands[i].get('courseCode')
        raw = prereqs.get(code, {}).get('prerequisites', [])

        # Normalize raw prereqs into a flat list of entries (strings or {"or": [...]})
        req_list = []
        if isinstance(raw, dict):
            req_list = raw.get('and', [])
        elif isinstance(raw, list):
            req_list = raw

        for entry in req_list:
            if isinstance(entry, dict) and 'or' in entry:
                candidates = entry['or']
            elif isinstance(entry, str):
                candidates = [entry]
            else:
                continue

            for pre in candidates:
                if pre in prereqs and pre not in existing and pre not in completed:
                    units = prereqs[pre].get('units', default_units)
                    major_cands.append({'courseCode': pre, 'units': units})
                    existing.add(pre)

        i += 1

    return _dedupe_by_code(major_cands) if dedupe else major_cands


def course_record(code: str, prereqs: Dict[str, dict], default_units: int = 3) -> dict:
    """Return a minimal course dict with code + units, looking up units in prereqs."""
    units = None
    if code in prereqs:
        units = prereqs[code].get('units') or prereqs[code].get('courseUnits')
    return {"courseCode": code, "units": units if units is not None else default_units}


def get_eligible_courses(
    completed_courses: Set[str],
    major_cands: List[dict],
    prereqs: Dict[str, dict],
    default_units: int = 3,
) -> List[dict]:
    """Return candidates whose prereqs are satisfied right now (stable-deduped)."""
    eligible: List[dict] = []
    for cand in major_cands:
        code = cand.get("courseCode")
        raw_pr = prereqs.get(code, {}).get("prerequisites", None)
        print(f"[ELIGIBILITY] Checking {code!r}: prereqs={raw_pr!r}, completed={sorted(completed_courses)}")

        if code in completed_courses:
            print(f"   → skip {code}: already completed")
            continue

        if course_prereqs_satisfied({"prerequisites": raw_pr}, completed_courses):
            print(f"   ✔ {code} is eligible")
            eligible.append(course_record(code, prereqs, default_units))
        else:
            print(f"   ✖ {code} blocked by prereqs")

    return _dedupe_by_code(eligible)

# -----------------------------------------------------------------------------
# Unlocker logic
# -----------------------------------------------------------------------------

def get_unlocker_courses(
    major_cands: List[dict],    
    completed: Set[str],
    prereqs: Dict[str, dict],
    *,
    min_unlocks: int = 1,
    max_count: int = 6,
    default_units: int = 3,
) -> List[dict]:
    """
    Identify *immediately-takeable* courses that would unlock other currently
    blocked major courses.

    Heuristic:
      1) Look at courses in `major_cands` that are BLOCKED right now.
      2) Enumerate their missing prereq *leaf* codes (respecting AND/OR semantics).
      3) Keep only those missing codes whose OWN prereqs are already satisfied
         (so we can take them this term).
      4) Tally how many blocked majors each such code would unlock.

    Returns a list of course dicts, sorted by descending unlock count, each with:
      {
        'courseCode': ..., 'units': ..., 'tag': 'UNLOCKER', 'unlocks': [blocked1, ...],
        'unlockCount': <int>
      }
    """
    # 1) Which major courses are blocked right now?
    blocked: List[Tuple[str, object]] = []  # (course_code, raw_prereq_block)
    for cand in major_cands:
        code = cand.get('courseCode')
        raw = prereqs.get(code, {}).get('prerequisites')
        if code in completed:
            continue
        if not course_prereqs_satisfied({"prerequisites": raw}, completed):
            blocked.append((code, raw))

    # 2) For each blocked course, list missing leaf prereqs
    unlock_count: Dict[str, int] = {}
    unlock_targets: Dict[str, Set[str]] = {}

    for blk_code, blk_raw in blocked:
        missing = _collect_missing_from_block(blk_raw, completed)
        for pre in missing:
            # Only consider *real* CC courses we know about
            if pre not in prereqs:
                continue
            # The unlocker must itself be takeable now
            if not course_prereqs_satisfied(prereqs[pre], completed):
                continue
            unlock_count[pre] = unlock_count.get(pre, 0) + 1
            unlock_targets.setdefault(pre, set()).add(blk_code)

    # 3) Build ranked unlockers
    ranked = sorted(
        ((code, cnt) for code, cnt in unlock_count.items() if cnt >= min_unlocks),
        key=lambda t: (-t[1], t[0])
    )

    out: List[dict] = []
    for code, cnt in ranked[:max_count]:
        rec = course_record(code, prereqs, default_units)
        rec.update({
            'tag': 'UNLOCKER',
            'unlocks': sorted(unlock_targets.get(code, set())),
            'unlockCount': cnt,
        })
        out.append(rec)

    return _dedupe_by_code(out)
