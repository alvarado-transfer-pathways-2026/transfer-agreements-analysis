import pandas as pd
from itertools import permutations
import os
import math
from multiprocessing import Pool, cpu_count
from importlib import import_module

try:
	tqdm = import_module("tqdm").tqdm
except Exception:
	def tqdm(iterable, **kwargs):
		return iterable

uc_schools = ["UCSD", "UCSB", "UCSC", "UCLA", "UCB", "UCI", "UCD", "UCR", "UCM"]

def generate_combinations(uc_schools):
	# Generate all permutations of all 9 UCs
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

# Helper function for multiprocessing
def process_combo(args):
	combo, df_pickle, roles = args
	import pickle
	df = pickle.loads(df_pickle)
	
	previous_unarticulated_names = set()
	previous_total_unique = 0
	uc_role_counts = []
	
	for idx, uc in enumerate(combo):
		role = roles[idx]
		uc_lower = uc.lower()
		prefix_combo = combo[:idx + 1]
		articulated_courses, unarticulated_courses, uc_counts = count_required_courses_optimal(df, prefix_combo)
		current_articulated_names, current_unarticulated_names = get_course_name_sets(articulated_courses, unarticulated_courses)
		current_total_unique = len(current_articulated_names | current_unarticulated_names)
		
		# Count net increase from previous prefix
		art_count = max(0, current_total_unique - previous_total_unique)
		unart_count = max(0, len(current_unarticulated_names) - len(previous_unarticulated_names))
		
		uc_role_counts.append((uc, role, art_count, unart_count))
		
		previous_unarticulated_names = current_unarticulated_names
		previous_total_unique = current_total_unique
	
	return uc_role_counts

def process_combinations_order_sensitive(df, uc_list):
	all_combinations = generate_combinations(uc_list)
	k = len(all_combinations[0])
	n = len(uc_list)
	roles = get_roles(k)
	per_uc_per_position = math.factorial(n-1) // math.factorial(n-k)

	uc_role_totals = {
		uc: {role: {'articulated': 0, 'unarticulated': 0} for role in roles} for uc in uc_list
	}

	# To pass DataFrame to Pool workers, pickle it once
	import pickle
	df_pickle = pickle.dumps(df)

	# Prepare arguments for parallel processing
	args = [(combo, df_pickle, roles) for combo in all_combinations]

	with Pool(cpu_count()) as pool:
		results = list(tqdm(pool.imap(process_combo, args), total=len(args), desc="Processing combinations"))

	for uc_role_counts in results:
		for uc, role, art_count, unart_count in uc_role_counts:
			uc_role_totals[uc][role]['articulated'] += art_count
			uc_role_totals[uc][role]['unarticulated'] += unart_count

	return uc_role_totals, per_uc_per_position, roles

