import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# === CONFIGURATION ===
json_12 = "question_4/data/min_units/pathway_results_IGETC_20250810_154201.json"    # 12 units (min full-time)
json_15 = "question_4/data/average_units/pathway_results_IGETC_20250810_125719.json" # 15 units (average)
json_18 = "question_4/data/max-units/pathway_results_IGETC_20250810_145038.json"     # 18 units (max)
out_png = "cc_avg_terms_transfer_GROUPED_18_15_12.png"

# === MANUAL CC EXCLUSION ===
exclude_ccs = ["de_anza", "foothill", "mt_san_jacinto"]

def load_avg_terms(json_path: str, exclude=None) -> pd.DataFrame:
    p = Path(json_path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data["results"])
    if "total_terms" not in df.columns:
        raise ValueError(f"{p} missing 'total_terms'")

    if exclude:
        df = df[~df["cc"].isin(exclude)]

    out = (
        df.groupby("cc", as_index=False)["total_terms"]
          .mean()
    )
    return out

# --- load & merge ---
df12 = load_avg_terms(json_12, exclude_ccs).rename(columns={"total_terms": "u12"})
df15 = load_avg_terms(json_15, exclude_ccs).rename(columns={"total_terms": "u15"})
df18 = load_avg_terms(json_18, exclude_ccs).rename(columns={"total_terms": "u18"})

merged = df18.merge(df15, on="cc", how="outer").merge(df12, on="cc", how="outer")

# Sort CCs (keep your original behavior: rank by 15u if present, else 18u, else 12u)
sort_key = merged["u15"].fillna(merged["u18"]).fillna(merged["u12"])
merged = merged.assign(_sort=sort_key).sort_values("_sort").drop(columns="_sort")
merged["cc_label"] = merged["cc"].str.replace("_", " ")

# --- plot: grouped bars in order 18, 15, 12 ---
x = np.arange(len(merged))
width = 0.25

fig, ax = plt.subplots(figsize=(12, 7))

# brighter colors
col18 = "tab:orange"  # 18u
col15 = "tab:blue"    # 15u
col12 = "tab:red"     # 12u

# Colors inspired by image: Teal, Red, Yellow
bars18 = ax.bar(x - width, merged["u18"].values, width, label="18 units/term", color="#B5E81BD2", edgecolor="black",linewidth=1.8)
bars15 = ax.bar(x,          merged["u15"].values, width, label="15 units/term", color="#43D5E9", edgecolor="black",linewidth=1.8)
bars12 = ax.bar(x + width,  merged["u12"].values, width, label="12 units/term", color="#FC9B2C", edgecolor="black",linewidth=1.8)

ax.set_ylabel("Average Number of Terms")
ax.set_xlabel("Community College")
ax.set_title("Average Terms to Transfer by CC (Grouped by Unit Cap)")
ax.set_xticks(x)
ax.set_xticklabels(merged["cc_label"], rotation=45, ha="right")
ymax = merged[["u12","u15","u18"]].stack().max()
ax.set_ylim(0, float(ymax) + 1)
ax.grid(axis="y", alpha=0.3)
# legend in ascending order of units (18, 15, 12)
ax.legend(handles=[bars18, bars15, bars12], title=None)

plt.tight_layout()
plt.savefig(out_png, dpi=300)
plt.show()

# --- summaries ---
def safe_stats(colname):
    col = merged[colname].dropna()
    if len(col) == 0:
        return "n/a"
    i_min = col.idxmin()
    i_max = col.idxmax()
    return (
        f"CCs: {len(col)} | "
        f"Lowest: {col.min():.2f} ({merged.loc[i_min, 'cc_label']}) | "
        f"Highest: {col.max():.2f} ({merged.loc[i_max, 'cc_label']}) | "
        f"Overall avg: {col.mean():.2f}"
    )

print("\nSummary (18 units):", safe_stats("u18"))
print("Summary (15 units):", safe_stats("u15"))
print("Summary (12 units):", safe_stats("u12"))
print(f"\nSaved plot → {out_png}")
