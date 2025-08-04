from plan_exporter import export_term_plan, save_plan_to_json

# Courses for Fall 2025
fall_courses = [
    {
        "courseCode": "CS 101",
        "units": 4,
        "tags": ["CS Major"],
        "fulfills": ["Intro to Programming"]
    },
    {
        "courseCode": "ENGL 100",
        "units": 3,
        "tags": ["GE Area A2"]
    }
]

# Courses for Spring 2026
spring_courses = [
    {
        "courseCode": "MATH 200",
        "units": 5,
        "tags": ["CS Major"],
        "fulfills": ["Discrete Math"]
    },
    {
        "courseCode": "COMM 120",
        "units": 3,
        "tags": ["GE Area A1"]
    }
]

output_plan = []

# Use different course lists for each term
export_term_plan("Fall 2025", fall_courses, output_plan)
export_term_plan("Spring 2026", spring_courses, output_plan)

save_plan_to_json(output_plan)
