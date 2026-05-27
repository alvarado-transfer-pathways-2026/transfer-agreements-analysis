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
	return list(permutations(uc_schools, 4))

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
			# Each row in this Set ID becomes a separate requirement
			for row_idx, (_, row) in enumerate(set_df.iterrows()):
				key = (uc, group_id, set_id, row_idx)
				uc_group_map[(uc, group_id)].append(key)
				requirements.append(key)
				
				# For this row, collect all OR options from Courses Group columns
				options = []
				for col in row.index:
					if col.lower().startswith("courses group"):
						val = str(row[col]).strip()
						if val and val.lower() != "not articulated" and val.lower() != "nan":
							# Semicolon-separated = AND bundle
							bundle = frozenset(v.strip() for v in val.split(';') if v.strip())
							if bundle:
								options.append(bundle)
				
				course_options[key] = options
				
				# Receiving courses: split by semicolon to get the UC courses
				receiving_courses = [r.strip() for r in str(row['Receiving']).split(';') if r.strip()]
				receiving_map[key] = set(receiving_courses)
	
	return requirements, course_options, uc_group_map, receiving_map

def optimal_set_cover(requirements, course_options, time_limit=None):
	# Group requirements by (uc, group_id, set_id) to enforce set selection constraint
	# Within a group, only ONE set_id can be chosen
	req_options = {req: [opt for opt in course_options.get(req, []) if opt] for req in requirements}
	all_courses = sorted({course for opts in req_options.values() for opt in opts for course in opt})
	if not all_courses:
		return set(), {}, set(requirements)

	try:
		import pulp
	except Exception:
		# Greedy fallback
		selected_courses = set()
		req_to_bundles = {}

		def req_satisfied(req, chosen_courses):
			return any(opt.issubset(chosen_courses) for opt in req_options.get(req, []))

		while True:
			uncovered = [req for req in requirements if not req_satisfied(req, selected_courses)]
			if not uncovered:
				break

			best_req = None
			best_opt = None
			best_add = None
			best_gain = None

			for req in uncovered:
				for opt in req_options.get(req, []):
					add_count = len(opt - selected_courses)
					gain = sum(1 for r in uncovered if any(o.issubset(selected_courses | opt) for o in req_options.get(r, [])))
					if (
						best_opt is None
						or add_count < best_add
						or (add_count == best_add and gain > best_gain)
					):
						best_req = req
						best_opt = opt
						best_add = add_count
						best_gain = gain

			if best_opt is None:
				break

			selected_courses.update(best_opt)
			req_to_bundles.setdefault(best_req, []).append(best_opt)

			for req in requirements:
				if req not in req_to_bundles and req_satisfied(req, selected_courses):
					for opt in req_options.get(req, []):
						if opt.issubset(selected_courses):
							req_to_bundles.setdefault(req, []).append(opt)
							break

		return selected_courses, req_to_bundles, set(r for r in requirements if r not in req_to_bundles)

	model = pulp.LpProblem("OptimalSetCover", pulp.LpMinimize)
	x = pulp.LpVariable.dicts("x", all_courses, cat="Binary")
	y = {}
	for req in requirements:
		y[req] = pulp.LpVariable.dicts(f"y_{abs(hash(req))}", list(range(len(req_options.get(req, [])))), cat="Binary")

	# Minimize total CC courses used
	model += pulp.lpSum(x[c] for c in all_courses)

	# Constraint 1: For each Group ID, choose exactly one Set ID
	group_set_map = {}
	for req in requirements:
		uc, group_id, set_id = req[0], req[1], req[2]
		group_set_map.setdefault((uc, group_id), set()).add(set_id)

	z_by_group_set = {}

	# For each group, create one selector variable per set_id
	for (uc, group_id), set_ids in group_set_map.items():
		group_reqs = [req for req in requirements if req[0] == uc and req[1] == group_id]
		set_id_reqs = {}
		for req in group_reqs:
			set_id = req[2]
			set_id_reqs.setdefault(set_id, []).append(req)

		set_id_vars = {}
		for set_id, set_reqs in set_id_reqs.items():
			z_set = pulp.LpVariable(f"z_{uc}_{group_id}_{set_id}", cat="Binary")
			set_id_vars[set_id] = z_set
			z_by_group_set[(uc, group_id, set_id)] = z_set

		model += pulp.lpSum(set_id_vars.values()) == 1

	# Constraint 2: Row satisfaction is gated by the chosen set_id.
	for req in requirements:
		options = req_options.get(req, [])
		if not options:
			continue

		z_req = z_by_group_set[(req[0], req[1], req[2])]
		sum_y = pulp.lpSum(y[req][i] for i in range(len(options)))

		# Chosen set row must be satisfied; unchosen set row must be 0.
		model += sum_y >= z_req
		model += sum_y <= len(options) * z_req

		# Within a row, Courses Group columns are OR: choose at most one cell.
		model += sum_y <= 1

		for i, opt in enumerate(options):
			for course in opt:
				model += x[course] >= y[req][i]

	solver = pulp.PULP_CBC_CMD(msg=False)
	status = model.solve(solver)
	if pulp.LpStatus[status] != "Optimal":
		return set(), {}, set(requirements)

	selected_courses = {c for c in all_courses if pulp.value(x[c]) > 0.5}
	req_to_bundles = {}
	for req in requirements:
		bundles = []
		for i, opt in enumerate(req_options.get(req, [])):
			if pulp.value(y[req][i]) > 0.5:
				bundles.append(opt)
		if bundles:
			req_to_bundles[req] = bundles

	uncovered = {req for req in requirements if req not in req_to_bundles}
	return selected_courses, req_to_bundles, uncovered

