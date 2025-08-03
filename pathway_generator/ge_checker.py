class GE_Tracker:
    def __init__(self, ge_data, ccc_term_types=None):
        self.ge_data = ge_data
        self.ge_patterns = {}  # pattern_id -> list of requirements
        self.completed_courses = []
        self.ccc_term_types = ccc_term_types or {}

    def load_pattern(self, pattern_id: str):
        pattern = next((p for p in self.ge_data["requirementPatterns"] if p["patternId"] == pattern_id), None)
        if pattern:
            self.ge_patterns[pattern_id] = pattern["requirements"]

    def add_completed_course(self, course_name: str, tags: list, units: int = 3):
        self.completed_courses.append({"name": course_name, "tags": tags, "units": units})

    def _get_unit_scale(self, ccc_name: str):
        """Convert quarter units to semester equivalent if needed"""
        term_type = self.ccc_term_types.get(ccc_name, "semester")
        return 1.0 if term_type == "semester" else 0.67  # quarter to semester conversion

    def _evaluate_requirement(self, req: dict, completed_courses: list, ccc_name: str = ""):
        req_id = req["reqId"]
        min_courses = req.get("minCourses", 0)
        min_units = req.get("minUnits", 0)
        
        # Apply unit scaling for quarter systems
        unit_scale = self._get_unit_scale(ccc_name)
        min_units_scaled = min_units * unit_scale if min_units > 0 else 0

        matched_courses = [c for c in completed_courses if req_id in c.get("tags", [])]
        count = len(matched_courses)
        total_units = sum(c.get("units", 3) for c in matched_courses)

        remaining_courses = max(0, min_courses - count)
        remaining_units = max(0, min_units_scaled - total_units)

        if remaining_courses == 0 and remaining_units == 0:
            return None
            
        return {
            "name": req["name"],
            "courses_remaining": remaining_courses,
            "units_remaining": round(remaining_units, 1),
            "tags": [req_id]  # Critical for pathway_generator.py
        }

    def get_remaining_requirements(self, pattern_id: str, ccc_name: str = ""):
        requirements = self.ge_patterns.get(pattern_id)
        if not requirements:
            return {}

        remaining = {}

        for req in requirements:
            if "subRequirements" in req:
                if pattern_id == "7CoursePattern" and req["reqId"] == "GE_General":
                    # 7CoursePattern special case logic
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
                            "courses_remaining": remaining_courses,
                            "tags": sub_ids  # All sub-tags for flexibility
                        }

                    # Report taken counts per subcategory
                    for sub in req["subRequirements"]:
                        sub_id = sub["reqId"]
                        taken = taken_per_sub.get(sub_id, 0)
                        remaining[f"{sub_id}_taken"] = {
                            "name": f"{sub['name']} (taken: {taken})",
                            "courses_remaining": 0,
                            "tags": [sub_id]
                        }

                else:
                    # IGETC or other sub-requirement cases
                    sub_min_total = 0
                    fulfilled_per_sub = {}
                    extra_courses = []

                    for sub in req["subRequirements"]:
                        sub_id = sub["reqId"]
                        sub_result = self._evaluate_requirement(sub, self.completed_courses, ccc_name)
                        
                        if sub_result:
                            remaining[sub_id] = sub_result
                        
                        sub_min_total += sub.get("minCourses", 0)
                        
                        # Track extra courses for leftover calculation
                        matched = [c for c in self.completed_courses if sub_id in c.get("tags", [])]
                        sub_min = sub.get("minCourses", 0)
                        if len(matched) > sub_min:
                            extra_courses.extend(matched[sub_min:])

                    # Handle leftover for OR-style requirements
                    leftover_needed = req.get("minCourses", 0) - sub_min_total
                    if leftover_needed > 0:
                        leftover_remaining = max(0, leftover_needed - len(extra_courses))
                        all_or_tags = [s["reqId"] for s in req["subRequirements"]]
                        
                        remaining[f"{req['reqId']}_Leftover"] = {
                            "name": f"{req['name']} (additional)",
                            "courses_remaining": leftover_remaining,
                            "tags": all_or_tags
                        }

            else:
                # Simple requirement
                res = self._evaluate_requirement(req, self.completed_courses, ccc_name)
                if res:
                    remaining[req["reqId"]] = res

        return remaining

    def is_fulfilled(self, pattern_id: str, ccc_name: str = "") -> bool:
        remaining = self.get_remaining_requirements(pattern_id, ccc_name)
        # Filter out "taken" status entries
        actual_remaining = {k: v for k, v in remaining.items() if not k.endswith("_taken")}
        return len(actual_remaining) == 0

    # Aliases for pathway_generator.py compatibility
    def check_ge_progress(self, course_name: str, tags: list, units: int = 3):
        """Add a course and return its impact on GE progress"""
        self.add_completed_course(course_name, tags, units)
        return {"course_added": course_name, "tags_applied": tags}

    def get_remaining_ge(self, pattern_id: str, ccc_name: str = ""):
        """Alias for get_remaining_requirements"""
        return self.get_remaining_requirements(pattern_id, ccc_name)

    def ge_is_complete(self, pattern_id: str, ccc_name: str = ""):
        """Alias for is_fulfilled"""
        return self.is_fulfilled(pattern_id, ccc_name)