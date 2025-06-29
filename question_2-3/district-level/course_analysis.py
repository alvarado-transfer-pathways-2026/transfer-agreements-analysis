import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

from helper import analyze_all_districts, COURSE_GROUPS


def create_group_frequency_graph(data):
    """
    Creates a segmented bar graph showing the frequency of each Group ID
    across UC campuses with simplified color scheme for related courses.
    """
    plt.figure(figsize=(15, 8))
    
    # Get unique UCs and Group IDs
    uc_names = data['UC Name'].unique()
    
    # Count Group ID frequencies for each UC
    uc_group_counts = {}
    for uc in uc_names:
        uc_data = data[data['UC Name'] == uc]
        group_counts = {}
        
        for _, row in uc_data.iterrows():
            if pd.notna(row['unarticulated_courses']):
                groups = row['unarticulated_courses'].split('\n')
                for group in groups:
                    if ':' in group:
                        group_id = group.split(':')[0].strip()
                        if group_id not in group_counts:
                            group_counts[group_id] = 0
                        group_counts[group_id] += 1
        
        uc_group_counts[uc] = group_counts
    
    # Get all unique Group IDs
    all_groups = set()
    for counts in uc_group_counts.values():
        all_groups.update(counts.keys())
    all_groups = sorted(list(all_groups))
    
    
    # Group courses by their color category
    color_grouped_courses = {category: [] for category in COURSE_GROUPS.keys()}
    ungrouped = []
    
    for group in all_groups:
        group_lower = group.lower()
        assigned = False
        for category, info in COURSE_GROUPS.items():
            if any(pattern in group_lower for pattern in info['patterns']):
                color_grouped_courses[category].append(group)
                assigned = True
                break
        if not assigned:
            ungrouped.append(group)
    
    # Calculate total counts and percentages for each category
    category_totals = {}
    total_unarticulated = 0
    
    for category, groups in color_grouped_courses.items():
        if not groups:
            continue
        category_total = 0
        for group in groups:
            for uc in uc_names:
                count = uc_group_counts[uc].get(group, 0)
                category_total += count
        category_totals[category] = category_total
        total_unarticulated += category_total
    
    # Add ungrouped total
    ungrouped_total = sum(
        uc_group_counts[uc].get(group, 0)
        for group in ungrouped
        for uc in uc_names
    )
    if ungrouped_total > 0:
        category_totals['Other'] = ungrouped_total
        total_unarticulated += ungrouped_total
    
    # Plot each category's groups together
    bottom = np.zeros(len(uc_names))
    for category, groups in color_grouped_courses.items():
        if not groups:  # Skip empty categories
            continue
        color = COURSE_GROUPS[category]['color']
        category_total = np.zeros(len(uc_names))
        
        # Combine all groups in the category
        for group in sorted(groups):
            heights = []
            for uc in uc_names:
                count = uc_group_counts[uc].get(group, 0)
                heights.append(count)
            category_total += heights
        
        label = f"{category.replace('_', ' ').title()}"
        
        # Plot the combined category
        plt.bar(uc_names, category_total, bottom=bottom, 
               label=label, color=color)
        bottom += category_total
    
    # Plot ungrouped courses last as a single category
    # if ungrouped:
    #     ungrouped_total_heights = np.zeros(len(uc_names))
    #     for group in sorted(ungrouped):
    #         heights = []
    #         for uc in uc_names:
    #             count = uc_group_counts[uc].get(group, 0)
    #             heights.append(count)
    #         ungrouped_total_heights += heights
        
    #     percentage = (category_totals['Other'] / total_unarticulated) * 100
    #     plt.bar(uc_names, ungrouped_total_heights, bottom=bottom, 
    #            label=f"Other Courses ({percentage:.1f}%)", color='#CCCCCC')
    
    # Add total counts on top of each bar
    total_heights = bottom  # bottom now contains cumulative heights
    for i, uc in enumerate(uc_names):
        plt.text(i, total_heights[i], f'Total: {int(total_heights[i])}',
                ha='center', va='bottom')
    
    plt.title('Distribution of Unarticulated Course Groups by UC Campus')
    plt.xlabel('UC Campus')
    plt.ylabel('Number of Unarticulated Course Groups')
    plt.xticks(rotation=30, ha='right')
    plt.legend(title='Course Categories', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    # Save to course_analysis directory
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'course_frequency_analysis.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def create_normalized_group_graph(data):
    """
    Creates a 100%-stacked bar graph showing the relative composition
    of un-articulated course-group categories by UC campus, with
    percent labels on each segment.
    """
    import os
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from helper import COURSE_GROUPS

    # 1) Build per-campus/category raw counts
    uc_names = sorted(data['UC Name'].unique())
    categories = list(COURSE_GROUPS.keys())

    # initialize counters
    uc_category_counts = {
        uc: {cat: 0 for cat in categories}
        for uc in uc_names
    }

    # fill in counts
    for uc in uc_names:
        uc_data = data[data['UC Name'] == uc]
        for _, row in uc_data.iterrows():
            if pd.notna(row['unarticulated_courses']):
                for line in row['unarticulated_courses'].split('\n'):
                    if ':' not in line:
                        continue
                    gid = line.split(':', 1)[0].strip()
                    # map to a category or 'Other'
                    matched = False
                    for cat, info in COURSE_GROUPS.items():
                        if any(pat in gid.lower() for pat in info['patterns']):
                            uc_category_counts[uc][cat] += 1
                            matched = True
                            break
                    if not matched:
                        # optionally, handle new/unexpected groups
                        uc_category_counts[uc].setdefault('Other', 0)
                        uc_category_counts[uc]['Other'] += 1
                        if 'Other' not in categories:
                            categories.append('Other')
                            COURSE_GROUPS['Other'] = {'color': '#CCCCCC', 'patterns': []}

    # 2) build matrix and normalize each row to 100%
    counts = np.array([
        [uc_category_counts[uc][cat] for cat in categories]
        for uc in uc_names
    ], dtype=float)
    row_sums = counts.sum(axis=1, keepdims=True)
    percents = np.divide(counts, row_sums, where=row_sums>0) * 100

    # 3) plot
    fig, ax = plt.subplots(figsize=(15, 8))
    bottom = np.zeros(len(uc_names))

    for j, cat in enumerate(categories):
        heights = percents[:, j]
        bars = ax.bar(
            uc_names,
            heights,
            bottom=bottom,
            label=f"{cat.replace('_',' ').title()}",
            color=COURSE_GROUPS.get(cat, {'color':'#CCCCCC'})['color']
        )
        # annotate each segment with its percent
        for rect in bars:
            h = rect.get_height()
            if h > 0.5:  # only label segments big enough to read
                ax.text(
                    rect.get_x() + rect.get_width()/2,
                    rect.get_y() + h/2,
                    f"{h:.1f}%",
                    ha='center',
                    va='center',
                    fontsize=8,
                    color='white'
                )
        bottom += heights

    # axis labels, legend, etc.
    ax.set_title("100%-Stacked Composition of Un-articulated Groups by Campus")
    ax.set_ylabel("Percentage of Un-articulated Course Groups (%)")
    ax.set_xticks(np.arange(len(uc_names)))
    ax.set_xticklabels(uc_names, rotation=30, ha='right')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title='Course Categories')
    fig.tight_layout()

    # save
    out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'course_relative_frequency_analysis.png'
    )
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)

