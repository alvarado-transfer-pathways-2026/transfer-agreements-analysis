import os
import pandas as pd
import json
from collections import defaultdict

DATA_DIR = 'results/'
OUTPUT_DIR = '.' # Output files will be created in the same directory as the script

# This dictionary will store our deeply nested data
# Format: { "UC_Name": { "UC_Course": { "articulated_cc_courses": { "CC_Name": ["CC_Course_1", "CC_Course_2"] } } } }
uc_articulation_map = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

print("--- Generating Raw Articulation Map from 'results/' directory ---")

os.makedirs(OUTPUT_DIR, exist_ok=True)

for filename in os.listdir(DATA_DIR):
    if filename.endswith('_allUC.csv'):
        file_path = os.path.join(DATA_DIR, filename)
        
        try:
            df = pd.read_csv(file_path)
            
            for index, row in df.iterrows():
                uc_name = row['UC Campus'].strip()
                cc_name = row['CC'].strip()
                
                uc_courses_raw = str(row['UC Course Requirement']).strip()
                uc_courses = [c.strip() for c in uc_courses_raw.split(';') if c.strip()]

                cc_courses_raw = []
                for col in df.columns:
                    if 'Courses Group' in col and pd.notna(row[col]):
                        cc_courses_raw.append(str(row[col]).strip())
                
                # Link each UC course to the list of articulated CC courses
                for uc_course in uc_courses:
                    # Using a set to prevent duplicate CC course entries for the same UC course
                    if 'articulated_cc_courses' not in uc_articulation_map[uc_name][uc_course]:
                         uc_articulation_map[uc_name][uc_course]['articulated_cc_courses'] = defaultdict(set)
                    
                    for cc_course_group in cc_courses_raw:
                        uc_articulation_map[uc_name][uc_course]['articulated_cc_courses'][cc_name].add(cc_course_group)

        except Exception as e:
            print(f"Could not process {filename}: {e}")

# --- Convert sets to sorted lists for clean JSON output ---
final_output = {}
for uc, courses in sorted(uc_articulation_map.items()):
    final_output[uc] = {}
    for uc_course, details in sorted(courses.items()):
        final_output[uc][uc_course] = {
            'articulated_cc_courses': {
                cc_name: sorted(list(cc_courses)) for cc_name, cc_courses in sorted(details['articulated_cc_courses'].items())
            }
        }

# --- FILE WRITING LOGIC ---
output_filepath = os.path.join(OUTPUT_DIR, 'raw_articulation_map.json')
with open(output_filepath, 'w') as f:
    json.dump(final_output, f, indent=2)

print(f"\n✅ Analysis complete. Raw articulation map saved to '{output_filepath}'")
print("\n--- Generation Complete ---")