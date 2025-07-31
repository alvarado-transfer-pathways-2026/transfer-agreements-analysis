from typing import Optional

class GE_Tracker:
    def __init__(self, ge_data):
        self.ge_data = ge_data
        self.completed_courses = []

    def check_course(self, course: dict):
        """Add a course to the list of completed courses."""
        self.completed_courses.append(course)

    def _evaluate_requirement(self, req: dict, completed_courses: list) -> Optional[dict]:
        matched_courses = []
        units_matched = 0

        for course in completed_courses:
            # If any course tag matches one of the requirement tags
            if any(tag in req['tags'] for tag in course.get('tags', [])):
                matched_courses.append(course)
                units_matched += course.get('units', 0)

        remaining_courses = max(0, req['num_courses'] - len(matched_courses))
        remaining_units = max(0, req['num_units'] - units_matched)

        if remaining_courses == 0 and remaining_units == 0:
            return None  # Requirement is fully met

        return {
            'name': req['name'],
            'courses_remaining': remaining_courses,
            'units_remaining': remaining_units
        }


    def get_remaining_requirements(self, pattern_name: str) -> dict:
        pattern = self.ge_data.get(pattern_name, {})
        completed = self.completed_courses
        remaining = {}
        for req_id, req in pattern.items():
            result = self._evaluate_requirement(req, completed)
            if result:
                remaining[req_id] = result
        return remaining

    def is_fulfilled(self, pattern_name: str) -> bool:
        return not self.get_remaining_requirements(pattern_name)
