#!/usr/bin/env python3
import itertools
import json
from pathlib import Path
import sys

# Make pathway_generator importable
sys.path.append(str(Path(__file__).resolve().parents[1] / "pathway_generator"))
from pathway_generator import (
    generate_pathway,
    ARTICULATION_DIR,
    PREREQS_DIR,
    COURSE_REQS_FILE,
    SUPPORTED_UCS,
)

# -------------------- Config --------------------

# EXACT fifteen CC keys we'll run
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

# Run both patterns
GE_PATTERNS = ["IGETC", "7CoursePattern"]

# Where outputs go
OUTPUT_ROOT = Path(__file__).resolve().parent / "pathway_runs"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

# ---- Hardcoded articulation filenames (authoritative, no guessing) ----
# These MUST exactly match files in articulated_courses_json/
ARTICULATION_FILES = {
    "cabrillo": "Cabrillo_College_articulation.json",
    "chabot": "Chabot_College_articulation.json",
    "city_college_of_san_francisco": "City_College_Of_San_Francisco_articulation.json",
    "cosumnes_river": "Cosumnes_River_College_articulation.json",
    "de_anza": "De_Anza_College_articulation.json",
    "diablo_valley": "Diablo_Valley_College_articulation.json",
    "folsom_lake": "Folsom_Lake_College_articulation.json",
    "foothill": "Foothill_College_articulation.json",
    "la_city": "Los_Angeles_City_College_articulation.json",              # <- LA City
    "las_positas": "Las_Positas_College_articulation.json",
    "los_angeles_pierce": "Los_Angeles_Pierce_College_articulation.json",
    "miracosta": "MiraCosta_College_articulation.json",
    "mt_san_jacinto": "Mt._San_Jacinto_College_articulation.json",        # <- DOT after Mt.
    "orange_coast": "Orange_Coast_College_articulation.json",
    "palomar": "Palomar_College_articulation.json",
}

# ---- Prereq filenames (match prerequisites/ folder) ----
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

# -------------------- Helpers --------------------

def articulation_path_for(cc_id: str) -> Path:
    """Strictly map CC key to its articulation file; raise helpful errors if missing."""
    fname = ARTICULATION_FILES.get(cc_id)
    if not fname:
        raise FileNotFoundError(f"No articulation mapping for '{cc_id}'. Add it to ARTICULATION_FILES.")
    path = ARTICULATION_DIR / fname
    if not path.exists():
        # Helpful debug: show a few files from the folder
        sample = [p.name for p in list(ARTICULATION_DIR.glob('*_articulation.json'))[:10]]
        raise FileNotFoundError(
            f"Articulation file for '{cc_id}' not found at {path}.\n"
            f"Check punctuation/case. Example files: {sample} ..."
        )
    return path

def prereq_path_for(cc_id: str) -> Path:
    """Strictly map CC key to its prereq file; raise helpful errors if missing."""
    fname = PREREQ_FILES.get(cc_id)
    if not fname:
        raise FileNotFoundError(f"No prereq mapping for '{cc_id}'. Add it to PREREQ_FILES.")
    path = PREREQS_DIR / fname
    if not path.exists():
        sample = [p.name for p in list(PREREQS_DIR.glob('*.json'))]
        raise FileNotFoundError(
            f"Prereq file for '{cc_id}' not found at {path}.\n"
            f"Available in prerequisites/: {sample}"
        )
    return path

def uc_slug(ucs) -> str:
    return "-".join(sorted(ucs))

def summarize_plan(plan):
    terms = len(plan)
    units = 0
    courses = 0
    for term in plan:
        cs = term.get("courses", [])
        courses += len(cs)
        for c in cs:
            try:
                units += int(c.get("units", 0))
            except Exception:
                pass
    return terms, units, courses

# -------------------- Main --------------------

def main():
    ge_json_path = PREREQS_DIR / "ge_reqs.json"
    if not ge_json_path.exists():
        raise FileNotFoundError(f"GE requirements file not found: {ge_json_path}")

    manifest_rows = []
    runs = 0

    for ge_pattern in GE_PATTERNS:
        print(f"== GE pattern: {ge_pattern} ==")
        ge_out_dir = OUTPUT_ROOT / ge_pattern
        ge_out_dir.mkdir(parents=True, exist_ok=True)

        for cc in TOP15_CCS:
            cc_out_dir = ge_out_dir / cc
            cc_out_dir.mkdir(parents=True, exist_ok=True)

            art_path = articulation_path_for(cc)
            prereq_path = prereq_path_for(cc)

            for k in range(1, 10):  # UC subset sizes: 1..9
                size_dir = cc_out_dir / f"{k}UC"
                size_dir.mkdir(parents=True, exist_ok=True)

                for uc_combo in itertools.combinations(SUPPORTED_UCS, k):
                    slug = uc_slug(uc_combo)

                    # New organized location + legacy flat location (skip if either exists)
                    out_json = size_dir / f"{cc}__{slug}.json"
                    legacy_out_json = cc_out_dir / f"{cc}__{slug}.json"
                    if out_json.exists() or legacy_out_json.exists():
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
                        print(f"[OK] {cc} | {ge_pattern} | {k} UC | {slug} -> {terms} terms, {units} units")

                    except Exception as e:
                        err_path = size_dir / f"{cc}__{slug}__ERROR.txt"
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
                        print(f"[ERR] {cc} | {ge_pattern} | {k} UC | {slug}: {e}")

    # Write manifest.csv at OUTPUT_ROOT
    manifest_path = OUTPUT_ROOT / "manifest.csv"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("cc,ge_pattern,ucs,terms,total_units,total_courses,relative_path\n")
        for row in manifest_rows:
            f.write(",".join(map(str, row)) + "\n")

    print(f"\nDone. Completed {runs} new runs. Manifest saved to {manifest_path}")

if __name__ == "__main__":
    main()