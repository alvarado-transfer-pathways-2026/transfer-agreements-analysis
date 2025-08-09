import json
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION ===
# Path to your JSON file with results
json_path = "question_4/data/average_units/pathway_results_IGETC_20250809_145418.json"  # Change this to your file

# === LOAD DATA ===
with open(json_path, 'r') as f:
    data = json.load(f)

# Convert to DataFrame
df = pd.DataFrame(data['results'])

# === CALCULATE PERCENTAGES ===
# Count % of pathways over and under/equal 2 years by CC
cc_grouped = df.groupby('cc')['over_2_years'].value_counts(normalize=True).unstack(fill_value=0) * 100

# Rename columns for clarity
cc_grouped = cc_grouped.rename(columns={False: '≤ 2 years', True: '> 2 years'})

# === PLOT ===
ax = cc_grouped.plot(kind='bar', figsize=(10,6))
ax.set_ylabel('% of Pathways')
ax.set_xlabel('Community College')
ax.set_title('Percentage of Pathways Over 2 Years by CC')
ax.legend(title='Duration')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()

# Save plot as PNG
plt.savefig("cc_pathway_durations.png", dpi=300)

# Show plot
plt.show()
