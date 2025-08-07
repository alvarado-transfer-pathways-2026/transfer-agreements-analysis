#!/usr/bin/env python3
import itertools
import json
import os
from pathlib import Path
from datetime import datetime

# Add pathway_generator folder to sys.path so we can import generate_pathway
import sys
sys.path.append(str(Path(__file__).resolve().parents[1] / "pathway_generator"))
from pathway_generator import (
    generate_pathway,
    ARTICULATION_DIR,
    PREREQS_DIR,
    COURSE_REQS_FILE,
    SUPPORTED_UCS,
)

# --- Config ---

TOP15_CCS = [
    "city_college_of_san_francisco",
    "cabrillo",
    "chabot",
    "los_angeles_pierce",
    "diablo_valley",
    "palomar",
    "folsom_lake",
    "foothill",
    "orange_coast",
    "mt_san_jacinto",
    "miracosta",
    "las_positas",
    "la_city",
    "cosumnes_river",
    "de_anza",
]

GE_PATTERNS = ["IGETC", "7CoursePattern"]

OUTPUT_ROOT = Path(__file__).resolve().parent / "pathway_runs"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

# Fix articulation filename typo for Cosumnes
ARTICULATION_FILENAME_OVERRIDES = {
    "cosumnes_river": "Cosumnes_River_College_articulation.json",
}

# Map CC -> prereq filename (matches prereq folder files)
PREREQ_FILES = {
    "cabrillo": "cabrillo_college_prereqs.json",
    "chabot": "chabot_college_prereqs.json",
    "city_college_of_san_francisco": "city_college_of_san_francisco_prereqs.json",
    "cosumnes_river": "cosumnes_river_college_prereqs.json",
    "de_anza": "de_anza_college_prereqs.json",
    "diablo_valley": "diablo_valley_prereqs.json",
    "folsom_lake": "folsom_lake_college_prereqs.json",
    "foothill": "foothill_college_prereqs.json",
    "la_city": "la_city_college_prereqs.json",
    "las_positas": "las_positas_college_prereqs.json",
    "los_angeles_pierce": "los_angeles_pierce_prereqs.json",
    "miracosta": "miracosta_college_prereqs.json",
    "mt_san_jacinto": "mt_san_jacinto_college_prereqs.json",
    "orange_coast": "orange_coast_college_prereqs.json",
    "palomar": "palomar_prereqs.json",
}

def articulation_path_for(cc_key: str) -> Path:
    if cc_key in ARTICULATION_FILENAME_OVERRIDES:
        fname = ARTICULATION_FILENAME_OVERRIDES[cc_key]
    else:
        # Find articulation file matching cc_key words heuristically
        candidates = list(ARTICULATION_DIR.glob("*_articulation.json"))
        parts = cc_key.replace("_", " ").split()
        for c in candidates:
            name = c.name.lower()
            if all(part in name for part in parts):
                return c
        raise FileNotFoundError(f"No articulation file found for {cc_key!r}")
    return ARTICULATION_DIR / fname

def prereq_path_for(cc_key: str) -> Path:
    fname = PREREQ_FILES.get(cc_key)
    if not fname:
        raise FileNotFoundError(f"No prereq mapping for {cc_key}")
    path = PREREQS_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"Prereq file not found: {path}")
    return path

def uc_slug(ucs):
    return "-".join(sorted(ucs))

def summarize_plan(plan):
    total_terms = len(plan)
    total_units = 0
    total_courses = 0
    for term in plan:
        total_courses += len(term.get("courses", []))
        for c in term.get("courses", []):
            total_units += int(c.get("units", 0))
    return total_terms, total_units, total_courses

def main():
    ge_json_path = PREREQS_DIR / "ge_reqs.json"
    if not ge_json_path.exists():
        raise FileNotFoundError(f"GE requirements file not found: {ge_json_path}")

    manifest_rows = []
    runs = 0

    for ge_pattern in GE_PATTERNS:
        print(f"Starting runs for GE pattern: {ge_pattern}")
        ge_out_dir = OUTPUT_ROOT / ge_pattern
        ge_out_dir.mkdir(parents=True, exist_ok=True)

        for cc in TOP15_CCS:
            cc_out_dir = ge_out_dir / cc
            cc_out_dir.mkdir(parents=True, exist_ok=True)

            art_path = articulation_path_for(cc)
            prereq_path = prereq_path_for(cc)

            for k in range(1, 10):  # UC subset sizes 1 to 9
                for uc_combo in itertools.combinations(SUPPORTED_UCS, k):
                    slug = uc_slug(uc_combo)
                    out_json = cc_out_dir / f"{cc}__{slug}.json"

                    if out_json.exists():
                        # Skip if already done
                        continue

                    try:
                        plan = generate_pathway(
                            art_path,
                            prereq_path,
                            ge_json_path,
                            COURSE_REQS_FILE,
                            cc,
                            list(uc_combo),
                            ge_pattern
                        )

                        with open(out_json, "w", encoding="utf-8") as f:
                            json.dump(plan, f, indent=2)

                        terms, units, courses = summarize_plan(plan)
                        manifest_rows.append([
                            cc,
                            ge_pattern,
                            ",".join(uc_combo),
                            terms,
                            units,
                            courses,
                            str(out_json.relative_to(OUTPUT_ROOT))
                        ])

                        runs += 1
                        print(f"[OK] {cc} | {ge_pattern} | {slug} -> {terms} terms, {units} units")

                    except Exception as e:
                        err_path = cc_out_dir / f"{cc}__{slug}__ERROR.txt"
                        err_path.write_text(str(e), encoding="utf-8")
                        manifest_rows.append([
                            cc,
                            ge_pattern,
                            ",".join(uc_combo),
                            "ERROR",
                            "ERROR",
                            "ERROR",
                            str(err_path.relative_to(OUTPUT_ROOT))
                        ])
                        print(f"[ERR] {cc} | {slug} | {ge_pattern}: {e}")

    # Write manifest.csv
    manifest_path = OUTPUT_ROOT / "manifest.csv"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("cc,ge_pattern,ucs,terms,total_units,total_courses,relative_path\n")
        for row in manifest_rows:
            f.write(",".join(map(str, row)) + "\n")

    print(f"\nDone. Completed {runs} new runs. Manifest saved to {manifest_path}")

if __name__ == "__main__":
    main()