def get_course_name_sets(articulated_courses, unarticulated_courses):
	articulated_names = {course for (_, course) in articulated_courses}
	unarticulated_names = {course for (_, course) in unarticulated_courses}
	return articulated_names, unarticulated_names

def count_required_courses_optimal(df, combo):
	requirements, course_options, uc_group_map, receiving_map = get_requirement_options(df, combo)
	selected_courses, req_to_bundles, uncovered = optimal_set_cover(requirements, course_options)

	# Count articulated and unarticulated at the row level
	uc_counts = {uc: {'articulated': set(), 'unarticulated': set()} for uc in [uc.lower() for uc in combo]}
	
	for uc in uc_counts:
		# Get all Group IDs for this UC
		uc_groups = [k for k in uc_group_map if k[0] == uc]
		
		for group_key in uc_groups:
			group_reqs = uc_group_map[group_key]
			
			# Determine which set_id is chosen for this group
			chosen_set_ids = set()
			for req in group_reqs:
				if req in req_to_bundles:
					chosen_set_ids.add(req[2])
			
			if chosen_set_ids:
				# Group is fulfilled by chosen set(s): ignore unchosen sets entirely.
				for req in group_reqs:
					if req[2] in chosen_set_ids:
						bundles = req_to_bundles.get(req, [])
						if bundles:
							for bundle in bundles:
								uc_counts[uc]['articulated'].update(bundle)
						else:
							uc_counts[uc]['unarticulated'].update(receiving_map.get(req, set()))
			else:
				# No set was chosen; count only one fallback set (least receiving courses).
				unchosen_set_ids = {}
				for req in group_reqs:
					set_id = req[2]
					if set_id not in unchosen_set_ids:
						unchosen_set_ids[set_id] = set()
					unchosen_set_ids[set_id].update(receiving_map.get(req, set()))

				if unchosen_set_ids:
					min_unchosen_set_id = min(unchosen_set_ids.keys(), key=lambda s: len(unchosen_set_ids[s]))
					for req in group_reqs:
						if req[2] == min_unchosen_set_id:
							uc_counts[uc]['unarticulated'].update(receiving_map.get(req, set()))

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
	previous_articulated_names = set()
	uc_role_counts = []
	
	for idx, uc in enumerate(combo):
		role = roles[idx]
		uc_lower = uc.lower()
		prefix_combo = combo[:idx + 1]
		articulated_courses, unarticulated_courses, uc_counts = count_required_courses_optimal(df, prefix_combo)
		current_articulated_names, current_unarticulated_names = get_course_name_sets(articulated_courses, unarticulated_courses)
		current_articulated_total = len(current_articulated_names)
		current_unarticulated_total = len(current_unarticulated_names)
		
		# Count articulated and unarticulated separately.
		art_count = max(0, current_articulated_total - len(previous_articulated_names))
		unart_count = max(0, current_unarticulated_total - len(previous_unarticulated_names))
		
		uc_role_counts.append((uc, role, art_count, unart_count))
		
		previous_articulated_names = current_articulated_names
		previous_unarticulated_names = current_unarticulated_names
	
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
