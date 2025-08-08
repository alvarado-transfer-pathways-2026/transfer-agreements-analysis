import json
import matplotlib.pyplot as plt
import numpy as np
import os
from collections import defaultdict

def load_and_process_data(json_file_path):
    """
    Load JSON data and process it to extract UC counts and terms information
    """
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    
    # Group data by UC count and collect terms for each group
    uc_count_to_terms = defaultdict(list)
    
    for result in data['results']:
        uc_count = result['uc_count']
        total_terms = result['total_terms']
        uc_count_to_terms[uc_count].append(total_terms)
    
    return uc_count_to_terms

def calculate_averages(uc_count_to_terms):
    """
    Calculate average terms for each UC count level
    """
    uc_counts = []
    avg_terms = []
    
    for uc_count in sorted(uc_count_to_terms.keys()):
        terms_list = uc_count_to_terms[uc_count]
        average = sum(terms_list) / len(terms_list)
        
        uc_counts.append(uc_count)
        avg_terms.append(average)
        
        print(f"UC Count {uc_count}: {len(terms_list)} pathways, Average terms: {average:.2f}")
    
    return uc_counts, avg_terms

def create_visualization(uc_counts, avg_terms):
    """
    Create the visualization showing UC count vs average terms
    """
    plt.figure(figsize=(12, 8))
    
    # Create the plot
    plt.plot(uc_counts, avg_terms, 'bo-', linewidth=2, markersize=8, alpha=0.7)
    
    # Add data point labels
    for i, (x, y) in enumerate(zip(uc_counts, avg_terms)):
        plt.annotate(f'{y:.2f}', (x, y), textcoords="offset points", 
                    xytext=(0,10), ha='center', fontsize=10)
    
    # Customize the plot
    plt.xlabel('Number of UCs Applied To', fontsize=14, fontweight='bold')
    plt.ylabel('Average Number of Terms Required', fontsize=14, fontweight='bold')
    plt.title('Computer Science Transfer Pathways:\nAverage Terms by Number of UCs Applied', 
              fontsize=16, fontweight='bold', pad=20)
    
    # Set x-axis to show all UC counts
    plt.xticks(uc_counts)
    
    # Add grid for better readability
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # Add some styling
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Set y-axis to start from a reasonable minimum
    y_min = min(avg_terms) - 0.1
    y_max = max(avg_terms) + 0.1
    plt.ylim(y_min, y_max)
    
    # Add a subtle background color
    plt.gca().set_facecolor('#f8f9fa')
    
    plt.tight_layout()
    return plt

def main():
    """
    Main function to run the analysis and create visualization
    """
    # Replace 'your_data.json' with the path to your JSON file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # json_file_path = os.path.join(project_root, 'data', 'chill_workload', 'sem-qtr_pathway_results_IGETC_20250808_102557.json')
    json_file_path = os.path.join(project_root, 'data', 'intense_workload', 'sem-qtr_pathway_results_IGETC_20250808_094422.json')

    print(f"Looking for data file at: {json_file_path}")
    print(f"File exists: {os.path.exists(json_file_path)}")
    try:
        # Load and process the data
        print("Loading and processing data...")
        uc_count_to_terms = load_and_process_data(json_file_path)
        
        # Calculate averages
        print("\nCalculating averages...")
        uc_counts, avg_terms = calculate_averages(uc_count_to_terms)
        
        # Create visualization
        print("\nCreating visualization...")
        plt = create_visualization(uc_counts, avg_terms)
        
        # save_dir = 'question_4/figures/chill_workload'
        save_dir = 'question_4/figures/intense_workload'
        os.makedirs(save_dir, exist_ok=True)
        
        save_path = os.path.join(save_dir, 'uc_transfer_analysis.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\nVisualization saved as '{save_path}'")
        
        # Print summary statistics
        print(f"\nSummary Statistics:")
        print(f"UC Count Range: {min(uc_counts)} - {max(uc_counts)}")
        print(f"Average Terms Range: {min(avg_terms):.2f} - {max(avg_terms):.2f}")
        print(f"Overall Average Terms: {sum(avg_terms)/len(avg_terms):.2f}")
        
    except FileNotFoundError:
        print(f"Error: Could not find file '{json_file_path}'")
        print("Please update the json_file_path variable with the correct path to your data file.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in the data file.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()