import matplotlib.pyplot as plt
import seaborn as sns
import os

from helper import analyze_all_colleges

def create_heatmap(data):
    # Pivot the data for the heatmap
    heatmap_data = data.pivot(index='College', columns='UC Name', values='counts')
    
    # Create a figure with larger size
    plt.figure(figsize=(10, 30))  # Increased height to accommodate all colleges
    
    # Create heatmap with a different colormap to emphasize binary nature
    sns.heatmap(heatmap_data, annot=True, cmap='RdYlGn', cbar=False, fmt='g', vmin=0, vmax=1, linewidths=1, linecolor='black')
    plt.title('Valid Transfer Paths to UCs\n(1=All courses articulated, 0=Some courses not articulated)', pad=20)
    plt.ylabel('Community College')
    plt.xlabel('UC Campus')
    
    # Rotate x-axis labels and adjust their position
    plt.xticks(rotation=30, ha='right')
    # Keep y-axis labels horizontal for better readability
    plt.yticks(rotation=0)
    
    plt.tight_layout()
    # Save to the same directory as the script
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'transfer_availability_heatmap.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def create_bar_plot(data):
    # Calculate total transfer options per college
    total_options = data.groupby('College')['counts'].sum().sort_values()
    
    # Create bar plot with increased figure size for better label spacing
    plt.figure(figsize=(20, 10))
    ax = total_options.plot(kind='bar')
    plt.title('Number of Valid UC Transfer Paths by Community College')
    plt.xlabel('Community College')
    plt.ylabel('Number of UCs with All Courses Articulated')
    
    # Rotate x-axis labels and adjust their position
    plt.xticks(rotation=90, ha='center')
    
    # Adjust layout to prevent label cutoff
    plt.subplots_adjust(bottom=0.2)
    plt.tight_layout()
    # Save to the same directory as the script
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'total_transfer_availability.png')
    plt.savefig(output_path)
    plt.close()

def create_simple_bar_plot(data):
    """
    Creates a simplified bar plot showing the distribution of how many UCs
    each complete has complete articulation with.
    """
    # Calculate how many UCs each college has complete articulation with
    college_complete_counts = {}
    for college in data['College'].unique():
        college_data = data[data['College'] == college]
        complete_count = sum(college_data['counts'])
        college_complete_counts[college] = complete_count
    
    # Count frequency of each number of complete articulations (0-9 UCs)
    frequency = {i: 0 for i in range(10)}  # 0 to 9 UCs
    for count in college_complete_counts.values():
        frequency[count] += 1
    
    # Create bar plot
    plt.figure(figsize=(12, 6))
    x = list(frequency.keys())
    y = list(frequency.values())
    
    bars = plt.bar(x, y)
    
    # Add value labels on top of each bar
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom')
    
    plt.title('Distribution of Complete UC Articulations per College')
    plt.xlabel('Number of UCs with Complete Articulation')
    plt.ylabel('Number of Colleges')
    plt.xticks(range(10))
    plt.yticks(range(0, 20, 2))
    # Save the plot
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'college_simple_total_transfer_availability.png'
    )
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def main():
    # Directory containing the filtered CSV files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.normpath(os.path.join(script_dir, '../../filtered_results'))
    
    # Analyze all colleges
    combined_data = analyze_all_colleges(directory)
    
    # Create visualizations
    create_heatmap(combined_data)
    create_bar_plot(combined_data)
    create_simple_bar_plot(combined_data)
    
    # Find college with fewest options
    # total_options = combined_data.groupby('College')['counts'].sum()
    # min_college = total_options.idxmin()
    # min_count = total_options.min()
    
    # print(f"\nCollege with fewest valid UC transfer paths: {min_college}")
    # print(f"Number of UCs with all courses articulated: {min_count}")
    
    # # Show which UCs have all courses articulated for the college with fewest options
    # college_data = combined_data[combined_data['College'] == min_college]
    # available_ucs = college_data[college_data['counts'] == 1]['UC Name'].tolist()
    # print(f"\nUCs with all courses articulated:")
    # for uc in available_ucs:
    #     print(f"- {uc}")

if __name__ == "__main__":
    main()