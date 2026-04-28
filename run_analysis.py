import argparse
import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_UC_NAME_INDICES = {
    "UCD": "UC1*",
    "UCM": "UC2 ",
    "UCSD": "UC3*",
    "UCSB": "UC4*",
    "UCLA": "UC5*",
    "UCB": "UC6 ",
    "UCSC": "UC7*",
    "UCI": "UC8*",
    "UCR": "UC9*",
}

VALID_QUESTIONS = ("q1", "q2", "q3")


@dataclass
class AnalysisConfig:
    repo_root: Path
    year: str
    q1_k: int
    workers: int
    questions: tuple[str, ...]


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    parent = str(file_path.parent)
    inserted = False
    if parent not in sys.path:
        sys.path.insert(0, parent)
        inserted = True
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted and parent in sys.path:
            sys.path.remove(parent)
    return module


def summarize_q1(csv_dir: Path, year_label: str, order_count: int):
    rows = []
    for idx in range(1, order_count + 1):
        file_path = csv_dir / f"order_{idx}_averages.csv"
        if not file_path.exists():
            continue
        df = pd.read_csv(file_path)
        row = df[df["Community College"] == "TRANSFERABLE AVERAGE"]
        if row.empty:
            continue
        row = row.iloc[0]
        for uc in ["UCSD", "UCSB", "UCSC", "UCLA", "UCB", "UCI", "UCD", "UCR", "UCM"]:
            rows.append(
                {
                    "year": year_label,
                    "uc": uc,
                    "role": idx,
                    "articulated_avg": float(row[f"{uc} Articulated"]),
                    "unarticulated_avg": float(row[f"{uc} Unarticulated"]),
                }
            )
    return pd.DataFrame(rows)


def summarize_q2(combined_data: pd.DataFrame, year_label: str):
    ranking = (
        combined_data.groupby("District", as_index=False)["counts"]
        .sum()
        .rename(columns={"counts": "fully_articulated_uc_count"})
        .sort_values(["fully_articulated_uc_count", "District"], ascending=[True, True])
    )
    ranking["rank"] = np.arange(1, len(ranking) + 1)
    ranking["year"] = year_label
    return ranking[["year", "District", "rank", "fully_articulated_uc_count"]]


def summarize_q3(combined_data: pd.DataFrame, year_label: str, course_groups: dict):
    districts_total = combined_data["District"].nunique()
    rows = []
    for uc_name, uc_df in combined_data.groupby("UC Index"):
        category_to_districts = {cat: set() for cat in course_groups}
        category_to_occurrences = {cat: 0 for cat in course_groups}

        for _, row in uc_df.iterrows():
            raw = row["unarticulated_courses"]
            if not isinstance(raw, str) or not raw.strip():
                continue
            district_idx = int(row["District"])
            for line in raw.split("\n"):
                if ":" not in line:
                    continue
                group_id = line.split(":", 1)[0].strip().lower()
                for category, meta in course_groups.items():
                    if any(pattern in group_id for pattern in meta["patterns"]):
                        category_to_districts[category].add(district_idx)
                        category_to_occurrences[category] += 1
                        break

        for category in course_groups:
            impacted = len(category_to_districts[category])
            rows.append(
                {
                    "year": year_label,
                    "uc": uc_name,
                    "course_category": category,
                    "impacted_districts": impacted,
                    "pct_districts_impacted": round((impacted / districts_total) * 100, 2),
                    "missing_group_occurrences": category_to_occurrences[category],
                }
            )

    return pd.DataFrame(rows).sort_values(["uc", "impacted_districts"], ascending=[True, False])


def normalize_combined_data(combined_data: pd.DataFrame, helper_module) -> pd.DataFrame:
    df = combined_data.copy()
    if "UC Index" not in df.columns:
        if "UC Name" not in df.columns:
            raise ValueError("Combined district data missing both 'UC Index' and 'UC Name' columns.")
        uc_map = getattr(helper_module, "UC_NAME_INDICES", DEFAULT_UC_NAME_INDICES)
        df["UC Index"] = df["UC Name"].map(uc_map).fillna(df["UC Name"])
    return df


def parse_questions_arg(raw: str) -> tuple[str, ...]:
    parts = [part.strip().lower() for part in raw.split(",") if part.strip()]
    if not parts:
        raise argparse.ArgumentTypeError("At least one question must be provided.")

    invalid = [part for part in parts if part not in VALID_QUESTIONS]
    if invalid:
        raise argparse.ArgumentTypeError(
            f"Invalid questions {invalid}. Valid values are: {', '.join(VALID_QUESTIONS)}."
        )

    deduped: list[str] = []
    for part in parts:
        if part not in deduped:
            deduped.append(part)
    return tuple(deduped)


def run_script(script_path: Path, args: list[str] | None = None):
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    env = os.environ.copy()
    env.setdefault("MPLBACKEND", "Agg")
    mpl_cache = Path(os.environ.get("TMPDIR", "/tmp")) / "codex-mplconfig"
    mpl_cache.mkdir(parents=True, exist_ok=True)
    env["MPLCONFIGDIR"] = str(mpl_cache)
    subprocess.run(cmd, cwd=script_path.parent, check=True, env=env)


