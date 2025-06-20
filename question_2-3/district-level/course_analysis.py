import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os


from helper import analyze_all_districts, COURSE_GROUPS


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

    combined_data = analyze_all_districts(directory)

    create_group_frequency_graph(combined_data)

if __name__ == "__main__":
    main()
