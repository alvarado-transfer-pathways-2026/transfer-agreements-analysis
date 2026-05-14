import pandas as pd
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from district_indices import DISTRICT_INDICES
from course_group_semantics import is_articulated

COURSE_GROUPS = {
    'Calculus':             {'color': "#EC2424", 'patterns': ['calc']},
    'Intro Programming':    {'color': "#25ADA7", 'patterns': ['intro', 'program']},
    'Data Structures':      {'color': "#8F35B3", 'patterns': ['data', 'struct']},
    'Advanced Math':        {'color': "#0B7C3C", 'patterns': ['linear', 'differential']},
    'Computer Organization':    {'color': "#0C5382", 'patterns': ['organ', 'system', 'computer']},
    'Discrete Math':        {'color': '#FF9F1C', 'patterns': ['discrete']},
}

UC_NAME_INDICES = {
    'UCD':    'UC1*',
    'UCM':    'UC2 ',
    'UCSD':   'UC3*',
    'UCSB':   'UC4*',
    'UCLA':   'UC5*',
    'UCB':    'UC6 ',
    'UCSC':   'UC7*',
    'UCI':    'UC8*',
    'UCR':    'UC9*',
}

COURSE_CATEGORIES = list(COURSE_GROUPS.keys())

def normalize_requirement_value(value):
    return " ".join(str(value).strip().split())

def normalize_receiving_requirement(value):
    parts = [normalize_requirement_value(part) for part in str(value).split(';')]
    parts = [part for part in parts if part]
    return "; ".join(sorted(parts)) if len(parts) > 1 else (parts[0] if parts else "")

def load_current_requirement_keys():
    path = Path(__file__).resolve().parents[2] / 'scraping' / 'files' / 'course_reqs.json'
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8') as f:
        requirements = json.load(f).get('UC_REQUIREMENTS', {})
    keys = set()
    for uc_name, groups in requirements.items():
        for group_id, options in groups.items():
            by_set = {}
            for option in options:
                if len(option) < 2:
                    continue
                receiving, set_id = option[0], option[1]
                normalized_set_id = normalize_requirement_value(set_id)
                by_set.setdefault(normalized_set_id, []).append(normalize_requirement_value(receiving))
                keys.add((
                    normalize_requirement_value(uc_name),
                    normalize_requirement_value(group_id),
                    normalized_set_id,
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

def filter_current_requirements(df):
    keys = load_current_requirement_keys()
    if keys is None:
        return df
    mask = df.apply(
        lambda row: (
            normalize_requirement_value(row.get('UC Name', '')),
            normalize_requirement_value(row.get('Group ID', '')),
            normalize_requirement_value(row.get('Set ID', '')),
            normalize_receiving_requirement(row.get('Receiving', '')),
        ) in keys,
        axis=1,
    )
    return df[mask]

def can_transfer_to_uc(df, uc_name):
    # Get all requirements for this UC
    uc_requirements = df[df['UC Name'] == uc_name]
    unarticulated_courses = []
    
    # Group requirements by Group ID to handle sets
    grouped_reqs = uc_requirements.groupby('Group ID')
    
    # Check each group of requirements
    for group_id, group_data in grouped_reqs:
        # If there are multiple Set IDs, only one needs to be satisfied
        set_ids = group_data['Set ID'].unique()
        if len(set_ids) > 1:
            # Check if at least one set is satisfied
            set_satisfied = False
            best_set_unarticulated = []
            min_unarticulated = float('inf')
            
            for set_id in set_ids:
                set_data = group_data[group_data['Set ID'] == set_id]
                current_set_unarticulated = []
                
                for _, row in set_data.iterrows():
                    if not is_articulated(row):
                        current_set_unarticulated.append(row['Receiving'])
                            
                if len(current_set_unarticulated) == 0:
                    set_satisfied = True
                    break
                elif len(current_set_unarticulated) < min_unarticulated:
                    min_unarticulated = len(current_set_unarticulated)
                    best_set_unarticulated = current_set_unarticulated
                    
            if not set_satisfied:
                unarticulated_courses.extend(best_set_unarticulated)
        else:
            # Single set ID - all courses must be satisfied
            for _, row in group_data.iterrows():
                if not is_articulated(row):
                    unarticulated_courses.append(row['Receiving'])
    
    return unarticulated_courses

def count_transfer_options(file_path):
    """
    Reads a district CSV file and returns:
      - district_name
      - DataFrame with columns [UC Name, counts, unarticulated_courses]
        where `unarticulated_courses` is a '\n'-joined list of
        "Group X: course1, course2, …" lines.
    """
    df = pd.read_csv(file_path)
    df = filter_current_requirements(df)
    district_name = os.path.basename(file_path).replace('.csv', '').replace('_', ' ')
    
    records = []
    for uc in df['UC Name'].unique():
        uc_index = UC_NAME_INDICES.get(uc, uc)
        uc_df = df[df['UC Name'] == uc]
        # gather unarticulated courses by group, considering Set IDs
        grouped = {}
        for group_id, group_data in uc_df.groupby('Group ID'):
            # Check if this group has multiple Set IDs
            set_ids = group_data['Set ID'].unique()
            if len(set_ids) > 1:
                # For multiple Set IDs, check if any set is fully articulated
                set_satisfied = False
                best_set_courses = None
                min_unarticulated = float('inf')
                
                for set_id in set_ids:
                    set_data = group_data[group_data['Set ID'] == set_id]
                    current_set_unarticulated = set()
                    
                    for _, row in set_data.iterrows():
                        if not is_articulated(row):
                            current_set_unarticulated.add(row['Receiving'])
                    
                    if len(current_set_unarticulated) == 0:
                        set_satisfied = True
                        break
                    elif len(current_set_unarticulated) < min_unarticulated:
                        min_unarticulated = len(current_set_unarticulated)
                        best_set_courses = current_set_unarticulated
                
                if not set_satisfied and best_set_courses:
                    grouped[group_id] = best_set_courses
            else:
                # Single Set ID - check all courses
                unarticulated = set()
                for _, row in group_data.iterrows():
                    if not is_articulated(row):
                        unarticulated.add(row['Receiving'])
                if unarticulated:
                    grouped[group_id] = unarticulated
        
        # build the multi-line string
        if grouped:
            lines = []
            for gid, courses in sorted(grouped.items()):
                courses_list = sorted(courses)
                lines.append(f"{gid}: {', '.join(courses_list)}")
            detail = "\n".join(lines)
            count = 0
        else:
            detail = ""    # fully articulated → blank cell
            count = 1
    
        records.append({
            'UC Index': uc_index,
            'counts': count,
            'unarticulated_courses': detail
        })
    
    return district_name, pd.DataFrame(records)
    
def analyze_all_districts(directory):
    all_data = []
    
    # Process all CSV files in the directory
    for file in os.listdir(directory):
        if file.endswith('.csv'):
            file_path = os.path.join(directory, file)
            district_name, transfer_counts = count_transfer_options(file_path)
            
            # Add district name to each row
            transfer_counts['District'] = DISTRICT_INDICES.get(district_name)
            all_data.append(transfer_counts)
    
    # Combine all data
    combined_data = pd.concat(all_data, ignore_index=True)
    return combined_data
