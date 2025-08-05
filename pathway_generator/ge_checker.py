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
            sub_min_total = 0
            if "subRequirements" in req:
                if pattern_id == "7CoursePattern" and req["reqId"] == "GE_General":
                    # 7CoursePattern special case logic stays as is
                    sub_ids = [s["reqId"] for s in req["subRequirements"]]
                    sub_maxes = {s["reqId"]: s.get("maxCourses", float('inf')) for s in req["subRequirements"]}
                    taken_per_sub = {}

                    for sub_id in sub_ids:
                        count = sum(1 for c in self.completed_courses if sub_id in c.get("tags", []))
                        taken_per_sub[sub_id] = min(count, sub_maxes[sub_id])

                    total_taken = sum(taken_per_sub.values())
                    overall_min = req.get("minCourses", 0)
                    remaining_courses = max(0, overall_min - total_taken)

                    if remaining_courses > 0:
                        remaining[req["reqId"]] = {
                            "name": req["name"],
                            "courses_remaining": remaining_courses
                        }

                    for sub in req["subRequirements"]:
                        sub_id = sub["reqId"]
                        taken = taken_per_sub.get(sub_id, 0)
                        remaining[sub_id] = {
                            "name": sub["name"] + " (taken)",
                            "courses_remaining": taken
                        }

                else:
                    fulfilled_per_sub = {}
                    leftover_tags = set()

                    for sub in req["subRequirements"]:
                        sub_id = sub["reqId"]
                        sub_min = sub.get("minCourses", 0)
                        sub_min_total += sub_min
                        matched = [c for c in self.completed_courses if sub_id in c.get("tags", [])]
                        fulfilled_count = min(len(matched), sub_min)
                        fulfilled_per_sub[sub_id] = fulfilled_count
                        if fulfilled_count < sub_min:
                            remaining[sub_id] = {
                                "name": sub["name"],
                                "courses_remaining": sub_min - fulfilled_count
                            }
                        # Save *extra* matched courses (beyond sub min) for leftover
                        leftover_tags.update(c["name"] for c in matched[sub_min:])

                # Handle leftover for OR-style requirements
                leftover_key    = f"{req['reqId']}_Leftover"
                leftover_needed = req.get("minCourses", 0) - sub_min_total

                # 1) count “extra” subRequirement courses
                all_or_tags           = {s["reqId"] for s in req["subRequirements"]}
                valid_extra_courses   = [
                    c for c in self.completed_courses
                    if any(tag in all_or_tags for tag in c.get("tags", []))
                    and c["name"] in leftover_tags
                ]

                # 2) count any courses explicitly tagged as the leftover bucket
                explicit_leftovers = [
                    c for c in self.completed_courses
                    if leftover_key in c.get("tags", [])
                ]

                # 3) remaining = needed minus both sources
                leftover_remaining = max(
                    0,
                    leftover_needed - len(valid_extra_courses) - len(explicit_leftovers)
                )

                if leftover_remaining > 0:
                    remaining[leftover_key] = {
                        "name": f"{req['name']} (either subcategory)",
                        "courses_remaining": leftover_remaining
                    }

            else:
                res = self._evaluate_requirement(req, self.completed_courses)
                if res:
                    remaining[req["reqId"]] = res

        return remaining

    def is_fulfilled(self, pattern_id: str) -> bool:
        return len(self.get_remaining_requirements(pattern_id)) == 0
