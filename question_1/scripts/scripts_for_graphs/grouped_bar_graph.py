import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
import os

os.makedirs("question1/graphs", exist_ok=True)

# List of UC campuses
uc_schools = ["UCSD", "UCSB", "UCSC", "UCLA", "UCB", "UCI", "UCD", "UCR", "UCM"]

# Specify the folder containing the CSVs
csv_folder = "/Users/yasminkabir/transfer-agreements-analysis/question_1/csvs/order_4_csvs"

# Track which prefix was used for each order
order_sources = []

# Set the number of orders you expect (change to 6 if you only have 5 orders, etc.)
order_range = range(1, 5)

# Load and extract TRANSFERABLE AVERAGE row from each order CSV
order_dfs = []
for i in order_range:
    found = False
    for prefix in ["order", "greedy_order", "optimal_order"]:
        filename = f"{csv_folder}/{prefix}_{i}_averages.csv"
        try:
            df = pd.read_csv(filename)
            transferable_row = df[df["Community College"] == "TRANSFERABLE AVERAGE"]
            if not transferable_row.empty:
                transferable_row = transferable_row.copy()
                transferable_row.loc[:, "Order"] = f"Order {i}"  # Fix SettingWithCopyWarning
                order_dfs.append(transferable_row)
                order_sources.append(prefix)
                found = True
                break
        except FileNotFoundError:
            continue
    if not found:
        print(f"Neither order_{i}_averages.csv nor greedy_order_{i}_averages.csv nor optimal_order_{i}_averages.csv found in {csv_folder}, skipping.")

# Reformat into long-form for plotting
records = []
for df in order_dfs:
    order = df["Order"].values[0]
    for uc in uc_schools:
        art_col = f"{uc} Articulated"
        if art_col in df.columns:
            records.append({
                "UC": uc,
                "Order": order,
                "Average Courses": df[art_col].values[0]
            })

plot_df = pd.DataFrame(records)

if plot_df.empty:
    raise ValueError("No data loaded. Check your file paths and names.")

# Pivot to get each UC with average per order
pivot_df = plot_df.pivot(index="UC", columns="Order", values="Average Courses")

# --- Custom values for CS/Math Course Requirements ---
semester_values = {
    "UCSD": 4.67, #7 Quarter Courses
    "UCSB": 4.67, #7 Quarter Courses
    "UCSC": 3.33, #5 Quarter Courses
    "UCLA": 4.67, #7 Quarter Courses
    "UCB": 4,
    "UCI": 3.33, #5 Quarter Courses
    "UCD": 5.33, #8 Quarter Courses
    "UCR": 3.33, #5 Quarter Courses
    "UCM": 5
}
quarter_values = {
    "UCSD": 7,
    "UCSB": 7,
    "UCSC": 5,
    "UCLA": 7,
    "UCI": 5,
    "UCD": 8,
    "UCR": 5
    # UCB and UCM are not quarter, so not included
}
quarter_only = {uc: quarter_values[uc] - semester_values[uc] for uc in quarter_values}

# --- Custom UC order: UCB and UCM first ---
#uc_labels = ["UCB", "UCM"] + [uc for uc in semester_values if uc not in ("UCB", "UCM")]
uc_labels = ["UCD", "UCM", "UCSD", "UCSB", "UCLA", "UCB", "UCSC", "UCI", "UCR"]
x = np.arange(len(uc_labels))
n_orders = len(order_range)
total_bars = n_orders + 1  # 1 for CS/Math bar
bar_width = 0.8 / total_bars

fig, ax = plt.subplots(figsize=(20, 12))

# Calculate offsets so all bars are centered at each UC
offsets = np.linspace(-0.4 + bar_width/2, 0.4 - bar_width/2, total_bars)

# Plot the CS/Math Requirement stacked bar (always first in group)
for i, uc in enumerate(uc_labels):
    sem_val = semester_values[uc]
    qtr_val = quarter_only.get(uc, 0)
    # Solid bar
    bar_sem = ax.bar(
        x[i] + offsets[0], sem_val, width=bar_width,
        color="#FFD700", label="CS/Math Requirement" if i == 0 else "", zorder=2
    )
    # Slashed (quarter-only) bar, stacked
    if qtr_val > 0:
        bar_qtr = ax.bar(
            x[i] + offsets[0], qtr_val, width=bar_width,
            bottom=sem_val, color="#FFF8DC", hatch="//",
            label="", zorder=2  # No legend label
        )
    # Annotate total above the bar (vertical)
    if qtr_val > 0:
        ax.text(
            x[i] + offsets[0], sem_val + qtr_val + 0.1, f"{(sem_val + qtr_val):.2f}",
            ha='center', va='bottom', fontsize=20, color='black',
            rotation=90, zorder=3
        )
    else:
        ax.text(
            x[i] + offsets[0], sem_val + 0.1, f"{sem_val:.2f}",
            ha='center', va='bottom', fontsize=20, color='black',
            rotation=90, zorder=3
        )
    # Annotate solid bar (centered, vertical)
    ax.text(
        x[i] + offsets[0], sem_val / 2, f"{sem_val:.2f}",
        ha='center', va='center', fontsize=20, color='black',
        rotation=90, zorder=3
    )

