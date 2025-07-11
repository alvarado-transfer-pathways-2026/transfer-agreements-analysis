import matplotlib.pyplot as plt
import seaborn as sns
import os

from helper import analyze_all_districts

def create_bar_plot(data):
    # Calculate total transfer options per district
    total_options = data.groupby('District')['counts'].sum().sort_values()
    
    # Create bar plot with increased figure size for better label spacing
    plt.figure(figsize=(20, 5))
    ax = total_options.plot(kind='bar')
    plt.title('Number of Valid UC Transfer Paths by Community College District')
    plt.xlabel('Community College District')
    plt.ylabel('Number of UCs with All Courses Articulated')
    
    # Rotate x-axis labels and adjust their position
    plt.xticks(rotation=90, ha='center')
    
    # Adjust layout to prevent label cutoff
    plt.subplots_adjust(bottom=0.2)
    plt.tight_layout()
    # Save to the same directory as the script
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'district_total_transfer_availability.png')
    plt.savefig(output_path)
    plt.close()

def create_simple_bar_plot(data):
    """
    Creates a simplified bar plot showing the distribution of how many UCs
    each district has complete articulation with.
    """
    # Calculate how many UCs each district has complete articulation with
    district_complete_counts = {}
    for district in data['District'].unique():
        district_data = data[data['District'] == district]
        complete_count = sum(district_data['counts'])
        district_complete_counts[district] = complete_count
    
    # Count frequency of each number of complete articulations (0-9 UCs)
    frequency = {i: 0 for i in range(10)}  # 0 to 9 UCs
    for count in district_complete_counts.values():
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
                ha='center', va='bottom', fontsize=14)
    
    # plt.title('Distribution of Complete UC Articulations per District', fontsize=24)
    plt.xlabel('Number of UCs with Complete Articulation', fontsize=20)
    plt.ylabel('Number of Districts', fontsize=20)
    plt.xticks(range(10), fontsize=16)
    plt.yticks(fontsize=16)

    # Save the plot
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'district_simple_total_transfer_availability.png'
    )
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def create_horizontal_heatmap(data):
    # Pivot the data for the heatmap - swap index and columns
    heatmap_data = data.pivot(index='UC Index', columns='District', values='counts')
    
    # Set font sizes
    # plt.rcParams.update({'font.size': 22})  # Increase base font size
    # Create a figure with adjusted size for flipped axes
    plt.figure(figsize=(40, 25))  # Swapped dimensions
    
    # Create heatmap with a different colormap to emphasize binary nature
    sns.heatmap(heatmap_data, annot=False, cbar=False, cmap=sns.color_palette(["white", "#1a237e"], as_cmap=True), fmt='g', vmin=0, vmax=1, linewidths=1, linecolor='black', square=True)
    # plt.title('Valid Transfer Paths to UCs by CC District', pad=20, fontsize=36)
    plt.ylabel('UC Campus', fontsize=36)  # Swapped labels
    plt.xlabel('Community College District', fontsize=36)
    
    # Adjust rotation for the new axis orientation
    plt.xticks(rotation=90, ha='center', fontsize=20)
    plt.yticks(rotation=0, fontsize=20)
    
    plt.tight_layout()
    # Save to the same directory as the script
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'district_transfer_availability_horizontal_heatmap.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def create_vertical_heatmap(data):
    # Pivot the data for the heatmap
    heatmap_data = data.pivot(index='District', columns='UC Index', values='counts')

    # Create a figure with larger size
    plt.figure(figsize=(10, 30))  # Increased height to accommodate all districts
    plt.rcParams.update({'font.size': 18})  # Increase base font size
    
    # Create heatmap with a different colormap to emphasize binary nature
    sns.heatmap(heatmap_data, annot=False, cbar=False, cmap=sns.color_palette(["white", "#1a237e"], as_cmap=True), fmt='g', vmin=0, vmax=1, linewidths=1, linecolor='black')
    plt.title('Valid Transfer Paths to UCs by District', pad=20, fontsize=30)
    plt.ylabel('Community College District', fontsize=30)
    plt.xlabel('UC Campus', fontsize=30)
    
    # Rotate x-axis labels and adjust their position
    plt.xticks(rotation=45, ha='right', fontsize=20)
    # Keep y-axis labels horizontal for better readability
    plt.yticks(rotation=0, fontsize=20)
    
    plt.tight_layout()
    # Save to the same directory as the script
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'district_transfer_availability_vertical_heatmap.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
def main():
    # Directory containing the district CSV files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.normpath(os.path.join(script_dir, '../../district_csvs'))
    
    # Analyze all districts
    combined_data = analyze_all_districts(directory)
    
    # Create visualizations
    
    create_bar_plot(combined_data)
    
    create_simple_bar_plot(combined_data)

    create_horizontal_heatmap(combined_data)

    create_vertical_heatmap(combined_data)

if __name__ == "__main__":
    main()