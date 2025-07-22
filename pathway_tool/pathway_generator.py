import json
import os
from collections import defaultdict

# --- CONFIGURATION ---
# This script is designed to be run from the root of the project directory.
# It assumes the config files are in 'pathway_tool/created_json_files/'
# and the processed data files are in the root directory.

CONFIG_DIR = 'pathway_tool/created_json_files/'
DATA_DIR = 'pathway_tool/' # All data files are in here

# --- DATA LOADING ---

def load_all_data():
    """Loads all necessary JSON files into a single dictionary for easy access."""
    print("--- Loading all data files ---")
    data = {}
    try:
        with open(os.path.join(CONFIG_DIR, 'uc_names_standardized.json'), 'r', encoding='utf-8-sig') as f:
            print(f"Reading file: {'uc_names_standardized.json'}")
            print(f"Size: {os.path.getsize('uc_names_standardized.json')} bytes")
            data['uc_reqs'] = json.load(f)
        with open(os.path.join(CONFIG_DIR, 'prerequisites.json'), 'r', encoding='utf-8-sig') as f:
            data['prereqs'] = json.load(f)
        with open(os.path.join(CONFIG_DIR, 'ge_rules.json'), 'r', encoding='utf-8-sig') as f:
            data['ge_rules'] = json.load(f)
        with open('pathway_tool/master_articulation_data.json', 'r', encoding='utf-8-sig') as f:
            data['articulations'] = json.load(f)
        with open('pathway_tool/course_metadata.json', 'r', encoding='utf-8-sig') as f:
            data['metadata'] = json.load(f)
        print("✅ All data files loaded successfully.")
    except FileNotFoundError as e:
        print(f"❌ ERROR: Could not find a required data file: {e}")
        print("Please ensure you have run process_data.py and all config files are in the correct directory.")
        return None
    return data

# --- LOGIC FOR GATHERING REQUIREMENTS ---

def get_ge_requirements(pathway_type, data):
    """Generates a set of generic GE standard names based on the pathway type."""
    ge_names = set()
    ge_rules = data['ge_rules']
    
    if pathway_type == 'major_prep_optimized':
        pattern = ge_rules['seven_course_pattern']
        ge_names.add("GE_ENGLISH_COMP_1")
        ge_names.add("GE_ENGLISH_COMP_2")
        ge_names.add("GE_MATH")
        ge_names.add("GE_ARTS_HUMANITIES_1")
        ge_names.add("GE_SOCIAL_BEHAVIORAL_1")
        ge_names.add("GE_PHYSICAL_BIOLOGICAL_1")
        ge_names.add("GE_BREADTH_CHOICE_1")
    elif pathway_type == 'igetc_first':
        pattern = ge_rules['igetc_pattern']
        for i in range(pattern['area_1_english_comm']): ge_names.add(f"IGETC_AREA_1_{i+1}")
        for i in range(pattern['area_2_math_quant_reasoning']): ge_names.add(f"IGETC_AREA_2_{i+1}")
        for i in range(pattern['area_3_arts_humanities']): ge_names.add(f"IGETC_AREA_3_{i+1}")
        for i in range(pattern['area_4_social_behavioral']): ge_names.add(f"IGETC_AREA_4_{i+1}")
        for i in range(pattern['area_5_physical_biological']): ge_names.add(f"IGETC_AREA_5_{i+1}")
        for i in range(pattern['area_6_language_other_than_english']): ge_names.add(f"IGETC_AREA_6_{i+1}")
        for i in range(pattern['area_7_ethnic_studies']): ge_names.add(f"IGETC_AREA_7_{i+1}")
        
    return ge_names

def get_major_requirements(target_ucs, data):
    """Consolidates all required major prep standard names for the selected UCs."""
    required_names = set()
    choice_groups = []

    for uc in target_ucs:
        if uc in data['uc_reqs']:
            requirements = data['uc_reqs'][uc]
            if "REQUIRED_CORE" in requirements:
                required_names.update(requirements["REQUIRED_CORE"].values())
            for key in ["CHOOSE_ONE_FROM", "CHOOSE_TWO_FROM", "CHOOSE_THREE_FROM"]:
                if key in requirements:
                    num_to_choose = {"CHOOSE_ONE_FROM": 1, "CHOOSE_TWO_FROM": 2, "CHOOSE_THREE_FROM": 3}[key]
                    for group in requirements[key]:
                        choice_groups.append({
                            "uc": uc, "name": group["group_name"], "choose": num_to_choose,
                            "options": set(group["courses"].values())
                        })
    return required_names, choice_groups

