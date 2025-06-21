import pandas as pd
import os

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
                    for col in [col for col in df.columns if col.startswith('Courses Group')]:
                        if pd.notna(row[col]) and 'Not Articulated' in str(row[col]):
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
                for col in [col for col in df.columns if col.startswith('Courses Group')]:
                    if pd.notna(row[col]) and 'Not Articulated' in str(row[col]):
                        unarticulated_courses.append(row['Receiving'])
    
    return unarticulated_courses

def count_transfer_options(file_path):
    """
    Reads a “_filtered.csv” articulation file and returns:
      - college_name
      - DataFrame with columns [UC Name, counts, unarticulated_courses]
        where `unarticulated_courses` is a '\n'-joined list of
        "Group X: course1, course2, …" lines.
    """
    df = pd.read_csv(file_path)
    college_name = os.path.basename(file_path).replace('_filtered.csv', '')
    
    records = []
    for uc in df['UC Name'].unique():
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
                        for col in [c for c in df.columns if c.startswith('Courses Group')]:
                            if pd.notna(row[col]) and 'Not Articulated' in str(row[col]):
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
                    for col in [c for c in df.columns if c.startswith('Courses Group')]:
                        if pd.notna(row[col]) and 'Not Articulated' in str(row[col]):
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
            'UC Name': uc,
            'counts': count,
            'unarticulated_courses': detail
        })
    
    return college_name, pd.DataFrame(records)
    
def analyze_all_colleges(directory):
    all_data = []
    
    # Process all CSV files in the directory
    for file in os.listdir(directory):
        if file.endswith('_filtered.csv'):
            file_path = os.path.join(directory, file)
            college_name, transfer_counts = count_transfer_options(file_path)

            college_name = college_name.replace('_', ' ')
            
            # Add college name to each row
            transfer_counts['College'] = college_name
            all_data.append(transfer_counts)
    
    # Combine all data
    combined_data = pd.concat(all_data, ignore_index=True)
    return combined_data
