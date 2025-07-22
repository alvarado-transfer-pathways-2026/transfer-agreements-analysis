import os
import pandas as pd
import re
import json
from collections import defaultdict

DATA_DIR = 'filtered_results/'
OUTPUT_DIR = '.' # Output files will be created in the same directory as the script

# This dictionary will store our data
# Format: { "CC_Label": ["College Name 1", "College Name 2", ...] }
# Example: { "MATH 181": ["Allan Hancock College", "Citrus College"] }
cc_label_origins = defaultdict(list)

def extract_course_ids(course_string):
    """Extracts just the course ID (e.g., 'MATH 181') from a string like 'MATH 181 (4.00)'."""
    if pd.isna(course_string) or course_string == 'Not Articulated':
        return []
    return re.findall(r'[A-Z]+\s[0-9A-Z]+', course_string)

print("--- Analyzing CC Label Origins ---")

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

for filename in os.listdir(DATA_DIR):
    if filename.endswith('_filtered.csv'):
        college_name = filename.replace('_filtered.csv', '').replace('_', ' ')
        file_path = os.path.join(DATA_DIR, filename)
        
        try:
            df = pd.read_csv(file_path)
            # Check all 'Courses Group' columns
            for col in df.columns:
                if 'Courses Group' in col:
                    for cell_content in df[col].dropna():
                        cc_labels_in_cell = extract_course_ids(cell_content)
                        for cc_label in cc_labels_in_cell:
                            # If we haven't seen this college for this label, add it
                            if college_name not in cc_label_origins[cc_label]:
                                cc_label_origins[cc_label].append(college_name)
        except Exception as e:
            print(f"Could not process {filename}: {e}")

print(f"Found {len(cc_label_origins)} unique CC Labels across {len(os.listdir(DATA_DIR))} colleges.")

# --- FILE WRITING LOGIC ---
output_filepath = os.path.join(OUTPUT_DIR, 'cc_label_origins.json')

# Sort the dictionary by CC Label for clean output
sorted_cc_labels = dict(sorted(cc_label_origins.items()))

with open(output_filepath, 'w') as f:
    json.dump(sorted_cc_labels, f, indent=2)

print(f"✅ Analysis complete. Results saved to '{output_filepath}'")
print("\n--- Analysis Complete ---")