def create_per_course_graphs(data, output_dir):
    # --- Prep: campuses, categories, CC total count ---
    uc_names    = sorted(data['UC Name'].unique())
    categories  = list(COURSE_GROUPS.keys())
    n_districts = data['District'].nunique()  # denominator for percent calc

    os.makedirs(output_dir, exist_ok=True)

    # --- Build missing‐articulation counts ---
    uc_cat_counts = {
        uc: {cat: 0 for cat in categories}
        for uc in uc_names
    }
    for _, row in data.dropna(subset=['unarticulated_courses']).iterrows():
        uc = row['UC Name']
        for line in row['unarticulated_courses'].split('\n'):
            if ':' not in line:
                continue
            gid = line.split(':',1)[0].strip().lower()
            for cat, info in COURSE_GROUPS.items():
                if any(pat in gid for pat in info['patterns']):
                    uc_cat_counts[uc][cat] += 1
                    break

    # --- Now, per‐category plotting ---
    grey = '#DDDDDD'
    for cat in categories:
        # raw counts & percent
        counts   = np.array([uc_cat_counts[uc][cat] for uc in uc_names], dtype=float)
        percents = counts / n_districts * 100  # percent of CC districts missing articulation

        # decide bar heights & colors
        #  - if count>0: height = percents[i], color = real
        #  - if count==0: height = 100,       color = grey
        real_color = COURSE_GROUPS[cat]['color']
        heights    = np.where(counts>0, percents, 100.0)
        colors     = [real_color if c>0 else grey for c in counts]

        # plot
        fig, ax = plt.subplots(figsize=(8,5))
        bars = ax.bar(uc_names, heights, color=colors, edgecolor='k')

        # annotate only the coloured (required) ones with their % value
        for i,(bar,h,c) in enumerate(zip(bars, heights, counts)):
            if c > 0 and h > 5:  # only label segments big enough to read
                ax.text(
                    bar.get_x() + bar.get_width()/2,
                    h/2,
                    f"{percents[i]:.1f}%",
                    ha='center', va='center',
                    fontsize=8,
                    color='white'
                )

        # styling
        ax.set_ylim(0, 100)
        ax.set_title(f"{cat.replace('_',' ').title()}\n% of CC Districts Missing Articulation")
        ax.set_ylabel("% of All CC Districts")
        ax.set_xticks(np.arange(len(uc_names)))
        ax.set_xticklabels(uc_names, rotation=30, ha='right')

        # legend
        from matplotlib.patches import Patch
        legend_items = [
            Patch(facecolor=real_color, edgecolor='k', label='Has Gaps (required)'),
            Patch(facecolor=grey,       edgecolor='k', label='Not Required')
        ]
        ax.legend(handles=legend_items, loc='upper right', fontsize=8)

        plt.tight_layout()
        fn = os.path.join(output_dir, f"relative_{cat.lower().replace(' ','_')}.png")
        fig.savefig(fn, dpi=300, bbox_inches='tight')
        plt.close(fig)
        
