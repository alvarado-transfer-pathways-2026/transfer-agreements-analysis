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

def select_courses_for_term(candidates, completed, MAX_UNITS=20):
    """
    candidates: list of dicts where GE courses have 'reqIds' and majors do not
    completed:  set of courseCodes already taken
    """
    # 1) Partition into GE vs majors
    remaining_ges   = [c for c in candidates if 'reqIds' in c]
    remaining_majors= [c for c in candidates if 'reqIds' not in c]

    selected = []
    total_units = 0

    # 2) STEP 1: Always take one GE if you can
    if remaining_ges:
        # you could sort or prioritize here; we'll just take the first
        ge = remaining_ges.pop(0)
        if total_units + ge['units'] <= MAX_UNITS:
            selected.append(ge)
            total_units += ge['units']
        # if it somehow doesn’t fit (unlikely with 3-unit GEs), you could skip or handle it here

    # 3) STEP 2: Fill with major courses
    for m in remaining_majors:
        if total_units + m['units'] <= MAX_UNITS:
            selected.append(m)
            total_units += m['units']

    # 4) (Optional) If you still want to pack in more GEs after majors:
    for ge in remaining_ges:
        if total_units + ge['units'] <= MAX_UNITS:
            selected.append(ge)
            total_units += ge['units']

    print(selected)
    return selected, total_units
