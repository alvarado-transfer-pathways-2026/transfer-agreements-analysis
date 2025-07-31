#!/usr/bin/env python3
"""
pathway_generator.py

Demo script showing how to call get_required_cc_courses from major_checker.py
and print out the articulated courses for a given community college and UC campuses.

Usage:
    cd pathway_generator
    python pathway_generator.py
"""
from pathlib import Path
from major_checker import get_required_cc_courses


def main():
    # Example inputs
    cc_name = "Palomar_College"
    # selected_ucs = ["UCLA", "UCSD"]
    selected_ucs = ["UCSD", "UCSC"]

    # Directory containing CC articulation JSON files (one level up)
    articulation_dir = Path(__file__).parent.parent / "articulated_courses_json"

    # Fetch articulated CC courses
    courses = get_required_cc_courses(cc_name, selected_ucs, articulation_dir)

    # Print results
    print(f"Articulated courses from {cc_name} for {', '.join(selected_ucs)}:")
    for course in courses:
        print(f" - {course}")


if __name__ == "__main__":
    main()
