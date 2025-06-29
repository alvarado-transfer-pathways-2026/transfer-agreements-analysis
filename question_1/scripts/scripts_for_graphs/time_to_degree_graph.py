import matplotlib.pyplot as plt
import numpy as np

# --- Example time to degree values (edit as needed) ---
semester_time_to_degree = {
    "UCSD": 14.67,
    "UCSB": 14.67,
    "UCSC": 12,
    "UCLA": 18,
    "UCB": 11,
    "UCI": 14.67,
    "UCD": 9.33,
    "UCR": 16,
    "UCM": 16
}
quarter_time_to_degree = {
    "UCSD": 22,
    "UCSB": 22,
    "UCSC": 18,
    "UCLA": 27,
    "UCI": 22,
    "UCD": 14,
    "UCR": 24
    # UCB and UCM are not quarter, so not included
}

quarter_only = {uc: quarter_time_to_degree[uc] - semester_time_to_degree[uc] for uc in quarter_time_to_degree}

# --- Custom UC order: UCB and UCM first ---
uc_labels = ["UCB", "UCM"] + [uc for uc in semester_time_to_degree if uc not in ("UCB", "UCM")]
x = np.arange(len(uc_labels))
bar_width = 0.6

fig, ax = plt.subplots(figsize=(16, 8))

for i, uc in enumerate(uc_labels):
    sem_val = semester_time_to_degree[uc]
    bar_sem = ax.bar(
        i, sem_val, width=bar_width,
        color="#CF1818", label="Semester Equivalent" if i == 0 else "", zorder=2
    )
    qtr_val = quarter_only.get(uc, 0)
    if qtr_val > 0:
        bar_qtr = ax.bar(
            i, qtr_val, width=bar_width,
            bottom=sem_val, color="#D08B8B", hatch="//",
            label="Quarter Only Portion" if i == 0 else "", zorder=2
        )
    # Annotate solid bar (centered, vertical)
    ax.text(
        i, sem_val / 2, f"{sem_val:.2f}",
        ha='center', va='center', fontsize=14, color='black',
        rotation=90, zorder=3
    )
    # Annotate slashed bar (above, vertical)
    if qtr_val > 0:
        ax.text(
            i, sem_val + qtr_val + 0.3, f"{qtr_val:.2f}",
            ha='center', va='bottom', fontsize=14, color='black',
            rotation=90, zorder=3
        )

# Increase y-axis limit for more space above bars
ymax = max(
    (semester_time_to_degree[uc] + quarter_only.get(uc, 0)) for uc in uc_labels
)
ax.set_ylim(0, ymax * 1.18)

ax.set_xticks(x)
ax.set_xticklabels(uc_labels, fontsize=16)
ax.set_ylabel("Number of Courses", fontsize=18)
ax.set_xlabel("University of California", fontsize=18)
plt.title("Time to Degree After Transfer by UC", fontsize=22)
plt.tight_layout()
plt.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

plt.figtext(
    0.5, -0.05,
    "Slashed bars represent the portion of time to degree from the quarter system; solid bars are semester equivalents.",
    wrap=True, horizontalalignment='center', fontsize=14, color='gray'
)

plt.savefig("time_to_degree_stacked_by_uc.png", dpi=300, bbox_inches='tight')
plt.show()