# --- Consistent color scheme for orders (reverse) ---
order_cmap = cm.get_cmap('Blues', n_orders + 2)
order_colors = [order_cmap(n_orders + 1 - i) for i in range(n_orders)]  # reverse order

# Plot the rest of the grouped bars (orders)
for j, col in enumerate([f"Order {i}" for i in range(1, n_orders + 1)]):
    if col in pivot_df.columns:
        vals = pivot_df[col].loc[uc_labels]
        bar_order = ax.bar(
            x + offsets[j+1], vals, width=bar_width,
            color=order_colors[j], label=col, zorder=1
        )
        # Annotate values above grouped bars (orders) - vertical, black
        for i, val in enumerate(vals):
            ax.text(
                x[i] + offsets[j+1], val + 0.1, f"{val:.2f}",
                ha='center', va='bottom', fontsize=20, color='black',
                rotation=90, zorder=3 
                #,fontweight = 'bold'
            )

# Increase y-axis limit for more space above bars
ymax = 0
for i, uc in enumerate(uc_labels):
    sem_val = semester_values[uc]
    qtr_val = quarter_only.get(uc, 0)
    bar_tops = [sem_val + qtr_val]
    for j, col in enumerate([f"Order {k}" for k in range(1, n_orders + 1)]):
        if col in pivot_df.columns:
            bar_tops.append(pivot_df[col].loc[uc])
    ymax = max(ymax, max(bar_tops))
ax.set_ylim(0, ymax * 1.18)

# --- Custom UC order: UCB and UCM first ---
uc_labels = ["UCD", "UCM", "UCSD", "UCSB", "UCLA", "UCB", "UCSC", "UCI", "UCR"]
# Mapping for display names

uc_display_names = {
    "UCD": "UC1*",
    "UCM": "UC2",
    "UCSD": "UC3*",
    "UCSB": "UC4*",
    "UCLA": "UC5*",
    "UCB": "UC6",
    "UCSC": "UC7*",
    "UCI": "UC8*",
    "UCR": "UC9*"
}

# ... rest of your plotting code ...

# X-axis labels
ax.set_xticks(x)
ax.set_xticklabels([uc_display_names[uc] for uc in uc_labels], fontsize=30)
ax.tick_params(axis='y', labelsize=28)

# ---- Dynamic title based on sources ----
source_types = set(order_sources)
if source_types == {"order"}:
    source_str = "Standard"
elif source_types == {"greedy_order"}:
    source_str = "Greedy"
elif source_types == {"optimal_order"}:
    source_str = "Optimal"
else:
    pretty = {
        "order": "Standard",
        "greedy_order": "Greedy",
        "optimal_order": "Optimal"
    }
    used = [pretty[p] for p in sorted(source_types)]
    source_str = " & ".join(used)
plot_title = f"Transferable Courses by Order per UC"
#plt.title(plot_title, fontsize=50)
plt.ylabel("Average Articulated Courses", fontsize=35)
plt.xlabel("University of California", fontsize=35)
plt.tight_layout()

# Custom legend (remove duplicates, ensure all bars are present)
handles, labels = ax.get_legend_handles_labels()
seen = set()
unique = []
for h, l in zip(handles, labels):
    if l and l not in seen:
        unique.append((h, l))
        seen.add(l)
ax.legend([h for h, l in unique], [l for h, l in unique], title="Order/Requirement",
          loc='upper right', fontsize=22, title_fontsize=24)

# plt.figtext(Add commentMore actions
#     0.5, -0.05,
#     "Slashed bars represent the portion of time to degree from the quarter system; solid bars are semester equivalents.",Add commentMore actions
#     wrap=True, horizontalalignment='center', fontsize=14, color='gray'
# )

plt.savefig("transferable_averages_by_uc_all_orders.png", dpi=300, bbox_inches='tight')
plt.show()