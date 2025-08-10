import json
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION ===
# Path to your JSON file with results
json_path = "question_4/data/average_units/pathway_results_IGETC_20250809_145418.json"  # Change this to your file

# === MANUAL CC EXCLUSION ===
# Add the community college codes you want to exclude here
exclude_ccs = [
    "de_anza",
    "foothill"
]

# === LOAD DATA ===
with open(json_path, 'r') as f:
    data = json.load(f)

# Convert to DataFrame
df = pd.DataFrame(data['results'])

# === FILTER OUT EXCLUDED CCs ===
print(f"Original dataset contains {len(df)} records from {df['cc'].nunique()} community colleges")

if exclude_ccs:
    df_filtered = df[~df['cc'].isin(exclude_ccs)]
    excluded_count = len(df) - len(df_filtered)
    print(f"Excluded {excluded_count} records from {len(exclude_ccs)} community colleges: {exclude_ccs}")
    print(f"Filtered dataset contains {len(df_filtered)} records from {df_filtered['cc'].nunique()} community colleges")
else:
    df_filtered = df
    print("No community colleges excluded")

# === CALCULATE PERCENTAGES ===
# Count % of pathways over and under/equal 2 years by CC
cc_grouped = df_filtered.groupby('cc')['over_2_years'].value_counts(normalize=True).unstack(fill_value=0) * 100

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

# === SUMMARY STATS ===
print(f"\nSummary Statistics:")
print(f"Number of CCs analyzed: {len(cc_grouped)}")

# Calculate overall percentages
total_pathways = len(df_filtered)
over_2_years = df_filtered['over_2_years'].sum()
under_2_years = total_pathways - over_2_years

print(f"Total pathways analyzed: {total_pathways}")
print(f"Pathways ≤ 2 years: {under_2_years} ({under_2_years/total_pathways*100:.1f}%)")
print(f"Pathways > 2 years: {over_2_years} ({over_2_years/total_pathways*100:.1f}%)")

# Show CCs with highest/lowest percentages over 2 years
if '> 2 years' in cc_grouped.columns:
    cc_over_2_sorted = cc_grouped['> 2 years'].sort_values()
    print(f"\nCC with lowest % over 2 years: {cc_over_2_sorted.index[0]} ({cc_over_2_sorted.iloc[0]:.1f}%)")
    print(f"CC with highest % over 2 years: {cc_over_2_sorted.index[-1]} ({cc_over_2_sorted.iloc[-1]:.1f}%)")