import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import os

from helper import analyze_all_colleges

def create_heatmap(data):
    # --- detailed view with per-group lines ---
    plt.figure(figsize=(30, 85))
    detailed = data.pivot(index='College', columns='UC Name', values='unarticulated_courses')
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

    # overlay each cell’s multi-line detail
    for i, college in enumerate(detailed.index):
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

    plt.title('Detailed Articulation (Green = OK, Red = Missing)', pad=20)
    plt.ylabel('Community College')
    plt.xlabel('UC Campus')
    plt.xticks(rotation=30, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    detailed_out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'detailed_transfer_availability_heatmap.png'
    )
    plt.savefig(detailed_out, dpi=300, bbox_inches='tight')
    plt.close()

def main():
    # Directory containing the filtered CSV files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.normpath(os.path.join(script_dir, '../../filtered_results'))
    
    # Analyze all colleges
    combined_data = analyze_all_colleges(directory)
    
    # Create visualizations
    create_heatmap(combined_data)
    # create_bar_plot(combined_data)
    
    # Find college with fewest options
    total_options = combined_data.groupby('College')['counts'].sum()
    min_college = total_options.idxmin()
    min_count = total_options.min()
    
    # print(f"\nCollege with fewest valid UC transfer paths: {min_college}")
    # print(f"Number of UCs with all courses articulated: {min_count}")
    
    # # Show which UCs have all courses articulated and which courses are not articulated
    # college_data = combined_data[combined_data['College'] == min_college]
    # print(f"\nDetailed transfer information for {min_college}:")
    # for _, row in college_data.iterrows():
    #     if row['counts'] == 1:
    #         print(f"- {row['UC Name']}: All courses articulated")
    #     else:
    #         print(f"- {row['UC Name']}: Missing articulation for {row['unarticulated_courses']}")

if __name__ == "__main__":
    main()