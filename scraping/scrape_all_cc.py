import argparse
import os
import csv
import time
import traceback
import scraping  # Importing existing scraping functions

# Directories
AGREEMENTS_DIR = "cc_agreements"
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

def find_agreement_urls(cc_name):
    safe_cc_name = cc_name.replace(" ", "_").replace("/", "-")
    cc_folder = os.path.join(AGREEMENTS_DIR, safe_cc_name)
    agreement_file = os.path.join(cc_folder, "agreements.txt")

    if not os.path.exists(agreement_file):
        print(f"❌ No agreements found for '{cc_name}' at: {agreement_file}")
        return []

    urls = []
    with open(agreement_file, "r", encoding="utf-8") as file:
        for line in file:
            if ":" in line:
                parts = line.split(":", 1)
                uc_name = parts[0].strip()
                url = parts[1].strip()
                if url.startswith("http"):
                    urls.append((uc_name, url))
    return urls

def scrape_uc_data(uc_name, url):
    print(f"🔍 Scraping {uc_name} => {url}")
    for attempt in range(3):
        try:
            html = scraping.get_dynamic_html(url)
            return scraping.parse_articulations(html)
        except Exception as e:
            print(f"❌ Error scraping {uc_name} (Attempt {attempt+1}/3): {e}")
            traceback.print_exc()
            time.sleep(5)
    print(f"❌ Failed to scrape {uc_name} after 3 retries.")
    return None

# def process_sending_courses(sending_courses):
#     if sending_courses == "Not Articulated" or not sending_courses:
#         return ["Not Articulated"]
#     if isinstance(sending_courses, list) and all(isinstance(x, list) for x in sending_courses):
#         return ["; ".join(group) for group in sending_courses]
#     elif isinstance(sending_courses, list):
#         return ["; ".join(sending_courses)]
#     return [str(sending_courses)]

def write_csv(cc_name, all_rows):
    safe_cc_name = cc_name.replace(" ", "_").replace("/", "-")
    csv_path = os.path.join(RESULTS_DIR, f"{safe_cc_name}_allUC.csv")

    max_or_columns = max(len(row["OR Groups"]) for row in all_rows)

    headers = ["UC Campus", "CC", "UC Course Requirement"]
    for i in range(1, max_or_columns + 1):
        headers.append(f"Courses Group {i}")

    with open(csv_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        for row in all_rows:
            row_data = dict(row)
            or_groups = row_data.pop("OR Groups")
            for i in range(max_or_columns):
                row_data[f"Courses Group {i+1}"] = or_groups[i] if i < len(or_groups) else ""
            writer.writerow(row_data)

    print(f"✅ CSV saved: {csv_path}")

def load_existing_rows(cc_name):
    safe_cc_name = cc_name.replace(" ", "_").replace("/", "-")
    csv_path = os.path.join(RESULTS_DIR, f"{safe_cc_name}_allUC.csv")
    if not os.path.exists(csv_path):
        return []
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))

def merge_uc_rows(cc_name, uc_name, uc_rows):
    existing_rows = load_existing_rows(cc_name)
    merged_rows = [
        row
        for row in existing_rows
        if row.get("UC Campus", "").strip() != uc_name
    ]
    merged_rows.extend(uc_rows)
    write_csv(cc_name, normalize_rows_for_write(merged_rows))

def normalize_rows_for_write(rows):
    normalized = []
    for row in rows:
        if "OR Groups" in row:
            normalized.append(row)
            continue
        or_groups = [
            value.strip()
            for key, value in sorted(
                row.items(),
                key=lambda item: int(item[0].split()[-1]) if item[0].startswith("Courses Group") else 0,
            )
            if key.startswith("Courses Group") and value.strip()
        ]
        normalized.append(
            {
                "UC Campus": row.get("UC Campus", ""),
                "CC": row.get("CC", ""),
                "UC Course Requirement": row.get("UC Course Requirement", ""),
                "OR Groups": or_groups,
            }
        )
    return normalized

def rows_from_articulations(cc_name, uc_name, articulations):
    rows = []
    for record in articulations:
        receiving = record["Receiving"]
        sending = record["Sending"]
        rows.append(
            {
                "UC Campus": uc_name,
                "CC": cc_name,
                "UC Course Requirement": "; ".join(receiving),
                "OR Groups": scraping.process_sending_courses(sending),
            }
        )
    return rows

def process_all_ccs(*, cc_filter=None, uc_filter=None, limit=None):
    cc_folders = [f for f in os.listdir(AGREEMENTS_DIR) if os.path.isdir(os.path.join(AGREEMENTS_DIR, f))]
    if cc_filter:
        cc_folders = [
            folder
            for folder in cc_folders
            if folder.replace("_", " ").replace("-", "/") == cc_filter
        ]
    if limit:
        cc_folders = cc_folders[:limit]

    for index, folder in enumerate(cc_folders, start=1):
        cc_name = folder.replace("_", " ").replace("-", "/")
        print(f"\n📘 [{index}/{len(cc_folders)}] Processing: {cc_name}", flush=True)

        uc_urls = find_agreement_urls(cc_name)
        if uc_filter:
            uc_urls = [
                (uc_name, url)
                for uc_name, url in uc_urls
                if uc_name == uc_filter
            ]
        if not uc_urls:
            print(f"⚠️ Skipping {cc_name} due to missing URLs.")
            continue

        all_rows = []
        for uc_name, url in uc_urls:
            articulations = scrape_uc_data(uc_name, url)
            if not articulations:
                continue

            all_rows.extend(rows_from_articulations(cc_name, uc_name, articulations))

        if all_rows:
            if uc_filter:
                merge_uc_rows(cc_name, uc_filter, all_rows)
            else:
                write_csv(cc_name, all_rows)
        else:
            print(f"⚠️ No data extracted for {cc_name}.")

def main():
    parser = argparse.ArgumentParser(description="Scrape ASSIST articulation pages for all configured community colleges.")
    parser.add_argument("--cc", help="Only scrape one community college, e.g. 'Coastline Community College'.")
    parser.add_argument("--uc", help="Only scrape one UC campus name, e.g. 'University of California Davis'.")
    parser.add_argument("--limit", type=int, help="Only process the first N colleges, useful for smoke tests.")
    args = parser.parse_args()

    process_all_ccs(cc_filter=args.cc, uc_filter=args.uc, limit=args.limit)

if __name__ == "__main__":
    main()
