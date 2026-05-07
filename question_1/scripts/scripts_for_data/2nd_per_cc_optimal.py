import pandas as pd
from itertools import permutations, combinations
import os
import math
from importlib import import_module

try:
	tqdm = import_module("tqdm").tqdm
except Exception:
	def tqdm(iterable, **kwargs):
		return iterable

uc_schools = ["UCSD", "UCSB", "UCSC", "UCLA", "UCB", "UCI", "UCD", "UCR", "UCM"]


def generate_combinations(uc_schools):
	# Change the number here for different permutation sizes
	return list(permutations(uc_schools, 3))


def get_roles(k):
	suffixes = ['st', 'nd', 'rd'] + ['th'] * 6
	return [f"{i+1}{suffixes[i] if i < 3 else 'th'}" for i in range(k)]


def get_requirement_options(df, combo):
	df.columns = df.columns.str.strip()
	df['UC Name'] = df['UC Name'].str.lower().str.strip()
	combo_lower = [uc.lower() for uc in combo]
	filtered_df = df[df['UC Name'].isin(combo_lower)]

	requirements = []
	course_options = {}
	uc_group_map = {}
	receiving_map = {}

	for (uc, group_id), group_df in filtered_df.groupby(['UC Name', 'Group ID']):
		uc_group_map.setdefault((uc, group_id), [])
		for set_id, set_df in group_df.groupby('Set ID'):
			for idx, row in set_df.iterrows():
				key = (uc, group_id, set_id, idx)
				uc_group_map[(uc, group_id)].append(key)
				options = set()
				for col in row.index:
					if col.lower().startswith("courses group"):
						val = str(row[col]).strip()
						if val and val.lower() != "not articulated" and val.lower() != "nan":
							options.update([v.strip() for v in val.split(';') if v.strip()])
				course_options[key] = options
				requirements.append(key)
				receiving = set([r.strip() for r in str(row['Receiving']).split(';') if r.strip()])
				receiving_map[key] = receiving
	return requirements, course_options, uc_group_map, receiving_map


def optimal_set_cover(requirements, course_options, time_limit=None):
	# Try MILP exact solver via pulp; if unavailable, fall back to greedy
	try:
		import pulp
	except Exception:
		# fallback: greedy selection
		course_to_reqs = {}
		for req in requirements:
			for c in course_options.get(req, set()):
				course_to_reqs.setdefault(c, set()).add(req)

		uncovered = set(requirements)
		req_to_course = {}
		selected = set()
		while uncovered:
			best_course = None
			best_cover = set()
			for course in sorted(course_to_reqs):
				cover = course_to_reqs[course] & uncovered
				if len(cover) > len(best_cover):
					best_course = course
					best_cover = cover
			if not best_course:
				break
			selected.add(best_course)
			for req in best_cover:
				req_to_course[req] = best_course
			uncovered -= best_cover
		return selected, req_to_course, set(r for r in requirements if r not in req_to_course)

	# Build course->requirements map
	from collections import defaultdict
	course_to_reqs = defaultdict(set)
	for req in requirements:
		for course in course_options.get(req, set()):
			course_to_reqs[course].add(req)

	all_courses = sorted(course_to_reqs.keys())
	if not all_courses:
		return set(), {}, set(requirements)

	model = pulp.LpProblem("OptimalSetCover", pulp.LpMinimize)
	x = pulp.LpVariable.dicts("x", all_courses, cat="Binary")

	model += pulp.lpSum(x[c] for c in all_courses)

	# cover constraints for requirements that have options
	for req in requirements:
		options = sorted(course_options.get(req, set()))
		if not options:
			continue
		model += pulp.lpSum(x[c] for c in options) >= 1

	solver = pulp.PULP_CBC_CMD(msg=False)
	status = model.solve(solver)
	if pulp.LpStatus[status] != "Optimal":
		return set(), {}, set(requirements)

	selected_courses = {c for c in all_courses if pulp.value(x[c]) > 0.5}
	req_to_course = {}
	for req in requirements:
		for course in sorted(course_options.get(req, set())):
			if course in selected_courses:
				req_to_course[req] = course
				break

	uncovered = {req for req in requirements if req not in req_to_course}
	return selected_courses, req_to_course, uncovered


def get_course_name_sets(articulated_courses, unarticulated_courses):
	articulated_names = {course for (_, course) in articulated_courses}
	unarticulated_names = {course for (_, course) in unarticulated_courses}
	return articulated_names, unarticulated_names


