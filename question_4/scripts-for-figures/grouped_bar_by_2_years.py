#!/usr/bin/env python3
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION ===
json_path = "question_4/data/min_units/pathway_results_IGETC_20250810_154201.json"
exclude_ccs = ["de_anza", "foothill","mt_san_jacinto"]   # CC codes to exclude

# === LOAD DATA ===
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data["results"])
if df.empty:
    raise ValueError("No results in JSON.")
if "cc" not in df.columns or "over_2_years" not in df.columns:
    raise ValueError("JSON must include 'cc' and 'over_2_years' fields.")

# === FILTER OUT EXCLUDED CCs ===
print(f"Original dataset contains {len(df)} records from {df['cc'].nunique()} community colleges")
if exclude_ccs:
    df = df[~df["cc"].isin(exclude_ccs)].copy()
    print(f"Filtered dataset contains {len(df)} records from {df['cc'].nunique()} community colleges")

# === CALCULATE PERCENTAGES (per CC) ===
pct = (
    df.groupby("cc")["over_2_years"]
      .value_counts(normalize=True)
      .unstack(fill_value=0.0) * 100.0
)

# ensure both columns exist
if True not in pct.columns:  pct[True]  = 0.0
if False not in pct.columns: pct[False] = 0.0
pct = pct.rename(columns={False: "≤ 2 years", True: "> 2 years"})
pct = pct[["≤ 2 years", "> 2 years"]].sort_index()

# === PLOT (same grouped style as your example) ===
fig, ax = plt.subplots(figsize=(16, 8))

x = range(len(pct))
width = 0.4

ax.bar([i - width/2 for i in x], pct["≤ 2 years"].values, width, label="≤ 2 years")
ax.bar([i + width/2 for i in x], pct["> 2 years"].values, width, label="> 2 years")

ax.set_title("Percentage of Pathways Over 2 Years by CC")
ax.set_xlabel("Community College")
ax.set_ylabel("% of Pathways")
ax.set_xticks(list(x))
ax.set_xticklabels(pct.index, rotation=45, ha="right")
ax.legend(title="Duration")
ax.set_ylim(0, 100)

plt.tight_layout()

out_png = Path("cc_pathway_durations.png")
plt.savefig(out_png, dpi=300)
plt.show()

# === SUMMARY STATS ===
print("\nSummary Statistics:")
print(f"Number of CCs analyzed: {len(pct)}")
total_pathways = len(df)
over_2_years   = int(df["over_2_years"].sum())
under_2_years  = total_pathways - over_2_years
print(f"Total pathways analyzed: {total_pathways}")
print(f"Pathways ≤ 2 years: {under_2_years} ({under_2_years/total_pathways*100:.1f}%)")
print(f"Pathways > 2 years: {over_2_years} ({over_2_years/total_pathways*100:.1f}%)")

# extremes
cc_over_sorted = pct["> 2 years"].sort_values()
print(f"\nCC with lowest % over 2 years: {cc_over_sorted.index[0]} ({cc_over_sorted.iloc[0]:.1f}%)")
print(f"CC with highest % over 2 years: {cc_over_sorted.index[-1]} ({cc_over_sorted.iloc[-1]:.1f}%)")
print(f"\nSaved figure to: {out_png.resolve()}")
