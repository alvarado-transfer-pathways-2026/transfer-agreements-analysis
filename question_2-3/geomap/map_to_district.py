#!/usr/bin/env python3
# import math
import os, glob, json, ast
import pandas as pd
# from itertools import combinations

# def haversine_km(a, b):
#     lat1, lon1 = a
#     lat2, lon2 = b
#     R = 6371.0
#     φ1, φ2 = math.radians(lat1), math.radians(lat2)
#     Δφ = math.radians(lat2 - lat1)
#     Δλ = math.radians(lon2 - lon1)
#     h = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
#     return 2*R*math.asin(math.sqrt(h))

# --- locate your CSV ---
base = os.path.dirname(__file__)
csvs = glob.glob(os.path.join(base, "*.csv"))
if len(csvs) != 1:
    raise RuntimeError(f"Expected exactly one CSV in {base}, found: {csvs}")
df = pd.read_csv(csvs[0])

# --- auto-detect columns ---
cols = df.columns.tolist()
college_col = next((c for c in cols if "college" in c.lower()), None)
coords_col  = next((c for c in cols if "coord"   in c.lower()), None)
if not college_col or not coords_col:
    raise RuntimeError(f"Couldn't find columns. Found: {cols}")

# --- parse the coords list into a list of (lat,lon) points ---
def parse_coords(cell):
    try:
        data = json.loads(cell)
    except Exception:
        data = ast.literal_eval(cell)
    pts = []
    for trip in data:
        lon, lat = trip[0], trip[1]
        pts.append((lat, lon))
    return pts

df["pts"]    = df[coords_col].astype(str).map(parse_coords)
df["cc_lat"] = df["pts"].map(lambda pts: sum(p[0] for p in pts) / len(pts))
df["cc_lon"] = df["pts"].map(lambda pts: sum(p[1] for p in pts) / len(pts))

# --- load districts.json ---
districts_path = os.path.abspath(os.path.join(
    base, os.pardir, os.pardir,
    "creating_districts", "districts.json"))
if not os.path.exists(districts_path):
    raise FileNotFoundError(f"Can't find districts.json at {districts_path}")
with open(districts_path) as f:
    district_data = json.load(f)["districts"]

# --- verify district names match exactly ---
missing = [d for d in df[college_col].unique() if d not in district_data]
if missing:
    raise RuntimeError(f"No entries in districts.json for: {missing}")

# --- build GeoJSON of district centroids ---
features = []
for dist_name, grp in df.groupby(college_col):
    mean_lat = grp["cc_lat"].mean()
    mean_lon = grp["cc_lon"].mean()

    feat = {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [mean_lon, mean_lat]
      },
      "properties": {
        "district": dist_name,
        "region": district_data[dist_name].get("region")
      }
    }
    features.append(feat)

out_fc = {"type": "FeatureCollection", "features": features}
out_path = os.path.join(base, "District_map.geojson")
with open(out_path, "w") as f:
    json.dump(out_fc, f, indent=2)

print(f"Wrote {len(features)} districts to {out_path}")
