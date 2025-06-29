import pandas as pd
from itertools import permutations
import os
import math

uc_schools = ["UCSD", "UCSB", "UCSC", "UCLA", "UCB", "UCI", "UCD", "UCR", "UCM"]

def generate_combinations(uc_schools):
    # Change the number here for different permutation sizes
    return list(permutations(uc_schools, 5))

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

def greedy_set_cover(requirements, course_options):
    uncovered = set(requirements)
    course_to_reqs = {}
    for req in uncovered:
        for course in course_options[req]:
            course_to_reqs.setdefault(course, set()).add(req)

    selected_courses = set()
    req_to_course = {}

    while uncovered:
        best_course = None
        best_cover = set()
        # Sort courses for deterministic tie-breaking
        for course in sorted(course_to_reqs):
            reqs = course_to_reqs[course]
            cover = reqs & uncovered
            if len(cover) > len(best_cover):
                best_course = course
                best_cover = cover
        if not best_course:
            break
        selected_courses.add(best_course)
        for req in best_cover:
            req_to_course[req] = best_course
        uncovered -= best_cover
    return selected_courses, req_to_course, uncovered

def count_required_courses_global(df, combo):
    requirements, course_options, uc_group_map, receiving_map = get_requirement_options(df, combo)
    selected_courses, req_to_course, uncovered = greedy_set_cover(requirements, course_options)

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
                # Count how many in this set are fulfilled
                fulfilled = sum(1 for req in reqs if req in req_to_course)
                if fulfilled >= num_required:
                    group_fulfilled = True
                    break  # This group is fulfilled by this set, skip unarticulated for this group
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
                # Only count the minimum number of unfulfilled requirements needed to fulfill the group
                for req in min_unfulfilled_reqs:
                    uc_counts[uc]['unarticulated'].update(receiving_map[req])

    # Articulated courses (as before)
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

def process_combinations_order_sensitive(df, uc_list):
    all_combinations = generate_combinations(uc_list)
    k = len(all_combinations[0])
    n = len(uc_list)
    roles = get_roles(k)
    per_uc_per_position = math.factorial(n-1) // math.factorial(n-k)

    uc_role_totals = {
        uc: {role: {'articulated': 0, 'unarticulated': 0} for role in roles} for uc in uc_list
    }

    for combo in all_combinations:
        articulated_tracker = set()
        unarticulated_tracker = set()

        for idx, uc in enumerate(combo):
            role = roles[idx]
            art_count, unart_count = 0, 0
            # Use the greedy logic for each UC in the combo
            # (simulate the greedy per-UC logic as in total_combination_order.py)
            # For greedy, we need to run the global greedy for the whole combo, then count for each UC
            articulated_courses, unarticulated_courses, uc_counts = count_required_courses_global(df, combo)
            uc_lower = uc.lower()
            art_courses = sorted(uc_counts[uc_lower]['articulated'])
            unart_courses = sorted(uc_counts[uc_lower]['unarticulated'])

            # Only show new courses/unarticulated for this UC
            if idx == 0:
                seen_courses = set()
                seen_unarticulated = set()
            new_art_courses = [c for c in art_courses if c not in seen_courses]
            new_unart_courses = [c for c in unart_courses if c not in seen_unarticulated]

            art_count = len(new_art_courses)
            unart_count = len(new_unart_courses)
            uc_role_totals[uc][role]['articulated'] += art_count
            uc_role_totals[uc][role]['unarticulated'] += unart_count

            seen_courses.update(new_art_courses)
            seen_unarticulated.update(new_unart_courses)

    return uc_role_totals, per_uc_per_position, roles

def process_all_csvs(folder_path):
    total_txt = "greedy_total_combination_order.txt"
    avg_txt = "greedy_average_combination_order.txt"
    excluded_txt = "greedy_untransferrable_cc_uc_pairs.txt"

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

        df.to_csv(f"greedy_order_{idx+1}_averages.csv", index=False)

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
    folder_path = "/Users/yasminkabir/transfer-agreements-analysis/district_csvs"
    process_all_csvs(folder_path)