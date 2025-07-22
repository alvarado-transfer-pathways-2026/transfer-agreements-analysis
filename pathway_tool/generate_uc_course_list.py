import os
import pandas as pd
import json
from collections import defaultdict

DATA_DIR = 'results/'
OUTPUT_DIR = '.' # Output files will be created in the same directory as the script

# This dictionary will store our nested data
# Format: { "UC_Name": {"Course1", "Course2", ...} }
# Using a set for the value automatically handles duplicates
uc_courses_by_campus = defaultdict(set)

print("--- Generating a clean list of all UC courses by campus from the 'results/' directory ---")

os.makedirs(OUTPUT_DIR, exist_ok=True)

for filename in os.listdir(DATA_DIR):
    if filename.endswith('_allUC.csv'):
        file_path = os.path.join(DATA_DIR, filename)
        
        try:
            df = pd.read_csv(file_path)
            
            # Iterate through each row of the CSV
            for index, row in df.iterrows():
                # Clean up UC campus name by removing extra spaces
                uc_name = ' '.join(str(row['UC Campus']).split())
                
                # The 'UC Course Requirement' column can have multiple courses separated by ';'
                receiving_courses_raw = str(row['UC Course Requirement'])
                
                receiving_courses = [c.strip() for c in receiving_courses_raw.split(';') if c.strip()]
                
                for course in receiving_courses:
                    if course: # Ensure it's not an empty string
                        uc_courses_by_campus[uc_name].add(course)

        except Exception as e:
            print(f"Could not process {filename}: {e}")

# --- Convert sets to sorted lists for clean JSON output ---
final_output = {}
# Sort by UC name for consistent output
for uc, courses_set in sorted(uc_courses_by_campus.items()):
    final_output[uc] = sorted(list(courses_set))

# --- FILE WRITING LOGIC ---
output_filepath = os.path.join(OUTPUT_DIR, 'uc_course_list_by_campus.json')
with open(output_filepath, 'w') as f:
    json.dump(final_output, f, indent=2)

print(f"\n✅ Analysis complete. A clean list of UC courses has been saved to '{output_filepath}'")
print("\n--- Generation Complete ---")