import json
import pandas as pd
import matplotlib.pyplot as plt

# Replace this with the path to your JSON file
json_file_path = "question_4/12-units/los_angeles_pierce/los_angeles_pierce_IGETC_20250809_133042.json"

# Load JSON data from file
with open(json_file_path, 'r') as f:
    data = json.load(f)

# Extract the 'results' list
results = data.get("results", [])

# Convert to DataFrame
df = pd.DataFrame(results)

# If you want to filter for a specific cc_name (e.g., "chabot")
# Uncomment the following line if needed
# df = df[df["cc"] == "chabot"]

# Group by uc_count and compute average total_terms
avg_terms_by_uc_count = df.groupby("uc_count")["total_terms"].mean().reset_index()

# Plot the bar graph
plt.figure(figsize=(8,5))
plt.bar(avg_terms_by_uc_count["uc_count"], avg_terms_by_uc_count["total_terms"], color='skyblue')
plt.xlabel("Number of UCs Applied To (uc_count)")
plt.ylabel("Average Number of Terms (total_terms)")
plt.title(f"Average Total Terms by UC Count for CC: {data.get('cc_name', '')}")
plt.xticks(range(1, 10))  # Assuming uc_count is between 1 and 9
cc_name = data.get("cc_name", "unknown_cc").replace(" ", "_").lower()
output_file = f"{cc_name}_average_terms_by_uc_count.png"
plt.savefig(output_file, dpi=300, bbox_inches='tight')
plt.show()
