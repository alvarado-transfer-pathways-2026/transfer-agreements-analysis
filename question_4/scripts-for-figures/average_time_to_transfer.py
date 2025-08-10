import json
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION ===
json_path = "question_4/data/min_units/pathway_results_IGETC_20250809_145559.json"

# === MANUAL CC EXCLUSION ===
# Add the community college codes you want to exclude here
exclude_ccs = [
    "de_anza",
    "foothill"
]

# === LOAD DATA ===
with open(json_path, 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data['results'])

# Check total_terms column exists
if "total_terms" not in df.columns:
    raise ValueError("The JSON must contain a 'total_terms' field.")

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

# === CALCULATE AVERAGE TERMS ===
avg_terms = df_filtered.groupby('cc')['total_terms'].mean().sort_values()

# === PLOT ===
plt.figure(figsize=(10,6))
avg_terms.plot(kind='bar', color='skyblue', edgecolor='black')

plt.ylabel('Average Number of Terms')
plt.xlabel('Community College')
plt.title('Average Number of Terms to Transfer by CC')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()

# Save plot
plt.savefig("cc_avg_terms_transfer.png", dpi=300)

plt.show()

# === SUMMARY STATS ===
print(f"\nSummary Statistics:")
print(f"Number of CCs analyzed: {len(avg_terms)}")
print(f"Lowest average terms: {avg_terms.iloc[0]:.2f} ({avg_terms.index[0]})")
print(f"Highest average terms: {avg_terms.iloc[-1]:.2f} ({avg_terms.index[-1]})")
print(f"Overall average: {avg_terms.mean():.2f} terms")