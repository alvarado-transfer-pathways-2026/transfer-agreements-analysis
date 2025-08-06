#This one prioritizes Major courses and then GE courses

# def select_courses_for_term(eligible_courses, completed_courses=None, fulfilled_ge_ids=None, max_units=20):
#     if completed_courses is None:
#         completed_courses = []
#     if fulfilled_ge_ids is None:
#         fulfilled_ge_ids = set()

#     # Filter out already completed courses
#     remaining_courses = [c for c in eligible_courses if c.get('courseCode') not in completed_courses]

#     # Helper to check if course is a GE
#     def is_ge(course):
#         return any(req.startswith('IG_') or req.startswith('GE_') for req in course.get('reqIds', []))

#     # Helper to check if GE course fulfills an unmet GE area
#     def fulfills_unmet_ge(course):
#         return any(req_id not in fulfilled_ge_ids for req_id in course.get('reqIds', []) if req_id.startswith('IG_') or req_id.startswith('GE_'))

#     # Split courses
#     ge_courses = [c for c in remaining_courses if is_ge(c) and fulfills_unmet_ge(c)]
#     major_courses = [c for c in remaining_courses if not is_ge(c)]  # Assume all others are majors

#     selected_courses = []
#     total_units = 0

#     # --- Step 1: Ensure at least one GE is selected (if any exist) ---
#     ge_added = False
#     for course in ge_courses:
#         if total_units + course['units'] <= max_units:
#             selected_courses.append(course)
#             total_units += course['units']
#             ge_added = True
#             break  # Only one GE guaranteed

#     # --- Step 2: Add as many major courses as fit ---
#     for course in major_courses:
#         if total_units + course['units'] <= max_units:
#             selected_courses.append(course)
#             total_units += course['units']

#     # --- Step 3: If space left and no majors remaining, add more GEs ---
#     if total_units < max_units:
#         for course in ge_courses:
#             if course not in selected_courses and total_units + course['units'] <= max_units:
#                 selected_courses.append(course)
#                 total_units += course['units']

#     return selected_courses, total_units


# unit_balancer.py

# This is when we want at least one ge course in each term

def prune_uc_to_cc_map(
    new_course: str,
    uc_to_cc_map: dict[str, list[list[str]]],
    completed: set[str]
) -> None:
    """
    After new_course is completed:
    - Remove any UC-course whose one AND-block is now ⊆ completed.
    - For that UC-course’s other blocks that are single courses,
      add those courses to completed (so they won’t be picked later).
    """
    # We iterate over a snapshot so we can del() safely.
    for uc_course, blocks in list(uc_to_cc_map.items()):
        for block in blocks:
            # If this block is now fully taken…
            if new_course in block and set(block).issubset(completed):
                # 1) Requirement satisfied ⇒ drop the UC-course entirely
                del uc_to_cc_map[uc_course]

                # 2) Any other single-course alternatives get marked done
                for other in blocks:
                    if other is not block and len(other) == 1:
                        completed.add(other[0])
                break  # move on to next uc_course



# unit_balancer.py
def select_courses_for_term(candidates, completed, uc_to_cc_map, all_cc_course_codes, MAX_UNITS=20):
    print(f"\n[BALANCER] start term, completed={sorted(completed)}, map keys={list(uc_to_cc_map.keys())}")
    remaining_ges    = [c for c in candidates if 'reqIds' in c]
    remaining_majors = [c for c in candidates if 'reqIds' not in c]

    selected = []
    total_units = 0
    pruned_codes = set()   # ← collect all OR‐courses to drop

    # STEP 1: pick one GE
    if remaining_ges:
        ge = remaining_ges.pop(0)
        print(f"[BALANCER] considering GE {ge['courseCode']} ({ge['units']}u)")
        if total_units + ge['units'] <= MAX_UNITS:
            print(f"   → selecting GE {ge['courseCode']}")
            selected.append(ge)
            total_units += ge['units']
            completed.add(ge['courseCode'])

    # STEP 2: majors
    for m in remaining_majors:
        code, units = m['courseCode'], m['units']
        print(f"[BALANCER] considering MAJOR {code} ({units}u)")
        if code in completed:
            print("   → skip: already completed")
            continue
        if total_units + units > MAX_UNITS:
            print("   → skip: unit cap")
            continue

        # pick it
        print("   → selecting")
        selected.append(m)
        total_units += units
        completed.add(code)
        
        

        
        # Whenever you complete a base course, complete its honors variant too (and vice versa)
        base = code.rstrip('H')    # e.g. "MATH 1AH" -> "MATH 1A", or "MATH 1A" -> "MATH 1A"
        hon  = base + 'H'          # "MATH 1AH"
        for eq in (base, hon):
            if eq != code and eq in all_cc_course_codes:
                print(f"[EQUIV] also marking equivalent {eq} complete")
                completed.add(eq)

        # now prune any UC requirement we’ve satisfied
        for uc_course, blocks in list(uc_to_cc_map.items()):
            if any(set(block).issubset(completed) for block in blocks):
                print(f"   [PRUNE] requirement {uc_course} satisfied; dropping it")
                del uc_to_cc_map[uc_course]

                # collect *every* CC‐course in those blocks for pruning
                for block in blocks:
                    for cc_code in block:
                        # if it's not the one we just completed, mark it as pruned
                        if cc_code not in completed:
                            pruned_codes.add(cc_code)
                            print(f"      [PRUNE] will drop CC‐course {cc_code}")
                break

    # STEP 3: more GEs
    for ge in remaining_ges:
        code, units = ge['courseCode'], ge['units']
        print(f"[BALANCER] reconsider GE {code} ({units}u)")
        if code in completed:
            print("   → skip: already completed")
            continue
        if total_units + units <= MAX_UNITS:
            print("   → selecting GE")
            selected.append(ge)
            total_units += units
            completed.add(code)

    print(f"[BALANCER] end term: selected={[c['courseCode'] for c in selected]}, total_units={total_units}")
    return selected, total_units, pruned_codes