def create_all_course_graphs(data, output_dir):
    """
    Draws a 2×3 grid of per-course, 100%-height bars where:
      • coloured bar = % of all CC districts missing articulation (if >0)
      • grey bar     = full 100% if 0 gaps (not required)
    """

    os.makedirs(output_dir, exist_ok=True)
    uc_names   = sorted(data['UC Name'].unique())
    categories = list(COURSE_GROUPS.keys())
    grey       = '#DDDDDD'
    n_districts = data['District'].nunique()

    # Build raw counts
    uc_cat_counts = { uc: {cat:0 for cat in categories} for uc in uc_names }
    for _, row in data.dropna(subset=['unarticulated_courses']).iterrows():
        uc = row['UC Name']
        for line in row['unarticulated_courses'].split('\n'):
            if ':' not in line:
                continue
            gid = line.split(':',1)[0].strip().lower()
            for cat, info in COURSE_GROUPS.items():
                if any(pat in gid for pat in info['patterns']):
                    uc_cat_counts[uc][cat] += 1
                    break

    # Create 2×3 grid
    fig, axes2d = plt.subplots(2, 3, figsize=(18, 10), sharey=True)
    axes = axes2d.flatten()

    for idx, (ax, cat) in enumerate(zip(axes, categories)):
        counts  = np.array([uc_cat_counts[uc][cat] for uc in uc_names], dtype=float)
        perc    = (counts / n_districts * 100).round(1)

        heights = [p if c > 0 else 100.0 for c, p in zip(counts, perc)]
        colors  = [
            COURSE_GROUPS[cat]['color'] if c > 0 else grey
            for c in counts
        ]

        bars = ax.bar(uc_names, heights, color=colors, edgecolor='k')

        # annotate only coloured bars
        for rect, c, p in zip(bars, counts, perc):
            if c > 0 and p > 5: 
                ax.text(
                    rect.get_x() + rect.get_width()/2,
                    p/2,
                    f"{p:.1f}%",
                    ha='center', va='center',
                    fontsize=8,
                    color='white'
                )

        ax.set_ylim(0, 100)
        ax.set_title(cat.replace('_',' ').title(), fontsize=20)
        ax.set_xticks(np.arange(len(uc_names)))
        ax.set_xticklabels(uc_names, rotation=20, ha='right')
        # only the leftmost column gets a ylabel
        if idx % 3 == 0:
            ax.set_ylabel("% of CC Districts", fontsize=20)

    # Shared title & legend
    fig.suptitle(
        "Per‐Course: % of CC Districts Missing Articulation",
        fontsize=24, y=0.9
    )
    from matplotlib.patches import Patch
    legend_items = [
        Patch(facecolor='black', edgecolor='k', label='Coloured = % missing'),
        Patch(facecolor=grey, edgecolor='k', label='Grey = not required')
    ]
    fig.legend(
        handles=legend_items,
        loc='lower center',
        ncol=2,
        frameon=False,
        fontsize=18,
        bbox_to_anchor=(0.5, -0.02)
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.92])
    out_path = os.path.join(output_dir, "all_courses_relative.png")
    fig.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def create_course_articulation_scatter(data, output_path):
    """
    Draws a 6×9 scatter‐matrix of courses vs. UC campuses.
    • Dot size ∝ percent of CC districts missing articulation (only for required courses).
    • Grey dots mark UC–course pairs with zero gaps (not required).
    """
    import os
    import numpy as np
    import matplotlib.pyplot as plt
    from helper import COURSE_GROUPS

    # 1) Prep
    uc_names   = sorted(data['UC Name'].unique())
    courses    = list(COURSE_GROUPS.keys())
    n_districts = data['District'].nunique()
    grey_color  = '#CCCCCC'
    base_size   = 800  # tweak for overall dot scale

    # 2) Compute missing‐counts
    uc_cat_counts = { uc: {cat:0 for cat in courses} for uc in uc_names }
    for _, row in data.dropna(subset=['unarticulated_courses']).iterrows():
        uc = row['UC Name']
        for line in row['unarticulated_courses'].split('\n'):
            if ':' not in line:
                continue
            gid = line.split(':',1)[0].strip().lower()
            for cat, info in COURSE_GROUPS.items():
                if any(pat in gid for pat in info['patterns']):
                    uc_cat_counts[uc][cat] += 1
                    break

    # 3) Build scatter data
    xs, ys, sizes, colors = [], [], [], []
    for i, cat in enumerate(courses):
        for j, uc in enumerate(uc_names):
            miss = uc_cat_counts[uc][cat]
            if miss > 0:
                pct = miss / n_districts  # fraction missing
                xs.append(j)
                ys.append(i)
                sizes.append(base_size * pct)
                colors.append(COURSE_GROUPS[cat]['color'])
            else:
                # not required → small grey dot
                xs.append(j)
                ys.append(i)
                sizes.append(base_size * 0.1)
                colors.append(grey_color)

    # 4) Plot
    fig, ax = plt.subplots(figsize=(12, 6))
    scatter = ax.scatter(xs, ys, s=sizes, c=colors, edgecolors='k', linewidth=0.3)

    # 5) Axes & labels
    ax.set_xticks(np.arange(len(uc_names)))
    ax.set_xticklabels(uc_names, rotation=45, ha='right')
    ax.set_yticks(np.arange(len(courses)))
    ax.set_yticklabels([c.replace('_',' ').title() for c in courses])
    ax.set_xlim(-0.5, len(uc_names)-0.5)
    ax.set_ylim(-0.5, len(courses)-0.5)

    ax.set_xlabel("UC Campus")
    ax.set_ylabel("Course Category")
    ax.set_title("Course Articulation Gaps: % of CC Districts Missing (dot size)")

    # 6) Legend for dot‐size + grey
    from matplotlib.lines import Line2D
    legend_elems = [
        Line2D([0], [0], marker='o', color='w', label='Not required',
               markerfacecolor=grey_color, markersize=5, markeredgecolor='k'),
        Line2D([0], [0], marker='o', color='w', label='20% missing',
               markerfacecolor='k', markersize=np.sqrt(base_size*0.2)/2),
        Line2D([0], [0], marker='o', color='w', label='50% missing',
               markerfacecolor='k', markersize=np.sqrt(base_size*0.5)/2),
    ]
    ax.legend(handles=legend_elems, title="Example dot sizes", 
              loc='lower right', fontsize=8, title_fontsize=9,
              frameon=False)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def main():
    # Directory containing the district CSV files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.normpath(os.path.join(script_dir, '../../district_csvs'))

    combined_data = analyze_all_districts(directory)

    create_group_frequency_graph(combined_data)
    create_normalized_group_graph(combined_data)
    create_per_course_graphs(combined_data, os.path.join(script_dir, 'per_course_analysis'))
    create_all_course_graphs(combined_data, os.path.join(script_dir, 'per_course_analysis'))
    create_course_articulation_scatter(combined_data, os.path.join(script_dir, 'course_articulation_scatter.png'))

if __name__ == "__main__":
    main()
