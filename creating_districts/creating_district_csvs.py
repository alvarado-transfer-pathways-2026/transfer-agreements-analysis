import os
import sys
import pandas as pd
import json
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from course_group_semantics import best_option_course_count, is_articulated

def normalize_college_name(name):
    """Normalize college names for matching filenames to districts.json."""
    return " ".join(str(name).split()).casefold()

def normalize_requirement_value(value):
    return " ".join(str(value).strip().split())

def normalize_receiving_requirement(value):
    parts = [normalize_requirement_value(part) for part in str(value).split(';')]
    parts = [part for part in parts if part]
    return "; ".join(sorted(parts)) if len(parts) > 1 else (parts[0] if parts else "")

def load_current_requirement_keys(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        requirements = json.load(f).get('UC_REQUIREMENTS', {})

    keys = set()
    for uc_name, groups in requirements.items():
        for group_id, options in groups.items():
            by_set = defaultdict(list)
            for option in options:
                if len(option) < 2:
                    continue
                receiving, set_id = option[0], option[1]
                by_set[normalize_requirement_value(set_id)].append(normalize_requirement_value(receiving))
                keys.add((
                    normalize_requirement_value(uc_name),
                    normalize_requirement_value(group_id),
                    normalize_requirement_value(set_id),
                    normalize_receiving_requirement(receiving),
                ))
            for set_id, receiving_courses in by_set.items():
                keys.add((
                    normalize_requirement_value(uc_name),
                    normalize_requirement_value(group_id),
                    set_id,
                    normalize_receiving_requirement("; ".join(receiving_courses)),
                ))
    return keys

def requirement_key(row):
    return (
        normalize_requirement_value(row.get('UC Name', '')),
        normalize_requirement_value(row.get('Group ID', '')),
        normalize_requirement_value(row.get('Set ID', '')),
        normalize_receiving_requirement(row.get('Receiving', '')),
    )

def count_total_courses(row, course_group_cols):
    """Return the smallest complete option size for a row."""
    count = best_option_course_count(row)
    return count if count is not None else float("inf")

# --- Determine paths based on script location ---
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir   = os.path.dirname(script_dir)

districts_json_path = os.path.join(script_dir, 'districts.json')
input_folder        = os.path.join(root_dir, 'filtered_results')
output_folder       = os.path.join(root_dir, 'district_csvs')
course_reqs_path    = os.path.join(root_dir, 'scraping', 'files', 'course_reqs.json')

# Make sure output folder exists
os.makedirs(output_folder, exist_ok=True)

# --- Load district mapping ---
with open(districts_json_path, 'r') as f:
    districts_data = json.load(f)['districts']

current_requirement_keys = load_current_requirement_keys(course_reqs_path)

# Build college -> district lookup
college_to_district = {}
normalized_college_lookup = {}
for district, info in districts_data.items():
    for college in info['colleges']:
        college_to_district[college] = district
        normalized_college_lookup[normalize_college_name(college)] = (college, district)

# --- Collect data by district ---
district_data = defaultdict(list)

print(f"Reading all college CSVs from: {input_folder}")
for filename in os.listdir(input_folder):
    if not filename.endswith('.csv'):
        continue

    college_name = filename.replace('_filtered.csv', '').replace('_', ' ')
    file_path    = os.path.join(input_folder, filename)
    df           = pd.read_csv(file_path)
    if current_requirement_keys is not None:
        df = df[df.apply(lambda row: requirement_key(row) in current_requirement_keys, axis=1)]

    if college_name in college_to_district:
        canonical_college_name = college_name
        district_name = college_to_district[college_name]
    else:
        normalized_match = normalized_college_lookup.get(normalize_college_name(college_name))
        if normalized_match:
            canonical_college_name, district_name = normalized_match
        else:
            print(f"  ⚠️  Warning: {college_name} not found in districts.json, skipping.")
            continue

    if not district_name:
        print(f"  ⚠️  Warning: {college_name} not found in districts.json, skipping.")
        continue

    df.insert(0, 'College Name', canonical_college_name)
    district_data[district_name].append(df)

# --- Merge and pick best articulations per district ---
print("\nCombining into district files...")
for district, dfs in district_data.items():
    combined = pd.concat(dfs, ignore_index=True)

    # Identify course‐group columns
    base_cols         = ['College Name', 'UC Name', 'Group ID', 'Set ID', 'Num Required', 'Receiving']
    course_group_cols = [c for c in combined.columns if c not in base_cols]

    final_rows = []
    grouped    = combined.groupby(['UC Name', 'Group ID', 'Set ID', 'Receiving'])

    for _, group_df in grouped:
        # Prefer articulated rows
        articulated = group_df[group_df.apply(is_articulated, axis=1)]

        if not articulated.empty:
            # Take the one with fewest total courses
            articulated = articulated.copy()
            articulated['Total Courses'] = articulated.apply(
                lambda r: count_total_courses(r, course_group_cols), axis=1
            )
            best_row = articulated.sort_values('Total Courses').iloc[0].drop('Total Courses')
        else:
            # Make a synthetic “Not Articulated” row
            example_row = group_df.iloc[0].copy()
            example_row['College Name']    = 'Not Articulated'
            example_row['Courses Group 1'] = 'Not Articulated'
            for col in course_group_cols[1:]:
                example_row[col] = ''
            best_row = example_row

        final_rows.append(best_row)

    final_df = pd.DataFrame(final_rows)

    # Write out
    safe_name      = district.replace(' ', '_').replace('/', '_')
    out_csv        = os.path.join(output_folder, f"{safe_name}.csv")
    final_df.to_csv(out_csv, index=False)
    print(f"  ✓ Saved {out_csv}")

print("\nAll district CSVs created successfully!")
