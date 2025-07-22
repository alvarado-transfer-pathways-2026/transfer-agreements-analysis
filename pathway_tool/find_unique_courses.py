import os
import pandas as pd
import re

# The directory where your clean CSVs are located
DATA_DIR = 'filtered_results/'

# A set to store all unique course IDs
unique_courses = set()

def extract_course_ids(course_string):
    """Extracts just the course ID (e.g., 'MATH 181') from a string like 'MATH 181 (4.00)'."""
    if pd.isna(course_string) or course_string == 'Not Articulated':
        return []
    
    # This regular expression finds patterns like 'CS 111' or 'MATH 182'
    # It looks for a sequence of letters, a space, and a sequence of numbers/letters.
    return re.findall(r'[A-Z]+\s[0-9A-Z]+', course_string)

# Loop through every file in the directory
print(f"Scanning files in {os.path.abspath(DATA_DIR)}...")
for filename in os.listdir(DATA_DIR):
    if filename.endswith('_filtered.csv'):
        file_path = os.path.join(DATA_DIR, filename)
        
        try:
            df = pd.read_csv(file_path)
            # Look in all 'Courses Group' columns for course data
            for col in df.columns:
                if 'Courses Group' in col:
                    # Apply the extraction function and add findings to our set
                    df[col].dropna().apply(lambda x: unique_courses.update(extract_course_ids(x)))
        except Exception as e:
            print(f"Could not process {filename}: {e}")

# Print the final sorted list
print("\n--- Unique Major Prep Courses Found ---")
for course in sorted(list(unique_courses)):
    print(course)
print(f"\nFound {len(unique_courses)} unique course codes.")