def run_pipeline(config: AnalysisConfig):
    root = config.repo_root
    output_dir = root / "analysis_outputs" / config.year.replace("-", "_")
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = set(config.questions)
    run_q1 = "q1" in selected
    run_q2 = "q2" in selected
    run_q3 = "q3" in selected

    district_helper = None
    if run_q2 or run_q3:
        district_helper = load_module(
            "district_helper",
            root / "question_2-3" / "district-level" / "helper.py",
        )

    district_generator = load_module(
        "district_generator",
        root / "creating_districts" / "creating_district_csvs.py",
    )
    district_generator.generate_district_csvs(
        input_folder=str(root / "filtered_results"),
        output_folder=str(root / "district_csvs"),
        districts_json_path=str(root / "creating_districts" / "districts.json"),
    )

    q1_output_dir = root / "question_1" / "csvs" / "order_3_csvs"
    if run_q1:
        run_script(
            root / "question_1" / "scripts" / "scripts_for_data" / "total_combination.py",
            [
                "--input-folder",
                str(root / "district_csvs"),
                "--output-dir",
                str(q1_output_dir),
                "--k",
                str(config.q1_k),
                "--workers",
                str(config.workers),
            ],
        )

        run_script(
            root / "question_1" / "scripts" / "scripts_for_graphs" / "grouped_bar_graph.py",
            [
                "--csv-folder",
                str(q1_output_dir),
                "--order-count",
                str(config.q1_k),
                "--output-file",
                str(root / "question_1" / "graphs" / "greedy_order_graphs" / "grouped_bar_transferable_averages_by_uc.png"),
            ],
        )
        run_script(
            root / "question_1" / "scripts" / "scripts_for_graphs" / "heat_map_transferrable_ccs.py",
            [
                "--csv-folder",
                str(q1_output_dir),
                "--order-count",
                str(config.q1_k),
                "--output-dir",
                str(root / "question_1" / "graphs" / "heat_maps_per_order"),
            ],
        )
        run_script(
            root / "question_1" / "scripts" / "scripts_for_graphs" / "untransferrable_ccs.py",
            [
                "--input-txt",
                str(q1_output_dir / "transferable_cc_uc_pairs.txt"),
                "--output-file",
                str(root / "question_1" / "graphs" / "greedy_order_graphs" / "untransferable_districts.png"),
            ],
        )

    if run_q2:
        run_script(root / "question_2-3" / "district-level" / "district_least_options.py")
        run_script(root / "question_2-3" / "district-level" / "detailed_district_least_options.py")
        run_script(root / "question_2-3" / "cc-level" / "least_options.py")
        run_script(root / "question_2-3" / "cc-level" / "detailed_least_options.py")

    if run_q3:
        run_script(root / "question_2-3" / "district-level" / "course_analysis.py")

    current_q1 = None
    current_q2 = None
    current_q3 = None
    if run_q1:
        current_q1 = summarize_q1(q1_output_dir, config.year, config.q1_k)
        if len(current_q1) != 9 * config.q1_k:
            raise ValueError("Q1 summary shape check failed.")

    if run_q2 or run_q3:
        assert district_helper is not None
        current_combined = district_helper.analyze_all_districts(str(root / "district_csvs"))
        current_combined = normalize_combined_data(current_combined, district_helper)
        if run_q2:
            current_q2 = summarize_q2(current_combined, config.year)
            if current_q2["District"].nunique() != 72:
                raise ValueError("Q2 district coverage check failed.")
            if not set(current_q2["fully_articulated_uc_count"].unique()).issubset(set(range(0, 10))):
                raise ValueError("Q2 transfer count check failed.")
        if run_q3:
            current_q3 = summarize_q3(current_combined, config.year, district_helper.COURSE_GROUPS)

    index_rows = []
    if run_q1:
        assert current_q1 is not None
        q1_file = output_dir / f"q1_uc_marginal_contribution_{config.year.replace('-', '_')}.csv"
        current_q1.to_csv(q1_file, index=False)
        index_rows.append({"artifact": "q1_summary", "path": str(q1_file)})

    if run_q2:
        assert current_q2 is not None
        q2_file = output_dir / f"q2_district_transfer_options_{config.year.replace('-', '_')}.csv"
        current_q2.to_csv(q2_file, index=False)
        index_rows.append({"artifact": "q2_summary", "path": str(q2_file)})

    if run_q3:
        assert current_q3 is not None
        q3_file = output_dir / f"q3_course_group_bottlenecks_{config.year.replace('-', '_')}.csv"
        current_q3.to_csv(q3_file, index=False)
        index_rows.append({"artifact": "q3_summary", "path": str(q3_file)})

    pd.DataFrame(index_rows).to_csv(output_dir / "results_index.csv", index=False)

    print(f"Analysis completed. Outputs in {output_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description="Run full 2025-2026 transfer analysis refresh.")
    parser.add_argument("--year", default="2025-2026")
    parser.add_argument(
        "--questions",
        type=parse_questions_arg,
        default=parse_questions_arg("q1,q2,q3"),
        help="Comma-separated subset of questions to run, e.g. q2,q3",
    )
    parser.add_argument("--q1-k", type=int, default=3)
    parser.add_argument("--workers", type=int, default=1)
    return parser.parse_args()


def main():
    args = parse_args()
    config = AnalysisConfig(
        repo_root=Path(__file__).resolve().parent,
        year=args.year,
        q1_k=args.q1_k,
        workers=args.workers,
        questions=args.questions,
    )
    run_pipeline(config)


if __name__ == "__main__":
    main()
