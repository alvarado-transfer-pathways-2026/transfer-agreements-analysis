#This one prioritizes Major courses and then GE courses

# def select_courses_for_term(eligible_courses, completed_courses=None, max_units=20):
#     if completed_courses is None:
#         completed_courses = []

#     # Filter out already completed courses
#     remaining_courses = [c for c in eligible_courses if c['courseCode'] not in completed_courses]

#     # Separate Major and GE courses
#     major_courses = [c for c in remaining_courses if 'Major' in c.get('tags', [])]
#     ge_courses = [c for c in remaining_courses if 'GE' in c.get('tags', [])]

#     selected_courses = []
#     total_units = 0

#     # First try to add as many Major courses as possible
#     for course in major_courses:
#         if total_units + course['units'] <= max_units:
#             selected_courses.append(course)
#             total_units += course['units']

#     # If still space left, add GE courses
#     if total_units < max_units:
#         for course in ge_courses:
#             if total_units + course['units'] <= max_units:
#                 selected_courses.append(course)
#                 total_units += course['units']

#     return selected_courses, total_units

# unit_balancer.py

# This is when we want at least one ge course in each term

def select_courses_for_term(eligible_courses, completed_courses=None, max_units=20):
    """
    Selects a list of courses from eligible_courses to fill a term up to max_units,
    ensuring at least one GE course is selected per term if any remain.

    Parameters:
        eligible_courses (list): List of dicts with keys like 'courseCode', 'units', 'tags'
        completed_courses (list): List of courseCodes already taken
        max_units (int): Max units allowed per term (default = 20)

    Returns:
        selected_courses (list): List of selected course dicts
        total_units (int): Total units of selected courses
    """
    if completed_courses is None:
        completed_courses = []

    # Filter out already completed courses
    remaining_courses = [c for c in eligible_courses if c['courseCode'] not in completed_courses]

    # Separate courses by tag
    ge_courses = [c for c in remaining_courses if 'GE' in c.get('tags', [])]
    major_courses = [c for c in remaining_courses if 'Major' in c.get('tags', [])]
    other_courses = [c for c in remaining_courses if 'GE' not in c.get('tags', []) and 'Major' not in c.get('tags', [])]

    selected_courses = []
    total_units = 0
    ge_taken = False

    # Always try to take at least one GE first (if available)
    for course in ge_courses:
        if total_units + course['units'] <= max_units:
            selected_courses.append(course)
            total_units += course['units']
            ge_courses.remove(course)  # Remove from list to avoid duplication
            ge_taken = True
            break  # only one GE for now

    # Add major courses next
    for course in major_courses:
        if total_units + course['units'] <= max_units:
            selected_courses.append(course)
            total_units += course['units']

    # Add additional GEs (if room and still unmet)
    for course in ge_courses:
        if total_units + course['units'] <= max_units:
            selected_courses.append(course)
            total_units += course['units']

    # Add other courses last
    for course in other_courses:
        if total_units + course['units'] <= max_units:
            selected_courses.append(course)
            total_units += course['units']

    return selected_courses, total_units
