class GE_Tracker:
    def __init__(self, ge_reqs_data):
        self.reqs = self._flatten_requirements(ge_reqs_data)
        self.state = self._init_state()

    def _flatten_requirements(self, data):
        flattened = {}
        for pattern in data["requirementPatterns"]:
            pattern_id = pattern["patternId"]
            flattened[pattern_id] = {}

            for req in pattern["requirements"]:
                flattened[pattern_id][req["reqId"]] = {
                    "name": req["name"],
                    "minCourses": req.get("minCourses", 0),
                    "minUnits": req.get("minUnits", 0),
                    "subRequirements": {}
                }

                for sub in req.get("subRequirements", []):
                    flattened[pattern_id][req["reqId"]]["subRequirements"][sub["reqId"]] = {
                        "name": sub["name"],
                        "minCourses": sub.get("minCourses", 0),
                        "minUnits": sub.get("minUnits", 0)
                    }
        return flattened

    def _init_state(self):
        state = {}
        for pattern_id, areas in self.reqs.items():
            state[pattern_id] = {}
            for area_id, area_info in areas.items():
                state[pattern_id][area_id] = {
                    "courses_completed": 0,
                    "units_completed": 0
                }

                for sub_id in area_info["subRequirements"]:
                    state[pattern_id][sub_id] = {
                        "courses_completed": 0,
                        "units_completed": 0
                    }
        return state

    def check_course(self, course):
        tags = course.get("tags", [])
        for tag in tags:
            for pattern_id, pattern_reqs in self.state.items():
                if tag in pattern_reqs:
                    pattern_reqs[tag]["courses_completed"] += 1
                    pattern_reqs[tag]["units_completed"] += course.get("units", 0)

    def get_remaining_requirements(self, pattern_name):
        remaining = {}
        for area_id, area in self.reqs[pattern_name].items():
            state = self.state[pattern_name][area_id]
            needed_courses = area.get("minCourses", 0)
            needed_units = area.get("minUnits", 0)

            if state["courses_completed"] < needed_courses or state["units_completed"] < needed_units:
                remaining[area_id] = {
                    "name": area["name"],
                    "courses_remaining": max(0, needed_courses - state["courses_completed"]),
                    "units_remaining": max(0, needed_units - state["units_completed"])
                }

            for sub_id, sub in area.get("subRequirements", {}).items():
                sub_state = self.state[pattern_name][sub_id]
                if (sub_state["courses_completed"] < sub["minCourses"] or
                    sub_state["units_completed"] < sub.get("minUnits", 0)):
                    remaining[sub_id] = {
                        "name": sub["name"],
                        "courses_remaining": max(0, sub["minCourses"] - sub_state["courses_completed"]),
                        "units_remaining": max(0, sub.get("minUnits", 0) - sub_state["units_completed"])
                    }
        return remaining

    def is_fulfilled(self, pattern_name):
        return len(self.get_remaining_requirements(pattern_name)) == 0
