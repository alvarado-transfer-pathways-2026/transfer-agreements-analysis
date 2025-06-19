import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import os
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors

from district_indices import DISTRICT_INDICES

# Define color groups for related courses
COURSE_GROUPS = {
    'Calculus':             {'color': "#EC2424", 'patterns': ['calc']},
    'Intro Programming':    {'color': "#285E5B", 'patterns': ['intro', 'program']},
    'Data Structures':      {'color': "#8F35B3", 'patterns': ['data', 'struct']},
    'Advanced Math':        {'color': "#0B7C3C", 'patterns': ['linear', 'differential']},
    'Computer Organization':    {'color': '#3498DB', 'patterns': ['organ', 'system', 'computer']},
    'Discrete Math':        {'color': '#FF9F1C', 'patterns': ['discrete']},
}

COURSE_CATEGORIES = list(COURSE_GROUPS.keys())


def create_course_heatmap(data, directory):
    """
    Draw a grid of (district × UC) cells, each divided into
    six vertical slices (one per COURSE_CATEGORIES):
      • white if that UC never requires that category in this district
      • pale  if it is required & fully articulated (light version of category color)
      • solid if it is required but *not* fully articulated (full category color)
    Borders around each full cell are drawn in black for clarity.
    """
    import pandas as pd
    import os
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors

    # Helper to lighten a color
    def light(color, amount=0.8):
        """Return a lighter shade of the given color by mixing it with white."""
        rgb = np.array(mcolors.to_rgb(color))
        white = np.ones_like(rgb)
        mixed = rgb + (white - rgb) * amount
        return tuple(mixed)

    # 1) Build missing_lookup keyed by (district_idx, UC)
    missing_lookup = {}
    for _, row in data.iterrows():
        d_idx = row['District']
        uc = row['UC Name']
        raw = row['unarticulated_courses']
        gids = set()
        if isinstance(raw, str) and raw.strip():
            for line in raw.split("\n"):
                gid = line.split(":", 1)[0].strip()
                gids.add(gid)
        missing_lookup.setdefault((d_idx, uc), set()).update(gids)

    # 2) Build required_lookup keyed by (district_idx, UC)
    required_lookup = {}
    for fn in os.listdir(directory):
        if not fn.endswith('.csv'):
            continue
        dn = fn[:-4].replace('_', ' ')
        d_idx = DISTRICT_INDICES.get(dn)
        if d_idx is None:
            continue
        df = pd.read_csv(os.path.join(directory, fn))
        for uc, grp in df.groupby('UC Name')['Group ID']:
            required_lookup.setdefault((d_idx, uc), set()).update(grp.unique())

    # 3) Map raw Group ID -> category
    group_to_cat = {}
    for key in set().union(*required_lookup.values(), *missing_lookup.values()):
        low = key.lower()
        matched = None
        for cat, info in COURSE_GROUPS.items():
            if any(p in low for p in info['patterns']):
                matched = cat
                break
        group_to_cat[key] = matched

    # 4) Setup plot
    districts = sorted(data['District'].unique())
    ucs = sorted(data['UC Name'].unique())
    nD, nU = len(districts), len(ucs)
    fig, ax = plt.subplots(figsize=(nU * 1.2, nD * 0.6))
    ax.set_xlim(0, nU)
    ax.set_ylim(0, nD)
    ax.invert_yaxis()
    slice_w = 1.0 / len(COURSE_CATEGORIES)

    # 5) Draw vertical slices and cell borders
    for i, d_idx in enumerate(districts):
        for j, uc in enumerate(ucs):
            reqs = required_lookup.get((d_idx, uc), set())
            missing = missing_lookup.get((d_idx, uc), set())
            # draw each category slice
            for k, cat in enumerate(COURSE_CATEGORIES):
                gids_req = {g for g in reqs if group_to_cat.get(g) == cat}
                base_color = COURSE_GROUPS[cat]['color']
                if not gids_req:
                    face = 'white'
                elif gids_req & missing:
                    face = base_color  # solid: full category color
                else:
                    face = light(base_color, amount=0.5)  # pale: lightened color
                x0 = j + k * slice_w
                rect = plt.Rectangle(
                    (x0, i), slice_w, 1,
                    facecolor=face,
                    edgecolor='gray', linewidth=0.5
                )
                ax.add_patch(rect)
            # draw a bold border around the full cell
            border = plt.Rectangle(
                (j, i), 1, 1,
                fill=False,
                edgecolor='black', linewidth=1.5
            )
            ax.add_patch(border)

    # 6) Final formatting
    ax.set_xticks(np.arange(nU) + 0.5)
    ax.set_xticklabels(ucs, rotation=45, ha='right')
    ax.set_yticks(np.arange(nD) + 0.5)
    ax.set_yticklabels(districts)
    ax.set_xlabel('UC Campus')
    ax.set_ylabel('Community College District')
    ax.set_title(
        'Per-District UC Transfer by Course Group\n'
        '(vertical slices, colored by category)'
    )
    plt.tight_layout()

    out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'course_transfer_heatmap_colored.png'
    )
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close()


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
    Reads a district CSV file and returns:
      - district_name
      - DataFrame with columns [UC Name, counts, unarticulated_courses]
        where `unarticulated_courses` is a '\n'-joined list of
        "Group X: course1, course2, …" lines.
    """
    df = pd.read_csv(file_path)
    district_name = os.path.basename(file_path).replace('.csv', '').replace('_', ' ')
    
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

def create_heatmap(data):
    # --- detailed view with per-group lines ---
    plt.figure(figsize=(30, 80))
    detailed = data.pivot(index='District', columns='UC Name', values='unarticulated_courses')
    # blank → NaN so that isna()==True means "good" → green
    detailed = detailed.replace('', np.nan)
    status = detailed.isna().astype(int)

    sns.heatmap(
        status,
        cmap='RdYlGn',
        cbar=False,
        vmin=0,
        vmax=1,
        linewidths=1,
        linecolor='black',
        square=False,  # Allow rectangular cells
        annot=False
    )

    # overlay each cell's multi-line detail
    for i, district in enumerate(detailed.index):
        for j, uc in enumerate(detailed.columns):
            text = detailed.iat[i, j]
            if pd.notna(text):
                plt.text(
                    j + 0.5, i + 0.5,
                    text,
                    ha='center', va='center',
                    wrap=True, fontsize=8,
                    color='white', fontweight='bold'
                )

    plt.title('Detailed District Articulation (Green = OK, Red = Missing)', pad=20)
    plt.ylabel('Community College District')
    plt.xlabel('UC Campus')
    plt.xticks(rotation=30, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    detailed_out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'detailed_district_transfer_availability_heatmap.png'
    )
    plt.savefig(detailed_out, dpi=300, bbox_inches='tight')
    plt.close()

def create_group_frequency_graph(data):
    """
    Creates a segmented bar graph showing the frequency of each Group ID
    across UC campuses with simplified color scheme for related courses.
    """
    plt.figure(figsize=(15, 8))
    
    # Get unique UCs and Group IDs
    uc_names = data['UC Name'].unique()
    
    # Count Group ID frequencies for each UC
    uc_group_counts = {}
    for uc in uc_names:
        uc_data = data[data['UC Name'] == uc]
        group_counts = {}
        
        for _, row in uc_data.iterrows():
            if pd.notna(row['unarticulated_courses']):
                groups = row['unarticulated_courses'].split('\n')
                for group in groups:
                    if ':' in group:
                        group_id = group.split(':')[0].strip()
                        if group_id not in group_counts:
                            group_counts[group_id] = 0
                        group_counts[group_id] += 1
        
        uc_group_counts[uc] = group_counts
    
    # Get all unique Group IDs
    all_groups = set()
    for counts in uc_group_counts.values():
        all_groups.update(counts.keys())
    all_groups = sorted(list(all_groups))
    
    
    # Group courses by their color category
    color_grouped_courses = {category: [] for category in COURSE_GROUPS.keys()}
    ungrouped = []
    
    for group in all_groups:
        group_lower = group.lower()
        assigned = False
        for category, info in COURSE_GROUPS.items():
            if any(pattern in group_lower for pattern in info['patterns']):
                color_grouped_courses[category].append(group)
                assigned = True
                break
        if not assigned:
            ungrouped.append(group)
    
    # Calculate total counts and percentages for each category
    category_totals = {}
    total_unarticulated = 0
    
    for category, groups in color_grouped_courses.items():
        if not groups:
            continue
        category_total = 0
        for group in groups:
            for uc in uc_names:
                count = uc_group_counts[uc].get(group, 0)
                category_total += count
        category_totals[category] = category_total
        total_unarticulated += category_total
    
    # Add ungrouped total
    ungrouped_total = sum(
        uc_group_counts[uc].get(group, 0)
        for group in ungrouped
        for uc in uc_names
    )
    if ungrouped_total > 0:
        category_totals['Other'] = ungrouped_total
        total_unarticulated += ungrouped_total
    
    # Plot each category's groups together
    bottom = np.zeros(len(uc_names))
    for category, groups in color_grouped_courses.items():
        if not groups:  # Skip empty categories
            continue
        color = COURSE_GROUPS[category]['color']
        category_total = np.zeros(len(uc_names))
        
        # Combine all groups in the category
        for group in sorted(groups):
            heights = []
            for uc in uc_names:
                count = uc_group_counts[uc].get(group, 0)
                heights.append(count)
            category_total += heights
        
        # Calculate percentage for legend label
        percentage = (category_totals[category] / total_unarticulated) * 100
        label = f"{category.replace('_', ' ').title()} ({percentage:.1f}%)"
        
        # Plot the combined category
        plt.bar(uc_names, category_total, bottom=bottom, 
               label=label, color=color)
        bottom += category_total
    
    # Plot ungrouped courses last as a single category
    if ungrouped:
        ungrouped_total_heights = np.zeros(len(uc_names))
        for group in sorted(ungrouped):
            heights = []
            for uc in uc_names:
                count = uc_group_counts[uc].get(group, 0)
                heights.append(count)
            ungrouped_total_heights += heights
        
        percentage = (category_totals['Other'] / total_unarticulated) * 100
        plt.bar(uc_names, ungrouped_total_heights, bottom=bottom, 
               label=f"Other Courses ({percentage:.1f}%)", color='#CCCCCC')
    
    # Add total counts on top of each bar
    total_heights = bottom  # bottom now contains cumulative heights
    for i, uc in enumerate(uc_names):
        plt.text(i, total_heights[i], f'Total: {int(total_heights[i])}',
                ha='center', va='bottom')
    
    plt.title('Distribution of Unarticulated Course Groups by UC Campus')
    plt.xlabel('UC Campus')
    plt.ylabel('Number of Unarticulated Course Groups')
    plt.xticks(rotation=30, ha='right')
    plt.legend(title='Course Categories (% of Total)', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    # Save to course_analysis directory
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'group_frequency_analysis.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def main():
    # Directory containing the district CSV files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.normpath(os.path.join(script_dir, '../../district_csvs'))
    
    # Analyze all districts
    combined_data = analyze_all_districts(directory)
    
    # Create visualizations
    create_heatmap(combined_data)
    create_group_frequency_graph(combined_data)
    create_course_heatmap(combined_data, directory)

if __name__ == "__main__":
    main()