def count_required_courses_optimal(df, combo):
	requirements, course_options, uc_group_map, receiving_map = get_requirement_options(df, combo)
	selected_courses, req_to_course, uncovered = optimal_set_cover(requirements, course_options)

	uc_counts = {uc: {'articulated': set(), 'unarticulated': set()} for uc in [uc.lower() for uc in combo]}
	for uc in uc_counts:
		uc_groups = [k for k in uc_group_map if k[0] == uc]
		for group_key in uc_groups:
			group_reqs = uc_group_map[group_key]
			# Organize by set_id
			sets = {}
			for req in group_reqs:
				_, _, set_id, idx = req
				sets.setdefault(set_id, []).append(req)
			group_fulfilled = False
			for set_id, reqs in sets.items():
				# Get Num Required from the first row in this set
				num_required = None
				for req in reqs:
					mask = (
						(df['UC Name'].str.lower() == uc)
						& (df['Group ID'] == group_key[1])
						& (df['Set ID'] == set_id)
					)
					if mask.any():
						num_required = int(df[mask]['Num Required'].iloc[0])
						break
				fulfilled = sum(1 for req in reqs if req in req_to_course)
				if fulfilled >= num_required:
					group_fulfilled = True
					break
			if not group_fulfilled:
				# For each set, count how many more are needed to fulfill that set
				min_needed = None
				min_unfulfilled_reqs = []
				for set_id, reqs in sets.items():
					num_required = None
					for req in reqs:
						mask = (
							(df['UC Name'].str.lower() == uc)
							& (df['Group ID'] == group_key[1])
							& (df['Set ID'] == set_id)
						)
						if mask.any():
							num_required = int(df[mask]['Num Required'].iloc[0])
							break
					unfulfilled_reqs = [req for req in reqs if req not in req_to_course]
					needed = max(0, num_required - sum(1 for req in reqs if req in req_to_course))
					if min_needed is None or needed < min_needed:
						min_needed = needed
						min_unfulfilled_reqs = unfulfilled_reqs[:needed]
				for req in min_unfulfilled_reqs:
					uc_counts[uc]['unarticulated'].update(receiving_map[req])

	# Articulated courses
	for req in requirements:
		uc, group_id, set_id, idx = req
		if req in req_to_course:
			uc_counts[uc]['articulated'].add(req_to_course[req])

	articulated_courses = set()
	unarticulated_courses = set()
	for uc in uc_counts:
		articulated_courses.update((uc, course) for course in uc_counts[uc]['articulated'])
		unarticulated_courses.update((uc, course) for course in uc_counts[uc]['unarticulated'])

	return articulated_courses, unarticulated_courses, uc_counts


def process_combinations(df, uc_list, txt_file="optimal_articulation_output.txt"):
	all_combinations = generate_combinations(uc_list)
	k = len(all_combinations[0])
	n = len(uc_list)
	roles = get_roles(k)
	per_uc_per_position = math.factorial(n-1) // math.factorial(n-k)

	print(f"Total UC combinations generated: {len(all_combinations)}")
	with open(txt_file, "w") as f:
		f.write(f"Total UC combinations generated: {len(all_combinations)}\n")

		uc_role_totals = {
			uc: {role: {'articulated': 0, 'unarticulated': 0} for role in roles} for uc in uc_list
		}

		for combo in tqdm(all_combinations, total=len(all_combinations), desc="Processing combinations", unit="combo"):
			results = []
			previous_unarticulated_names = set()
			previous_total_unique = 0
			final_total_unique_courses = 0
			for idx, uc in enumerate(combo):
				role = roles[idx]
				uc_lower = uc.lower()
				prefix_combo = combo[:idx + 1]
				articulated_courses, unarticulated_courses, uc_counts = count_required_courses_optimal(df, prefix_combo)
				art_courses = sorted(uc_counts[uc_lower]['articulated'])
				unart_courses = sorted(uc_counts[uc_lower]['unarticulated'])
				current_articulated_names, current_unarticulated_names = get_course_name_sets(articulated_courses, unarticulated_courses)
				current_total_unique = len(current_articulated_names | current_unarticulated_names)
				final_total_unique_courses = current_total_unique

				# Count only the net increase in total required courses from the previous prefix.
				# This avoids over-counting when the optimal pathway changes course identity
				# but the total number of required courses only increases by a small amount.
				art_count = max(0, current_total_unique - previous_total_unique)
				unart_count = max(0, len(current_unarticulated_names) - len(previous_unarticulated_names))
				uc_role_totals[uc][role]['articulated'] += art_count
				uc_role_totals[uc][role]['unarticulated'] += unart_count
				art_str = "; ".join(art_courses) if art_courses else "-"
				unart_str = "; ".join(unart_courses) if unart_courses else "-"
				results.append(
					f"{uc} ({role}): +{art_count} Net Required Courses, +{unart_count} Unarticulated "
					f"{{Current Optimal Articulated Courses: {art_str}; Current Optimal Unarticulated Courses: {unart_str}}}"
				)

				previous_unarticulated_names = current_unarticulated_names
				previous_total_unique = current_total_unique

			combo_str = ", ".join(combo)
			f.write(f"\nProcessing combination: {combo_str}\n")
			f.write(f"Total Unique Courses Required: {final_total_unique_courses}\n")
			for res in results:
				f.write(res + "\n")

		print("\nDone. Detailed results were written to the output file.\n")
		f.write("\n--- Final Totals Per UC by Role in Combination ---\n\n")
		for uc in uc_list:
			f.write(f"{uc}:\n")
			for role in roles:
				art = uc_role_totals[uc][role]['articulated']
				unart = uc_role_totals[uc][role]['unarticulated']
				f.write(f"  As {role}: {art} Courses, {unart} Unarticulated\n")
			f.write("\n")

		# Print averages per UC per role
		print("\nDone. Averages were written to the output file.\n")
		f.write("\n--- Average Per UC by Role in Combination ---\n\n")
		for uc in uc_list:
			f.write(f"{uc}:\n")
			for role in roles:
				art_avg = uc_role_totals[uc][role]['articulated'] / per_uc_per_position
				unart_avg = uc_role_totals[uc][role]['unarticulated'] / per_uc_per_position
				f.write(f"  As {role}: {art_avg:.2f} Courses, {unart_avg:.2f} Unarticulated\n")
			f.write("\n")


def load_csv(file_path):
	return pd.read_csv(file_path)


if __name__ == "__main__":
	file_path = "/Users/yasminkabir/Documents/GitHub/transfer-agreements-analysis/filtered_results/Allan_Hancock_College_filtered.csv"  # change to your CSV path

	if not os.path.exists(file_path):
		raise FileNotFoundError(f"❌ File not found: {file_path}")

	df = load_csv(file_path)
	uc_list = uc_schools
	process_combinations(df, uc_list)