def resolve_choices(required_names, choice_groups):
    """Intelligently resolves choice groups, prioritizing overlaps."""
    for group in choice_groups:
        overlap = group["options"].intersection(required_names)
        chosen = set(list(overlap)[:group["choose"]])
        remaining_to_choose = group["choose"] - len(chosen)
        if remaining_to_choose > 0:
            # Default choice: prioritize Physics > Chem > Bio > other
            options_sorted = sorted(list(group["options"] - chosen), key=lambda x: ('PHYSICS' not in x, 'CHEM' not in x, 'BIO' not in x, x))
            chosen.update(options_sorted[:remaining_to_choose])
        required_names.update(chosen)
    return required_names

def find_articulated_cc_courses(required_names, selected_ccc, data):
    """Finds the specific CC courses that satisfy the list of required standard names."""
    final_cc_course_list = set()
    unarticulated_requirements = set()
    
    ccc_articulations = [art for art in data['articulations'] if art['ccc_name'] == selected_ccc]

    for standard_name in required_names:
        found_articulation = False
        # Handle generic GE placeholders
        if standard_name.startswith("GE_") or standard_name.startswith("IGETC_"):
            final_cc_course_list.add(standard_name) # Add the placeholder itself
            found_articulation = True
            continue

        for art in ccc_articulations:
            if art['standard_name'] == standard_name:
                for course_group in art['ccc_courses_required']:
                    for course in course_group:
                        final_cc_course_list.add(course['id'])
                found_articulation = True
                break
        
        if not found_articulation:
            unarticulated_requirements.add(standard_name)

    return list(final_cc_course_list), list(unarticulated_requirements)

# --- LOGIC FOR SEQUENCING AND SCHEDULING ---

def build_prereq_graph(course_list, selected_ccc, data):
    """Builds a prerequisite graph (course -> list of prereqs)."""
    graph = {course: [] for course in course_list}
    
    for cc_course_id in course_list:
        if cc_course_id.startswith("GE_") or cc_course_id.startswith("IGETC_"): continue
        
        metadata_key = f"{selected_ccc}_{cc_course_id}"
        meta = data['metadata'].get(metadata_key)
        if not meta: continue

        for standard_name in meta.get("fulfills_standard_names", []):
            if standard_name in data['prereqs']:
                for prereq_standard_name in data['prereqs'][standard_name]:
                    for potential_prereq_cc_id in course_list:
                        prereq_meta_key = f"{selected_ccc}_{potential_prereq_cc_id}"
                        prereq_meta = data['metadata'].get(prereq_meta_key)
                        if prereq_meta and prereq_standard_name in prereq_meta.get("fulfills_standard_names", []):
                            graph[cc_course_id].append(potential_prereq_cc_id)
    return graph

