import matplotlib.pyplot as plt
import numpy as np

# --- Example values (edit as needed) ---
transfer_courses = {
    "UCSD": 4.67,
    "UCSB": 4.67,
    "UCSC": 3.33,
    "UCLA": 4.67,
    "UCB": 4,
    "UCI": 3.33,
    "UCD": 5.33,
    "UCR": 3.33,
    "UCM": 5
}
after_time_to_degree = {
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

# --- Custom UC order: UCB and UCM first ---
uc_labels = ["UCB", "UCM"] + [uc for uc in after_time_to_degree if uc not in ("UCB", "UCM")]
x = np.arange(len(uc_labels))
bar_width = 0.6

fig, ax = plt.subplots(figsize=(23, 13))  # Make the figure itself bigger

transfer_vals = [transfer_courses[uc] for uc in uc_labels]
after_vals = [after_time_to_degree[uc] for uc in uc_labels]
total_vals = [transfer_courses[uc] + after_time_to_degree[uc] for uc in uc_labels]

# Plot bottom (transferable courses)
bars_transfer = ax.bar(
    x, transfer_vals, width=bar_width,
    color="#091FAD", label="Transfer Requirements", zorder=2
)
# Plot top (after transfer courses)
bars_after = ax.bar(
    x, after_vals, width=bar_width,
    bottom=transfer_vals, color="#9BB1E7", label="Degree Requirements After Transfer", zorder=2
)

# Annotate inside each segment (vertical)
for i, (trans, after) in enumerate(zip(transfer_vals, after_vals)):
    # Transferable courses (centered in lower segment)
    ax.text(
        x[i], trans / 2, f"{trans:.2f}",
        ha='center', va='center', fontsize=25, color='white',
        rotation=90, zorder=3, fontweight = 'bold'
    )
    # After transfer courses (centered in upper segment)
    ax.text(
        x[i], trans + after / 2, f"{after:.2f}",
        ha='center', va='center', fontsize=25, color='white',
        rotation=90, zorder=3, fontweight = 'bold'
    )
    # Total (above the bar)
    ax.text(
        x[i], trans + after + 0.5, f"{trans + after:.2f}",
        ha='center', va='bottom', fontsize=25, color='black',
        rotation=0, zorder=3
    )

# Increase y-axis limit for more space above bars
ymax = max(total_vals)
ax.set_ylim(0, ymax * 1.18)

# Axis labels and title
ax.set_ylabel("Number of Courses", fontsize=35)
ax.set_xlabel("University of California", fontsize=35)
plt.title("CS and Math Degree Requirements", fontsize=50)

ax.set_xticks(x)
ax.set_xticklabels(uc_labels, fontsize=30)
ax.tick_params(axis='y', labelsize=28)

# Custom legend (remove duplicates)
handles, labels = ax.get_legend_handles_labels()
seen = set()
unique = []
for h, l in zip(handles, labels):
    if l and l not in seen:
        unique.append((h, l))
        seen.add(l)
ax.legend([h for h, l in unique], [l for h, l in unique], title="Degree Segment", fontsize=24, title_fontsize=26, loc='upper left')

# Optional: make the grid lines lighter and the layout tighter
plt.tight_layout()
plt.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

plt.savefig("time_to_degree_stacked_by_uc.png", dpi=300, bbox_inches='tight')
plt.show()