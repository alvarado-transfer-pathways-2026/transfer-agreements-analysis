import os
import re
from collections import defaultdict
from urllib.parse import urlencode, urlparse, parse_qs, unquote

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

############################################################
# 1) Dictionary of UC IDs and EXACT 'Computer Science' labels
############################################################
uc_cs_labels = {
    7:   "CSE: Computer Science B.S.",            # UC San Diego
    46:  "Computer Science, B.S.",                # UC Riverside
    79:  "Electrical Engineering & Computer Sciences, B.S.", # UC Berkeley
    89:  "Computer Science B.S.",                 # UC Davis
    117: "Computer Science/B.S.",                 # UCLA
    120: "Computer Science, B.S.",                # UC Irvine
    128: "Computer Science, B.S.",                # UC Santa Barbara
    132: "Computer Science B.S.",                 # UC Santa Cruz
    144: "Computer Science and Engineering, B.S. " # UC Merced
}

uc_names = {
    7: "University of California San Diego",
    46: "University of California Riverside",
    79: "University of California Berkeley",
    89: "University of California Davis",
    117: "University of California Los Angeles",
    120: "University of California Irvine",
    128: "University of California Santa Barbara",
    132: "University of California Santa Cruz",
    144: "University of California Merced",
}

# Keep the scrape pinned to one academic cycle by design.
# 2025-2026 is expected to map to id 76 on ASSIST.
ACADEMIC_YEAR_ID = 76


def _normalize_label(text):
    """Lowercase + strip punctuation/spacing for robust comparisons."""
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _is_plausible_cs_label(label):
    """Broad filter for CS major labels when exact matching fails."""
    l = (label or "").lower()
    return "computer science" in l or "computer sciences" in l


def _score_cs_label(label):
    """
    Rank fallback candidates.
    Higher score = more likely to be the intended CS bachelor's agreement.
    """
    l = (label or "").lower()
    score = 0
    if "computer science" in l or "computer sciences" in l:
        score += 10
    if any(token in l for token in [" b.s", "b.s.", " bs", "bachelor"]):
        score += 3
    if any(token in l for token in ["minor", "certificate", "master", "m.s", "ph.d"]):
        score -= 5
    return score


def _normalize_ws(text):
    return " ".join((text or "").split())


def _create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def _pairs_by_uc_from_existing_agreements(agreements_dir="cc_agreements"):
    """
    Uses existing cc_agreements/*/agreements.txt as the roster of valid CC<->UC pairs.
    Returns {uc_id: {cc_name: cc_id}}.
    """
    pairs_by_uc = defaultdict(dict)

    if not os.path.isdir(agreements_dir):
        return pairs_by_uc

    for folder in sorted(os.listdir(agreements_dir)):
        agreement_file = os.path.join(agreements_dir, folder, "agreements.txt")
        if not os.path.isfile(agreement_file):
            continue

        cc_name = folder.replace("_", " ").replace("-", "/")
        with open(agreement_file, "r", encoding="utf-8") as fh:
            for line in fh:
                if ":" not in line:
                    continue
                _, url = line.split(":", 1)
                url = url.strip()
                if not url.startswith("http"):
                    continue

                q = parse_qs(urlparse(url).query)
                try:
                    cc_id = int(q.get("institution", [None])[0])
                    uc_id = int(q.get("agreement", [None])[0])
                except (TypeError, ValueError):
                    continue

                pairs_by_uc[uc_id][cc_name] = cc_id

    return pairs_by_uc


def _select_best_major_anchor(anchors, desired_label):
    """
    Picks the best major row:
    1) Exact label match
    2) Normalized exact match
    3) Highest-scoring CS-like candidate
    """
    rows = []
    for a in anchors:
        text = _normalize_ws(a.text)
        if text:
            rows.append((a, text))

    for a, text in rows:
        if text == desired_label:
            return a, text

    desired_norm = _normalize_label(desired_label)
    for a, text in rows:
        if _normalize_label(text) == desired_norm:
            return a, text

    cs_rows = [(a, text) for a, text in rows if _is_plausible_cs_label(text)]
    if not cs_rows:
        return None, None

    best_anchor, best_text = max(cs_rows, key=lambda item: _score_cs_label(item[1]))
    return best_anchor, best_text