def topological_sort(graph):
    """Performs a topological sort on the course graph to get a valid sequence."""
    sorted_order = []
    in_degree = {u: 0 for u in graph}
    
    # Build the reversed graph and in-degree count
    rev_graph = defaultdict(list)
    for course, prereqs in graph.items():
        for prereq in prereqs:
            rev_graph[prereq].append(course)
            in_degree[course] += 1
            
    queue = [u for u in graph if in_degree[u] == 0]
    
    while queue:
        u = queue.pop(0)
        sorted_order.append(u)
        for v in rev_graph[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
    
    if len(sorted_order) == len(graph):
        return sorted_order
    else:
        print("Warning: Cycle detected in prerequisite graph. Scheduling may be incorrect.")
        return list(graph.keys()) # Fallback to unsorted list

def schedule_semesters(sorted_courses, selected_ccc, data, unit_cap=18):
    """Schedules courses into semesters using the topologically sorted list."""
    pathway = []
    semester_num = 1
    scheduled_courses = set()
    total_units = 0

    courses_to_schedule = list(sorted_courses)

    while courses_to_schedule:
        current_semester_courses = []
        current_semester_units = 0
        
        # Use a list of courses available to be scheduled in this semester
        schedulable_now = []

        for course_id in courses_to_schedule:
            # Check if all prerequisites for this course have already been scheduled
            prereqs = data['graph'].get(course_id, [])
            if all(prereq in scheduled_courses for prereq in prereqs):
                schedulable_now.append(course_id)
        
        for course_id in schedulable_now:
            is_ge_placeholder = course_id.startswith("GE_") or course_id.startswith("IGETC_")
            course_units = 3.0 if is_ge_placeholder else data['metadata'].get(f"{selected_ccc}_{course_id}", {}).get('units', 3.0)

            if current_semester_units + course_units <= unit_cap:
                current_semester_courses.append({ "course_id": course_id, "units": course_units })
                current_semester_units += course_units
                scheduled_courses.add(course_id)
                courses_to_schedule.remove(course_id)
        
        if current_semester_courses:
            pathway.append({
                "semester": semester_num, "units": current_semester_units,
                "courses": current_semester_courses
            })
            total_units += current_semester_units
            semester_num += 1
        else:
            print("Warning: Could not schedule all courses. Prerequisite deadlock.")
            break
            
    # Pad to 60 units if necessary
    if total_units < 60:
        units_needed = 60 - total_units
        electives_needed = (units_needed + 2) // 3 # Assuming 3 units per elective
        last_semester = pathway[-1]
        for i in range(int(electives_needed)):
            if last_semester['units'] + 3 <= unit_cap:
                last_semester['courses'].append({"course_id": f"ELECTIVE_{i+1}", "units": 3.0})
                last_semester['units'] += 3.0
            else:
                pathway.append({"semester": semester_num, "units": 3.0, "courses": [{"course_id": f"ELECTIVE_{i+1}", "units": 3.0}]})
                semester_num += 1
            
    return pathway

# --- MAIN ORCHESTRATION FUNCTION ---

def generate_pathway(selected_ccc, target_ucs, pathway_type):
    """The main function that orchestrates the entire pathway generation process."""
    all_data = load_all_data()
    if not all_data: return {"error": "Failed to load data."}
    
    # Step 1: Get major prep and GE requirements based on pathway type
    major_reqs, choice_groups = get_major_requirements(target_ucs, all_data)
    ge_reqs = get_ge_requirements(pathway_type, all_data)
    
    # Step 2: Resolve choices and combine requirements
    resolved_major_reqs = resolve_choices(major_reqs, choice_groups)
    final_required_names = resolved_major_reqs.union(ge_reqs)

    # Step 3: Find the articulated CC courses for these requirements
    cc_courses, unarticulated = find_articulated_cc_courses(final_required_names, selected_ccc, all_data)
    
    # Step 4: Build prerequisite graph
    graph = build_prereq_graph(cc_courses, selected_ccc, all_data)
    all_data['graph'] = graph # Make graph accessible to scheduler
    
    # Step 5: Topologically sort the courses
    sorted_courses = topological_sort(graph)
    
    # Step 6: Schedule the courses into semesters
    pathway = schedule_semesters(sorted_courses, selected_ccc, all_data)

    # Step 7: Format the final output
    output = {
        "metadata": {
            "ccc_name": selected_ccc, "target_uc_names": target_ucs, "pathway_type": pathway_type,
            "total_courses": len(cc_courses), "total_semesters": len(pathway),
            "unarticulated_requirements": unarticulated
        },
        "pathway": pathway
    }
    return output

# --- TEST BLOCK ---
if __name__ == "__main__":
    print("\n--- Running Test Case ---")
    test_ccc = "Diablo Valley College"
    test_ucs = ["UCB", "UCLA"]
    test_pathway_type = "major_prep_optimized"

    final_plan = generate_pathway(test_ccc, test_ucs, test_pathway_type)

    print("\n--- Final Generated Plan ---")
    print(json.dumps(final_plan, indent=2))
