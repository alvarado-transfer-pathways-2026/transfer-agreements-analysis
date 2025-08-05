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

# unit_balancer.py

def select_courses_for_term(eligible_courses, completed_courses=None, max_units=20):
    """
    Selects a list of courses from eligible_courses to fill a term up to max_units.
    Ensures that at least one GE is taken per term until all GE requirements are met.

    Parameters:
        eligible_courses (list): List of course dicts, either Major or GE courses.
        completed_courses (list): List of courseCodes (for majors) or reqIds (for GEs) already taken.
        max_units (int): Max units allowed per term (default = 20)

    Returns:
        selected_courses (list): List of selected course dicts
        total_units (int): Total units of selected courses
    """
    if completed_courses is None:
        completed_courses = []

    remaining_majors = []
    remaining_ges = []

    # Separate GE and Major courses
    for course in eligible_courses:
        if 'courseCode' in course:
            if course['courseCode'] not in completed_courses:
                remaining_majors.append(course)
        elif 'reqIds' in course:
            if not any(req in completed_courses for req in course['reqIds']):
                remaining_ges.append(course)

    selected_courses = []
    total_units = 0

    # Always try to take at least one GE if available
    took_ge_this_term = False
    for ge_course in remaining_ges:
        if total_units + ge_course['units'] <= max_units:
            selected_courses.append(ge_course)
            total_units += ge_course['units']
            took_ge_this_term = True
            break  # take only one GE first

    # Add major courses next
    for major_course in remaining_majors:
        if total_units + major_course['units'] <= max_units:
            selected_courses.append(major_course)
            total_units += major_course['units']

    # If space is left, add more GEs
    if took_ge_this_term:
        for ge_course in remaining_ges:
            if ge_course not in selected_courses and total_units + ge_course['units'] <= max_units:
                selected_courses.append(ge_course)
                total_units += ge_course['units']

    return selected_courses, total_units
