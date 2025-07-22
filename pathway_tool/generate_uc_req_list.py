import os
import pandas as pd
import json
from collections import defaultdict

DATA_DIR = 'filtered_results/'
OUTPUT_DIR = '.' # Output files will be created in the same directory as the script

# This dictionary will store our nested data
# Format: { "UC_Name": {"Course1", "Course2", ...} }
# Using a set for the value automatically handles duplicates
uc_courses_by_campus = defaultdict(set)

print("--- Generating UC Requirement List by Campus ---")

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

for filename in os.listdir(DATA_DIR):
    if filename.endswith('_filtered.csv'):
        file_path = os.path.join(DATA_DIR, filename)
        
        try:
            df = pd.read_csv(file_path)
            
            # Iterate through each row of the CSV
            for index, row in df.iterrows():
                uc_name = row['UC Name']
                
                # The 'Receiving' column can have multiple courses separated by ';'
                receiving_courses = str(row['Receiving']).split(';')
                
                for course in receiving_courses:
                    cleaned_course = course.strip()
                    if cleaned_course: # Ensure it's not an empty string
                        uc_courses_by_campus[uc_name].add(cleaned_course)

        except Exception as e:
            print(f"Could not process {filename}: {e}")

# --- Convert sets to sorted lists for clean JSON output ---
final_output = {}
for uc, courses_set in uc_courses_by_campus.items():
    final_output[uc] = sorted(list(courses_set))

# --- START: ADD THE NEW DIAGNOSTIC CODE HERE ---
print(f"\nFound {len(final_output)} UC campuses:")
for uc, courses in final_output.items():
    print(f"  {uc}: {len(courses)} unique courses")
# Show a sample of what was extracted
if final_output:
    sample_uc = list(final_output.keys())[0]
    sample_courses = final_output[sample_uc][:5]  # First 5 courses
    print(f"\nSample courses from {sample_uc}: {sample_courses}")
# --- END: ADD THE NEW DIAGNOSTIC CODE HERE ---


# --- FILE WRITING LOGIC ---
output_filepath = os.path.join(OUTPUT_DIR, 'uc_req_list_by_campus.json')
with open(output_filepath, 'w') as f:
    json.dump(final_output, f, indent=2, sort_keys=True)

print(f"\n✅ Analysis complete. Results saved to '{output_filepath}'")
print("\n--- Generation Complete ---")