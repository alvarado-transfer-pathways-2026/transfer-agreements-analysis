import pandas as pd
from itertools import permutations
import os
import math

# List of UC campuses
uc_schools = ["UCSD", "UCSB", "UCSC", "UCLA", "UCB", "UCI", "UCD", "UCR","UCM"]

# Change the number here for different permutation sizes
def generate_combinations(uc_schools):
    return list(permutations(uc_schools, 9))

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

def process_combinations(df, uc_list, txt_file="articulation_output.txt"):
    all_combinations = generate_combinations(uc_list)
    k = len(all_combinations[0])
    n = len(uc_list)
    roles = get_roles(k)
    per_uc_per_position = math.factorial(n-1) // math.factorial(n-k)

    # Only this progress message will print to terminal
    print(f"Total UC combinations generated: {len(all_combinations)}")
    with open(txt_file, "w") as f:
        f.write(f"Total UC combinations generated: {len(all_combinations)}\n")

        uc_role_totals = {
            uc: {role: {'articulated': 0, 'unarticulated': 0} for role in roles} for uc in uc_list
        }

        for combo in all_combinations:
            articulated_courses, unarticulated_courses, uc_counts = count_required_courses_global(df, combo)
            total_unique_courses = len(set([course for (_, course) in articulated_courses] +
                                           [course for (_, course) in unarticulated_courses]))
            results = []
            seen_courses = set()
            seen_unarticulated = set()
            for idx, uc in enumerate(combo):
                role = roles[idx]
                uc_lower = uc.lower()
                art_courses = sorted(uc_counts[uc_lower]['articulated'])
                unart_courses = sorted(uc_counts[uc_lower]['unarticulated'])

                # Only show new courses/unarticulated for this UC
                new_art_courses = [c for c in art_courses if c not in seen_courses]
                new_unart_courses = [c for c in unart_courses if c not in seen_unarticulated]

                art_count = len(new_art_courses)
                unart_count = len(new_unart_courses)
                uc_role_totals[uc][role]['articulated'] += art_count
                uc_role_totals[uc][role]['unarticulated'] += unart_count
                art_str = "; ".join(new_art_courses) if new_art_courses else "-"
                unart_str = "; ".join(new_unart_courses) if new_unart_courses else "-"
                results.append(
                    f"{uc} ({role}): {art_count} Courses, {unart_count} Unarticulated "
                    f"{{Courses: {art_str}; Unarticulated: {unart_str}}}"
                )

                seen_courses.update(new_art_courses)
                seen_unarticulated.update(new_unart_courses)

            combo_str = ", ".join(combo)
            f.write(f"\nProcessing combination: {combo_str}\n")
            f.write(f"Total Unique Courses Required: {total_unique_courses}\n")
            for res in results:
                f.write(res + "\n")

        f.write("\n--- Final Totals Per UC by Role in Combination ---\n\n")
        for uc in uc_list:
            f.write(f"{uc}:\n")
            for role in roles:
                art = uc_role_totals[uc][role]['articulated']
                unart = uc_role_totals[uc][role]['unarticulated']
                f.write(f"  As {role}: {art} Courses, {unart} Unarticulated\n")
            f.write("\n")

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
    file_path = "/Users/yasminkabir/assist_web_scraping/district_csvs/Merced_Community_College_District.csv" #change to path of csv of the cc/district you want

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ File not found: {file_path}")

    df = load_csv(file_path)
    uc_list = uc_schools
    process_combinations(df, uc_list)