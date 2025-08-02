import json

def export_term_plan(term_name, selected_courses, output_plan):
    """
    Adds selected courses for a term to the overall pathway plan.

    Parameters:
        term_name (str): Name of the term (e.g., "Fall 2025")
        selected_courses (list of dict): Each course has keys like:
            - courseCode (str)
            - units (int)
            - tags (list of str, optional)
            - fulfills (list of str, optional)
        output_plan (list): A list to accumulate term entries

    Returns:
        None (modifies output_plan in place)
    """
    term_entry = {
        "term": term_name,
        "courses": []
    }

    for course in selected_courses:
        course_entry = {
            "courseCode": course.get("courseCode"),
            "units": course.get("units", 0),
        }

        # Optional fields
        if "tags" in course:
            course_entry["tags"] = course["tags"]
        if "fulfills" in course:
            course_entry["fulfills"] = course["fulfills"]

        term_entry["courses"].append(course_entry)

    output_plan.append(term_entry)


def save_plan_to_json(output_plan, filename="output_pathway.json"):
    """
    Saves the full plan to a JSON file.

    Parameters:
        output_plan (list): List of term dictionaries
        filename (str): Output filename

    Returns:
        None
    """
    with open(filename, "w") as f:
        json.dump(output_plan, f, indent=2)
    print(f"Plan saved to {filename}")


