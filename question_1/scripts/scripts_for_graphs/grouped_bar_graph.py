import pandas as pd
import matplotlib.pyplot as plt

# List of UC campuses
uc_schools = ["UCSD", "UCSB", "UCSC", "UCLA", "UCB", "UCI", "UCD", "UCR", "UCM"]

# Specify the folder containing the CSVs
csv_folder = "/Users/yasminkabir/transfer-agreements-analysis/question_1/csvs/order_9_csvs"

# Track which prefix was used for each order
order_sources = []

# Set the number of orders you expect (change to 6 if you only have 5 orders, etc.)
order_range = range(1, 10)

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

# Add custom values as a new column (example values, replace with your own)
custom_values = {
    "UCSD": 7,
    "UCSB": 7,
    "UCSC": 5,
    "UCLA": 7,
    "UCB": 4,
    "UCI": 5,
    "UCD": 8,
    "UCR": 5,
    "UCM": 5
}
# Insert CS/Math Course Requirements as the first column
pivot_df.insert(0, "CS/Math Course Requirements", pd.Series(custom_values))

# Set up colors: first color for CS/Math, then tab10 for orders
colors = plt.get_cmap("tab10").colors
color_list = [(0.2, 0.2, 0.2)] + list(colors[:pivot_df.shape[1]-1])  # dark gray first, then tab10

# ---- Dynamic title based on sources ----
source_types = set(order_sources)
if source_types == {"order"}:
    source_str = "Standard"
elif source_types == {"greedy_order"}:
    source_str = "Greedy"
elif source_types == {"optimal_order"}:
    source_str = "Optimal"
else:
    # Mixed sources
    pretty = {
        "order": "Standard",
        "greedy_order": "Greedy",
        "optimal_order": "Optimal"
    }
    used = [pretty[p] for p in sorted(source_types)]
    source_str = " & ".join(used)

plot_title = f"Transferable Average Articulated Courses by UC and Order ({source_str} Orders) + CS/Math Course Requirements"

# Plot grouped bar chart with more space between groups and thicker bars
ax = pivot_df.plot(
    kind="bar",
    figsize=(32, 12),   # even wider and taller figure
    color=color_list,
    width=0.9          # narrower bars for more space between groups
)
plt.title(plot_title)
plt.ylabel("Average Articulated Courses")
plt.xlabel("University of California")
plt.xticks(rotation=0)
plt.tight_layout()

# Optionally, add more space on the sides
ax.set_xlim(-0.5, len(pivot_df)-0.5)

# Custom legend: match actual columns
handles, _ = ax.get_legend_handles_labels()
labels = list(pivot_df.columns)
ax.legend(handles, labels, title="Order/Requirement", bbox_to_anchor=(1.05, 1), loc='upper left')

# Annotate values above bars (larger font for clarity)
for container in ax.containers:
    ax.bar_label(container, fmt="%.1f", label_type="edge", padding=8, fontsize=14)  # more padding and bigger font

# Save the figure
plt.savefig("transferable_averages_by_uc_all_orders.png", dpi=300, bbox_inches='tight')

plt.show()