def process_all_csvs(folder_path):
	total_txt = "optimal_total_combination_order.txt"
	avg_txt = "optimal_average_combination_order.txt"
	excluded_txt = "optimal_transferrable_cc_uc_pairs.txt"

	open(total_txt, 'w').close()
	open(avg_txt, 'w').close()
	open(excluded_txt, 'w').close()

	csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
	average_results_list = []
	per_uc_per_position = None
	roles = None

	overall_totals = {}

	for idx, file in enumerate(csv_files):
		print(f"Processing {idx+1}/{len(csv_files)}: {file}")
		file_path = os.path.join(folder_path, file)
		df = pd.read_csv(file_path)
		results, per_uc_per_position, roles = process_combinations_order_sensitive(df, uc_schools)

		# Initialize overall_totals on first run
		if not overall_totals:
			overall_totals = {
				uc: {role: {'articulated': 0, 'unarticulated': 0} for role in roles} for uc in uc_schools
			}

		for uc in uc_schools:
			for role in roles:
				overall_totals[uc][role]['articulated'] += results[uc][role]['articulated']
				overall_totals[uc][role]['unarticulated'] += results[uc][role]['unarticulated']

		with open(total_txt, "a") as f:
			f.write(f"--- Processing {file} ---\n\n")
			for uc in uc_schools:
				f.write(f"{uc}:\n")
				for role in roles:
					art = results[uc][role]['articulated']
					unart = results[uc][role]['unarticulated']
					f.write(f"  As {role}: {art} Courses, {unart} Unarticulated\n")
				f.write("\n")

		avg = {
			uc: {role: {
				'articulated': round(results[uc][role]['articulated'] / per_uc_per_position, 2),
				'unarticulated': round(results[uc][role]['unarticulated'] / per_uc_per_position, 2)
			} for role in roles} for uc in uc_schools
		}
		average_results_list.append(avg)

		with open(avg_txt, "a") as f:
			f.write(f"--- Processing {file} ---\n\n")
			for uc in uc_schools:
				f.write(f"{uc}:\n")
				for role in roles:
					art = avg[uc][role]['articulated']
					unart = avg[uc][role]['unarticulated']
					f.write(f"  As {role}: {art} Courses, {unart} Unarticulated\n")
				f.write("\n")

	# Append grand totals and averages
	with open(total_txt, "a") as f:
		f.write("\n--- Grand Totals Across All Files ---\n\n")
		for uc in uc_schools:
			f.write(f"{uc}:\n")
			for role in roles:
				art = overall_totals[uc][role]['articulated']
				unart = overall_totals[uc][role]['unarticulated']
				f.write(f"  As {role}: {art} Courses, {unart} Unarticulated\n")
			f.write("\n")

		n = len(csv_files)
		f.write("--- Averages (Total ÷ # Files) ---\n\n")
		for uc in uc_schools:
			f.write(f"{uc}:\n")
			for role in roles:
				art_avg = round(overall_totals[uc][role]['articulated'] / n, 2)
				unart_avg = round(overall_totals[uc][role]['unarticulated'] / n, 2)
				f.write(f"  As {role}: {art_avg} Courses, {unart_avg} Unarticulated\n")
			f.write("\n")

	with open(avg_txt, "a") as f:
		f.write("--- Average of Averages ---\n\n")
		n = len(average_results_list)
		for uc in uc_schools:
			f.write(f"{uc}:\n")
			for role in roles:
				art_total = sum(avg[uc][role]['articulated'] for avg in average_results_list)
				unart_total = sum(avg[uc][role]['unarticulated'] for avg in average_results_list)
				art_avg = round(art_total / n, 2)
				unart_avg = round(unart_total / n, 2)
				f.write(f"  As {role}: {art_avg} Courses, {unart_avg} Unarticulated\n")
			f.write("\n")

	# Create per-order average CSVs with filtered average row
	for idx, role in enumerate(roles):
		data = []
		filtered_pairs = []
		filtered_sum = {}
		filtered_count = {}

		for file_name, avg in zip(csv_files, average_results_list):
			row = {"Community College": file_name}
			for uc in uc_schools:
				art = avg[uc][role]['articulated']
				unart = avg[uc][role]['unarticulated']
				row[f"{uc} Articulated"] = art
				row[f"{uc} Unarticulated"] = unart

				if unart == 0:
					filtered_sum[f"{uc} Articulated"] = filtered_sum.get(f"{uc} Articulated", 0) + art
					filtered_count[f"{uc} Articulated"] = filtered_count.get(f"{uc} Articulated", 0) + 1
				else:
					filtered_pairs.append((file_name, uc))
			data.append(row)

		df = pd.DataFrame(data)

		avg_row = {"Community College": "AVERAGE"}
		for col in df.columns[1:]:
			avg_row[col] = round(df[col].mean(), 2)
		df = pd.concat([df, pd.DataFrame([avg_row])], ignore_index=True)

		# Add filtered average row
		transfer_avg_row = {"Community College": "TRANSFERABLE AVERAGE"}
		for col in df.columns[1:]:
			if col.endswith("Articulated"):
				if filtered_count.get(col, 0) > 0:
					transfer_avg_row[col] = round(filtered_sum[col] / filtered_count[col], 2)
				else:
					transfer_avg_row[col] = 0.0
			else:
				transfer_avg_row[col] = 0.0
		df = pd.concat([df, pd.DataFrame([transfer_avg_row])], ignore_index=True)

		df.to_csv(f"optimal_order_{idx+1}_averages.csv", index=False)

		# Append filtered average to average_combination_order.txt
		with open(avg_txt, "a") as f:
			f.write(f"--- Transferable Average of Averages for Order {idx+1} ---\n\n")
			for col in df.columns[1:]:
				if col != "Community College":
					f.write(f"{col}: {transfer_avg_row[col]}\n")
			f.write("\n")

		# Write excluded pairs to txt file
		with open(excluded_txt, "a") as f:
			f.write(f"--- Order {idx+1} ---\n")
			cc_grouped = {}
			for cc, uc in filtered_pairs:
				cc_grouped.setdefault(cc, []).append(uc)
			for cc in sorted(cc_grouped):
				ucs = ", ".join(cc_grouped[cc])
				f.write(f"{cc}: {ucs}\n")
			f.write("\n")

if __name__ == "__main__":
	folder_path = "/Users/yasminkabir/Documents/GitHub/transfer-agreements-analysis/district_csvs"
	process_all_csvs(folder_path)
