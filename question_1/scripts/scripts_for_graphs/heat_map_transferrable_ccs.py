import argparse
import os

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set(style="white", font_scale=0.9)

UC_SCHOOLS = ["UCSD", "UCSB", "UCSC", "UCLA", "UCB", "UCI", "UCD", "UCR", "UCM"]


def create_order_heatmaps(csv_folder, output_dir, order_count=3):
    os.makedirs(output_dir, exist_ok=True)
    for order in range(1, order_count + 1):
        file_path = os.path.join(csv_folder, f"order_{order}_averages.csv")
        if not os.path.exists(file_path):
            continue
        df = pd.read_csv(file_path)
        df_filtered = df[~df["Community College"].isin(["AVERAGE", "TRANSFERABLE AVERAGE"])]
        df_filtered = df_filtered.sort_values("Community College")

        articulated_matrix = pd.DataFrame(index=df_filtered["Community College"], columns=UC_SCHOOLS)
        mask_matrix = pd.DataFrame(False, index=df_filtered["Community College"], columns=UC_SCHOOLS)

        for _, row in df_filtered.iterrows():
            cc = row["Community College"]
            for uc in UC_SCHOOLS:
                art_col = f"{uc} Articulated"
                unart_col = f"{uc} Unarticulated"
                articulated_matrix.loc[cc, uc] = row[art_col]
                if row[unart_col] > 0:
                    mask_matrix.loc[cc, uc] = True

        articulated_matrix = articulated_matrix.astype(float)
        fig, ax = plt.subplots(figsize=(14, max(6, len(articulated_matrix) * 0.4)))
        sns.heatmap(
            articulated_matrix,
            mask=mask_matrix,
            annot=True,
            fmt=".1f",
            cmap="YlGnBu",
            cbar_kws={"label": "Avg. Articulated Courses"},
            linewidths=0.5,
            linecolor="white",
            ax=ax,
        )

        for y in range(mask_matrix.shape[0]):
            for x in range(mask_matrix.shape[1]):
                if mask_matrix.iloc[y, x]:
                    ax.add_patch(
                        plt.Rectangle(
                            (x, y),
                            1,
                            1,
                            fill=True,
                            facecolor="lightcoral",
                            edgecolor="white",
                            linewidth=0.5,
                        )
                    )

        red_patch = mpatches.Patch(color="lightcoral", label="Untransferable")
        ax.legend(handles=[red_patch], loc="upper right", bbox_to_anchor=(1.15, 1.02))
        ax.set_title(f"Transferable Course Heatmap - Order {order}", fontsize=14, weight="bold")
        ax.set_xlabel("University of California", fontsize=11)
        ax.set_ylabel("Community College District", fontsize=11)
        plt.xticks(rotation=30, ha="right")
        plt.yticks(rotation=0)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"heatmap_order_{order}.png"), dpi=300)
        plt.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Generate Q1 order heatmaps.")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", "..", "..", ".."))
    parser.add_argument(
        "--csv-folder",
        default=os.path.join(repo_root, "question_1", "csvs", "order_3_csvs"),
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(repo_root, "question_1", "graphs", "heat_maps_per_order"),
    )
    parser.add_argument("--order-count", type=int, default=3)
    return parser.parse_args()


def main():
    args = parse_args()
    create_order_heatmaps(
        csv_folder=args.csv_folder,
        output_dir=args.output_dir,
        order_count=args.order_count,
    )


if __name__ == "__main__":
    main()
