class GE_Tracker:
    def __init__(self, ge_data):
        self.ge_data = ge_data
        self.ge_patterns = {}  # pattern_id -> list of requirements
        self.completed_courses = []

    def load_pattern(self, pattern_id: str):
        pattern = next((p for p in self.ge_data["requirementPatterns"] if p["patternId"] == pattern_id), None)
        if pattern:
            self.ge_patterns[pattern_id] = pattern["requirements"]

    def add_completed_course(self, course_name: str, tags: list):
        self.completed_courses.append({"name": course_name, "tags": tags})

    def _evaluate_requirement(self, req: dict, completed_courses: list):
        req_id = req["reqId"]
        min_courses = req.get("minCourses", 0)

        count = sum(1 for c in completed_courses if req_id in c.get("tags", []))
        remaining_courses = max(0, min_courses - count)

        if remaining_courses == 0:
            return None
        return {
            "name": req["name"],
            "courses_remaining": remaining_courses
        }

    def get_remaining_requirements(self, pattern_id: str):
        requirements = self.ge_patterns.get(pattern_id)
        if not requirements:
            return {}

        remaining = {}

        for req in requirements:
            if "subRequirements" in req:
                # Special logic for 7CoursePattern's "General" req
                if pattern_id == "7CoursePattern" and req["reqId"] == "GE_General":
                    # Count courses taken per subcategory with maxCourses limits applied
                    sub_ids = [s["reqId"] for s in req["subRequirements"]]
                    sub_maxes = {s["reqId"]: s.get("maxCourses", float('inf')) for s in req["subRequirements"]}

                    # Count how many courses taken per subcategory, capped by maxCourses
                    taken_per_sub = {}
                    for sub_id in sub_ids:
                        count = sum(1 for c in self.completed_courses if sub_id in c.get("tags", []))
                        taken_per_sub[sub_id] = min(count, sub_maxes[sub_id])

                    total_taken = sum(taken_per_sub.values())
                    overall_min = req.get("minCourses", 0)
                    remaining_courses = max(0, overall_min - total_taken)

                    # Report remaining courses at parent level
                    if remaining_courses > 0:
                        remaining[req["reqId"]] = {
                            "name": req["name"],
                            "courses_remaining": remaining_courses
                        }

                    # Report taken courses per subcategory (note: showing taken, not remaining)
                    for sub in req["subRequirements"]:
                        sub_id = sub["reqId"]
                        taken = taken_per_sub.get(sub_id, 0)
                        # We store taken as courses_remaining with "taken" in the name to distinguish
                        remaining[sub_id] = {
                            "name": sub["name"] + " (taken)",
                            "courses_remaining": taken
                        }

                else:
                    # Default logic for other patterns or requirements with subRequirements
                    sub_remaining = []
                    for sub in req["subRequirements"]:
                        res = self._evaluate_requirement(sub, self.completed_courses)
                        if res:
                            sub_remaining.append((sub["reqId"], res))

                    for subreq_id, subreq_info in sub_remaining:
                        remaining[subreq_id] = subreq_info

                    # Handle leftover / OR requirement logic
                    sub_ids = [s["reqId"] for s in req["subRequirements"]]
                    leftover = req.get("minCourses", 0) - sum(s.get("minCourses", 0) for s in req["subRequirements"])
                    if leftover > 0:
                        count = sum(
                            1 for c in self.completed_courses
                            if any(tag in sub_ids for tag in c.get("tags", []))
                        )
                        remaining_courses = max(0, leftover - max(0, count - sum(s.get("minCourses", 0) for s in req["subRequirements"])))
                        if remaining_courses > 0:
                            remaining[f"{req['reqId']}_Leftover"] = {
                                "name": f"{req['name']} (either subcategory)",
                                "courses_remaining": remaining_courses
                            }
            else:
                res = self._evaluate_requirement(req, self.completed_courses)
                if res:
                    remaining[req["reqId"]] = res

        return remaining

    def is_fulfilled(self, pattern_id: str) -> bool:
        return len(self.get_remaining_requirements(pattern_id)) == 0
