class GE_Tracker:
    def __init__(self, ge_data):
        self.ge_data = ge_data
        self.completed_courses = []

    def check_course(self, course: dict):
        self.completed_courses.append(course)

    def _evaluate_requirement(self, req: dict, completed_courses: list):
        req_id = req['reqId']
        min_courses = req.get('minCourses', 0)

        count = sum(1 for c in completed_courses if req_id in c.get('tags', []))
        remaining_courses = max(0, min_courses - count)

        if remaining_courses == 0:
            return None
        return {
            'name': req['name'],
            'courses_remaining': remaining_courses
        }

    def get_remaining_requirements(self, pattern_name: str):
        pattern = next((p for p in self.ge_data["requirementPatterns"] if p["patternId"] == pattern_name), None)
        remaining = {}

        if not pattern:
            return remaining

        for req in pattern["requirements"]:
            if "subRequirements" in req:
                # Evaluate subrequirements individually
                for subreq in req["subRequirements"]:
                    res = self._evaluate_requirement(subreq, self.completed_courses)
                    if res:
                        remaining[subreq["reqId"]] = res

                # Calculate leftover courses needed beyond subrequirements sum
                sum_sub_min = sum(s.get('minCourses', 0) for s in req["subRequirements"])
                leftover = req.get('minCourses', 0) - sum_sub_min
                if leftover > 0:
                    # Count courses completed in all subreq tags combined
                    subreq_ids = [s['reqId'] for s in req["subRequirements"]]
                    count = 0
                    for course in self.completed_courses:
                        if any(tag in subreq_ids for tag in course.get('tags', [])):
                            count += 1

                    remaining_courses = max(0, leftover - max(0, count - sum_sub_min))
                    if remaining_courses > 0:
                        remaining[f"{req['reqId']}_Leftover"] = {
                            'name': f"{req['name']} (either subcategory)",
                            'courses_remaining': remaining_courses
                        }
            else:
                res = self._evaluate_requirement(req, self.completed_courses)
                if res:
                    remaining[req["reqId"]] = res

        return remaining

    def is_fulfilled(self, pattern_name: str) -> bool:
        return len(self.get_remaining_requirements(pattern_name)) == 0
