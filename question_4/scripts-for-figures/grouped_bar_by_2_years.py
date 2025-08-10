#!/usr/bin/env python3
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt

# --- Config ---
json_path = "question_4/data/max-units/pathway_results_IGETC_20250810_145038.json"

# CCs to exclude
exclude_ccs = ["de_anza", "foothill", "mt_san_jacinto"]

# --- Load data ---
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data["results"])

# --- Filter ---
print(f"Original dataset contains {len(df)} records from {df['cc'].nunique()} community colleges")
if exclude_ccs:
    df_filtered = df[~df["cc"].isin(exclude_ccs)].copy()
    excluded_count = len(df) - len(df_filtered)
    print(f"Excluded {excluded_count} records from {len(exclude_ccs)} community colleges: {exclude_ccs}")
    print(f"Filtered dataset contains {len(df_filtered)} records from {df_filtered['cc'].nunique()} community colleges")
else:
    df_filtered = df
    print("No community colleges excluded")

# --- Compute percentages per CC ---
cc_grouped = (
    df_filtered.groupby("cc")["over_2_years"]
    .value_counts(normalize=True)
    .unstack(fill_value=0) * 100
)

# Ensure both columns exist
if True not in cc_grouped.columns:
    cc_grouped[True] = 0.0
if False not in cc_grouped.columns:
    cc_grouped[False] = 0.0

cc_grouped = cc_grouped.rename(columns={False: "≤ 2 years", True: "> 2 years"})
cc_grouped = cc_grouped[["≤ 2 years", "> 2 years"]].sort_index()

# --- Plot (grouped bar) ---
plt.figure(figsize=(12, 6))
ax = cc_grouped.plot(kind="bar", width=0.85)  # grouped bars
ax.set_ylabel("Share of pathways (%)")
ax.set_xlabel("Community College")
ax.set_title("Pathway duration by CC (≤ 2 years vs > 2 years)")
ax.legend(title="Duration")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()

# Save then show
out_png = Path("cc_pathway_durations.png")
plt.savefig(out_png, dpi=300)
plt.show()

# --- Summary stats ---
print("\nSummary Statistics:")
print(f"Number of CCs analyzed: {len(cc_grouped)}")

total_pathways = len(df_filtered)
over_2_years = int(df_filtered["over_2_years"].sum())
under_2_years = total_pathways - over_2_years

print(f"Total pathways analyzed: {total_pathways}")
print(f"Pathways ≤ 2 years: {under_2_years} ({under_2_years/total_pathways*100:.1f}%)")
print(f"Pathways > 2 years: {over_2_years} ({over_2_years/total_pathways*100:.1f}%)")

if "> 2 years" in cc_grouped.columns:
    cc_over_2_sorted = cc_grouped["> 2 years"].sort_values()
    print(f"\nCC with lowest % over 2 years: {cc_over_2_sorted.index[0]} ({cc_over_2_sorted.iloc[0]:.1f}%)")
    print(f"CC with highest % over 2 years: {cc_over_2_sorted.index[-1]} ({cc_over_2_sorted.iloc[-1]:.1f}%)")

print(f"\nSaved figure to: {out_png.resolve()}")
