import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import os
import matplotlib.colors as mcolors

from district_indices import DISTRICT_INDICES
from helper import analyze_all_districts, COURSE_GROUPS, COURSE_CATEGORIES


def create_course_heatmap(data, directory):
    """
    Draw a grid of (district × UC) cells, each divided into
    six vertical slices (one per COURSE_CATEGORIES):
      • white if that UC never requires that category in this district
      • pale  if it is required & fully articulated (light version of category color)
      • solid if it is required but *not* fully articulated (full category color)
    Borders around each full cell are drawn in black for clarity.
    """

    # Helper to lighten a color
    def light(color, amount=1):
        """Return a lighter shade of the given color by mixing it with white."""
        rgb = np.array(mcolors.to_rgb(color))
        white = np.ones_like(rgb)
        mixed = rgb + (white - rgb) * amount
        return tuple(mixed)

    # 1) Build missing_lookup keyed by (district_idx, UC)
    missing_lookup = {}
    for _, row in data.iterrows():
        d_idx = row['District']
        uc = row['UC Name']
        raw = row['unarticulated_courses']
        gids = set()
        if isinstance(raw, str) and raw.strip():
            for line in raw.split("\n"):
                gid = line.split(":", 1)[0].strip()
                gids.add(gid)
        missing_lookup.setdefault((d_idx, uc), set()).update(gids)

    # 2) Build required_lookup keyed by (district_idx, UC)
    required_lookup = {}
    for fn in os.listdir(directory):
        if not fn.endswith('.csv'):
            continue
        dn = fn[:-4].replace('_', ' ')
        d_idx = DISTRICT_INDICES.get(dn)
        if d_idx is None:
            continue
        df = pd.read_csv(os.path.join(directory, fn))
        for uc, grp in df.groupby('UC Name')['Group ID']:
            required_lookup.setdefault((d_idx, uc), set()).update(grp.unique())

    # 3) Map raw Group ID -> category
    group_to_cat = {}
    for key in set().union(*required_lookup.values(), *missing_lookup.values()):
        low = key.lower()
        matched = None
        for cat, info in COURSE_GROUPS.items():
            if any(p in low for p in info['patterns']):
                matched = cat
                break
        group_to_cat[key] = matched

    # 4) Setup plot
    districts = sorted(data['District'].unique())
    ucs = sorted(data['UC Name'].unique())
    nD, nU = len(districts), len(ucs)
    fig, ax = plt.subplots(figsize=(nU * 1.2, nD * 0.6))
    ax.set_xlim(0, nU)
    ax.set_ylim(0, nD)
    ax.invert_yaxis()
    slice_w = 1.0 / len(COURSE_CATEGORIES)

    # 5) Draw vertical slices and cell borders
    for i, d_idx in enumerate(districts):
        for j, uc in enumerate(ucs):
            reqs = required_lookup.get((d_idx, uc), set())
            missing = missing_lookup.get((d_idx, uc), set())
            # draw each category slice
            for k, cat in enumerate(COURSE_CATEGORIES):
                gids_req = {g for g in reqs if group_to_cat.get(g) == cat}
                base_color = COURSE_GROUPS[cat]['color']
                if not gids_req:
                    face = 'white'
                elif gids_req & missing:
                    face = base_color  # solid: full category color
                else:
                    face = light(base_color, amount=0.5)  # pale: lightened color
                x0 = j + k * slice_w
                rect = plt.Rectangle(
                    (x0, i), slice_w, 1,
                    facecolor=face,
                    edgecolor='gray', linewidth=0.5
                )
                ax.add_patch(rect)
            # draw a bold border around the full cell
            border = plt.Rectangle(
                (j, i), 1, 1,
                fill=False,
                edgecolor='black', linewidth=1.5
            )
            ax.add_patch(border)

    # 6) Final formatting
    ax.set_xticks(np.arange(nU) + 0.5)
    ax.set_xticklabels(ucs, rotation=45, ha='right')
    ax.set_yticks(np.arange(nD) + 0.5)
    ax.set_yticklabels(districts)
    ax.set_xlabel('UC Campus')
    ax.set_ylabel('Community College District')
    ax.set_title(
        'Per-District UC Transfer by Course Group\n'
        '(vertical slices, colored by category)'
    )
    plt.tight_layout()

    out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'course_transfer_heatmap_colored.png'
    )
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close()


def create_heatmap(data):
    # --- detailed view with per-group lines ---
    plt.figure(figsize=(30, 80))
    detailed = data.pivot(index='District', columns='UC Name', values='unarticulated_courses')
    # blank → NaN so that isna()==True means "good" → green
    detailed = detailed.replace('', np.nan)
    status = detailed.isna().astype(int)

    sns.heatmap(
        status,
        cmap='RdYlGn',
        cbar=False,
        vmin=0,
        vmax=1,
        linewidths=1,
        linecolor='black',
        square=False,  # Allow rectangular cells
        annot=False
    )

    # overlay each cell's multi-line detail
    for i, district in enumerate(detailed.index):
        for j, uc in enumerate(detailed.columns):
            text = detailed.iat[i, j]
            if pd.notna(text):
                plt.text(
                    j + 0.5, i + 0.5,
                    text,
                    ha='center', va='center',
                    wrap=True, fontsize=8,
                    color='white', fontweight='bold'
                )

    plt.title('Detailed District Articulation (Green = OK, Red = Missing)', pad=20)
    plt.ylabel('Community College District')
    plt.xlabel('UC Campus')
    plt.xticks(rotation=30, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    detailed_out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'detailed_district_transfer_availability_heatmap.png'
    )
    plt.savefig(detailed_out, dpi=300, bbox_inches='tight')
    plt.close()

def main():
    # Directory containing the district CSV files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.normpath(os.path.join(script_dir, '../../district_csvs'))
    
    # Analyze all districts
    combined_data = analyze_all_districts(directory)
    
    # Create visualizations
    create_heatmap(combined_data)
    create_course_heatmap(combined_data, directory)

if __name__ == "__main__":
    main()