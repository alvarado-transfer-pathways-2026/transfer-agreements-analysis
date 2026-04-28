import argparse
import os

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import cm

UC_SCHOOLS = ["UCSD", "UCSB", "UCSC", "UCLA", "UCB", "UCI", "UCD", "UCR", "UCM"]
UC_LABEL_ORDER = ["UCD", "UCM", "UCSD", "UCSB", "UCLA", "UCB", "UCSC", "UCI", "UCR"]
UC_DISPLAY_NAMES = {
    "UCD": "UC1*",
    "UCM": "UC2",
    "UCSD": "UC3*",
    "UCSB": "UC4*",
    "UCLA": "UC5*",
    "UCB": "UC6",
    "UCSC": "UC7*",
    "UCI": "UC8*",
    "UCR": "UC9*",
}


def load_transferable_order_data(csv_folder, order_count):
    order_dfs = []
    for i in range(1, order_count + 1):
        found_df = None
        for prefix in ["order", "greedy_order", "optimal_order"]:
            filename = os.path.join(csv_folder, f"{prefix}_{i}_averages.csv")
            if os.path.exists(filename):
                df = pd.read_csv(filename)
                transferable_row = df[df["Community College"] == "TRANSFERABLE AVERAGE"]
                if not transferable_row.empty:
                    found_df = transferable_row.copy()
                    found_df.loc[:, "Order"] = f"Order {i}"
                    break
        if found_df is not None:
            order_dfs.append(found_df)
    return order_dfs


def create_grouped_bar_graph(csv_folder, output_file, order_count=3):
    order_dfs = load_transferable_order_data(csv_folder=csv_folder, order_count=order_count)
    if not order_dfs:
        raise ValueError(f"No transferable rows found in {csv_folder}")

    records = []
    for df in order_dfs:
        order = df["Order"].values[0]
        for uc in UC_SCHOOLS:
            art_col = f"{uc} Articulated"
            if art_col in df.columns:
                records.append(
                    {
                        "UC": uc,
                        "Order": order,
                        "Average Courses": df[art_col].values[0],
                    }
                )

    plot_df = pd.DataFrame(records)
    pivot_df = plot_df.pivot(index="UC", columns="Order", values="Average Courses")

    fig, ax = plt.subplots(figsize=(18, 8))
    x = range(len(UC_LABEL_ORDER))
    bar_width = 0.8 / order_count
    order_cols = [f"Order {i}" for i in range(1, order_count + 1) if f"Order {i}" in pivot_df.columns]
    colors = [cm.get_cmap("Blues", len(order_cols) + 2)(len(order_cols) + 1 - i) for i in range(len(order_cols))]

    for idx, order_col in enumerate(order_cols):
        vals = pivot_df[order_col].reindex(UC_LABEL_ORDER).fillna(0)
        offsets = [xi - 0.4 + bar_width / 2 + idx * bar_width for xi in x]
        bars = ax.bar(offsets, vals, width=bar_width, color=colors[idx], label=order_col)
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.05,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    ax.set_xticks(list(x))
    ax.set_xticklabels([UC_DISPLAY_NAMES[uc] for uc in UC_LABEL_ORDER], fontsize=12)
    ax.set_ylabel("Average Articulated Courses")
    ax.set_xlabel("University of California")
    ax.set_title("Transferable Average Articulated Courses by UC and Order")
    ax.legend(title="Order")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Create grouped bar chart from Q1 order CSV outputs.")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", "..", "..", ".."))
    parser.add_argument(
        "--csv-folder",
        default=os.path.join(repo_root, "question_1", "csvs", "order_3_csvs"),
    )
    parser.add_argument(
        "--output-file",
        default=os.path.join(repo_root, "question_1", "graphs", "greedy_order_graphs", "grouped_bar_transferable_averages_by_uc.png"),
    )
    parser.add_argument("--order-count", type=int, default=3)
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    create_grouped_bar_graph(
        csv_folder=args.csv_folder,
        output_file=args.output_file,
        order_count=args.order_count,
    )


if __name__ == "__main__":
    main()
