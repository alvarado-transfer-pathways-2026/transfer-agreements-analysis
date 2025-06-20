import pandas as pd
import matplotlib.pyplot as plt

# List of UC campuses
uc_schools = ["UCSD", "UCSB", "UCSC", "UCLA", "UCB", "UCI", "UCD", "UCR", "UCM"]

# Specify the folder containing the CSVs
csv_folder = "/Users/yasminkabir/transfer-agreements-analysis/question_1/order_5_csvs"

# Load and extract TRANSFERABLE AVERAGE row from each order CSV (1 to 5)
order_dfs = []
for i in range(1, 10):
    try:
        df = pd.read_csv(f"{csv_folder}/order_{i}_averages.csv")
        transferable_row = df[df["Community College"] == "TRANSFERABLE AVERAGE"]
        if not transferable_row.empty:
            transferable_row["Order"] = f"Order {i}"
            order_dfs.append(transferable_row)
    except FileNotFoundError:
        print(f"order_{i}_averages.csv not found in {csv_folder}, skipping.")

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

# Plot grouped bar chart with wider bars
ax = pivot_df.plot(
    kind="bar",
    figsize=(16, 7),
    color=color_list,
    width=0.85  # wider bars for better label visibility
)
plt.title("Transferable Average Articulated Courses by UC and Order (All 5 Orders) + CS/Math Course Requirements")
plt.ylabel("Average Articulated Courses")
plt.xlabel("University of California")
plt.xticks(rotation=0)
plt.tight_layout()

# Custom legend: Orders and CS/Math Course Requirements
handles, labels = ax.get_legend_handles_labels()
labels = ["CS/Math Course Requirements"] + [f"Order {i}" for i in range(1, 6)]
ax.legend(handles, labels, title="Order/Requirement", bbox_to_anchor=(1.05, 1), loc='upper left')

# Annotate values above bars (larger font for clarity)
for container in ax.containers:
    ax.bar_label(container, fmt="%.1f", label_type="edge", padding=4, fontsize=12)

# Save the figure
plt.savefig("transferable_averages_by_uc_all_orders.png", dpi=300, bbox_inches='tight')

plt.show()