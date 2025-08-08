import json
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION ===
json_path = "/Users/yasminkabir/GitHub/transfer-agreements-analysis-4/question_4/data/18_units_automation_results/pathway_results_IGETC_20250808_094422.json"

# === LOAD DATA ===
with open(json_path, 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data['results'])

# Check total_terms column exists
if "total_terms" not in df.columns:
    raise ValueError("The JSON must contain a 'total_terms' field.")

# === CALCULATE AVERAGE TERMS ===
avg_terms = df.groupby('cc')['total_terms'].mean().sort_values()

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