def find_computer_science_key(driver, cc_id, uc_id, year=ACADEMIC_YEAR_ID):
    """
    Opens ASSIST major list page and clicks the CS major row to get live viewByKey.
    Returns full viewByKey string (e.g., '76/113/to/7/Major/<uuid>') or None.
    """
    if uc_id not in uc_cs_labels:
        return None

    desired_label = uc_cs_labels[uc_id]
    params = {
        "year": year,
        "institution": cc_id,
        "agreement": uc_id,
        "agreementType": "to",
        "viewAgreementsOptions": "true",
        "view": "agreement",
        "viewBy": "major",
        "viewSendingAgreements": "false",
    }
    url = f"https://assist.org/transfer/results?{urlencode(params)}"

    wait = WebDriverWait(driver, 30)
    driver.get(url)
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".viewByRow a")))
    anchors = driver.find_elements(By.CSS_SELECTOR, ".viewByRow a")
    target, used_label = _select_best_major_anchor(anchors, desired_label)
    if target is None:
        print(f"⚠️ Could not find CS major row for UC {uc_id} (CC {cc_id})")
        return None

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
    target.click()

    wait.until(lambda d: "viewByKey=" in d.current_url)
    q = parse_qs(urlparse(driver.current_url).query)
    raw_key = q.get("viewByKey", [None])[0]
    if not raw_key:
        print(f"⚠️ No viewByKey after selecting '{used_label}' for UC {uc_id} (CC {cc_id})")
        return None

    return unquote(raw_key)



############################################################
# 4) Build final articulation URL in correct format
############################################################
def build_articulation_url(year, cc_id, uc_id, key):
    """
    Builds the final articulation URL in the format:
      https://assist.org/transfer/results?year={year}&institution={cc_id}
        &agreement={uc_id}&agreementType=to&view=agreement&viewBy=major
        &viewSendingAgreements=false&viewByKey={key}
    """
    base_url = "https://assist.org/transfer/results"
    params = {
        "year": year,
        "institution": cc_id,
        "agreement": uc_id,
        "agreementType": "to",
        "viewAgreementsOptions": "true",
        "view": "agreement",
        "viewBy": "major",
        "viewSendingAgreements": "false",
        "viewByKey": key,
    }
    query_str = urlencode(params)
    return f"{base_url}?{query_str}"


############################################################
# 5) Generate & Save All CS URLs for a Single UC
############################################################
def generate_cs_urls_for_uc(uc_id, pairs_by_uc, driver, output_dir="cs_urls", year=ACADEMIC_YEAR_ID):
    """
    For a given UC, discovers one live CS viewByKey via Selenium (on a seed CC),
    then reuses the major UUID with each CC id to generate per-CC URL lines.

    The output file is placed inside output_dir. Each line has:
      CCName [tab] final_url
    """
    os.makedirs(output_dir, exist_ok=True)
    cc_map = pairs_by_uc.get(uc_id, {})
    if not cc_map:
        print(f"⚠️ No existing CC roster found for UC id {uc_id}; skipping")
        return

    uc_name = uc_names.get(uc_id, f"UC_{uc_id}")
    sorted_ccs = sorted(cc_map.items(), key=lambda pair: pair[0])
    seed_cc_name, seed_cc_id = sorted_ccs[0]
    base_key = find_computer_science_key(driver, seed_cc_id, uc_id, year=year)
    if not base_key:
        print(f"⚠️ Could not discover CS key for {uc_name} using seed CC {seed_cc_name}")
        return

    # key format: "<year>/<seed_cc>/to/<uc>/Major/<uuid>"
    parts = base_key.split("/")
    if len(parts) < 6:
        print(f"⚠️ Unexpected key format for {uc_name}: {base_key}")
        return
    key_uuid = parts[-1]

    # e.g. "University of California Los Angeles" => "University_of_California_Los_Angeles"
    uc_name_sanitized = uc_name.replace(" ", "_").replace(",", "")
    output_file = os.path.join(output_dir, f"cs_urls_{uc_name_sanitized}.txt")

    with open(output_file, "w", encoding="utf-8") as f:
        for cc_name, cc_id in sorted_ccs:
            cs_key = f"{year}/{cc_id}/to/{uc_id}/Major/{key_uuid}"
            final_url = build_articulation_url(year, cc_id, uc_id, cs_key)
            f.write(f"{cc_name}\t{final_url}\n")

    print(f"✅ Wrote {uc_name} Computer Science URLs to {output_file} ({len(sorted_ccs)} CCs)")


############################################################
# 6) Main: Generate for All UCs
############################################################
def main():
    """
    Build all Computer Science articulation URLs for each UC using
    existing CC<->UC roster and live Selenium key discovery.
    """
    pairs_by_uc = _pairs_by_uc_from_existing_agreements("cc_agreements")
    uc_ids = sorted([uc_id for uc_id in uc_cs_labels.keys() if uc_id in pairs_by_uc])
    if not uc_ids:
        print("❌ No CC/UC roster found from cc_agreements; cannot generate URLs.")
        return

    driver = _create_driver()
    try:
        for uc_id in uc_ids:
            generate_cs_urls_for_uc(
                uc_id,
                pairs_by_uc=pairs_by_uc,
                driver=driver,
                output_dir="cs_urls",
                year=ACADEMIC_YEAR_ID,
            )
    finally:
        driver.quit()

    print("Done generating Computer Science URLs for all UCs.")


if __name__ == "__main__":
    main()
