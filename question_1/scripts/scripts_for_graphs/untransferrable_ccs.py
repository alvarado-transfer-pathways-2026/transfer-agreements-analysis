import argparse
import os

import matplotlib.pyplot as plt

UC_LIST = ["UCSD", "UCSB", "UCSC", "UCLA", "UCB", "UCI", "UCD", "UCR", "UCM"]


def create_untransferable_plot(input_txt, output_file):
    counts = {uc: 0 for uc in UC_LIST}
    with open(input_txt, "r", encoding="utf-8") as f:
        for line in f:
            if ":" not in line:
                continue
            parts = line.strip().split(":", 1)
            if len(parts) != 2:
                continue
            uc_str = parts[1].strip()
            if not uc_str:
                continue
            for uc in [item.strip() for item in uc_str.split(",") if item.strip()]:
                if uc in counts:
                    counts[uc] += 1

    plt.figure(figsize=(10, 6))
    bars = plt.bar(counts.keys(), counts.values(), color="indianred")
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2.0, height + 0.2, str(height), ha="center", va="bottom")
    plt.title("Number of Districts Untransferable to Each UC")
    plt.xlabel("UC")
    plt.ylabel("Untransferable District Count")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Create untransferable district counts per UC.")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", "..", "..", ".."))
    parser.add_argument(
        "--input-txt",
        default=os.path.join(repo_root, "question_1", "csvs", "order_3_csvs", "transferable_cc_uc_pairs.txt"),
    )
    parser.add_argument(
        "--output-file",
        default=os.path.join(repo_root, "question_1", "graphs", "greedy_order_graphs", "untransferable_districts.png"),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    create_untransferable_plot(args.input_txt, args.output_file)


if __name__ == "__main__":
    main()
