import json
import os

def parse_and_display_json(filepath):
    """Parse and display the contents of an articulation JSON file in readable format"""
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return
    
    # Extract college name
    college_name = list(data.keys())[0]
    college_data = data[college_name]
    
    print(f"🏫 COLLEGE: {college_name}")
    print(f"📁 FILE: {os.path.basename(filepath)}")
    print(f"🎯 UC CAMPUSES: {len(college_data)}")
    print("=" * 80)
    
    # Display each UC's requirements
    for uc_name, uc_requirements in college_data.items():
        print(f"\n📍 {uc_name} ({len(uc_requirements)} requirements)")
        print("-" * 60)
        
        for req_name, req_data in uc_requirements.items():
            print(f"\n  🔹 REQUIREMENT: {req_name}")
            print(f"     Set ID: {req_data.get('set_id', 'N/A')}")
            print(f"     Num Required: {req_data.get('num_required', 'N/A')}")
            
            # Display receiving course(s)
            if 'receiving_course' in req_data:
                print(f"     UC Course: {req_data['receiving_course']}")
            elif 'receiving_courses' in req_data:
                print(f"     UC Courses: {', '.join(req_data['receiving_courses'])}")
            
            # Display course groups
            course_groups = req_data.get('course_groups', [])
            print(f"     Course Groups: {len(course_groups)}")
            
            for i, group in enumerate(course_groups, 1):
                print(f"       GROUP {i} (All courses required):")
                for course in group:
                    course_name = course.get('course', 'Unknown')
                    units = course.get('units', 'N/A')
                    print(f"         - {course_name} ({units} units)")
                
                if i < len(course_groups):
                    print(f"       --- OR ---")
        
        print("-" * 60)

def display_specific_requirement(filepath, uc_name, req_name):
    """Display just one specific requirement from a JSON file"""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return
    
    college_name = list(data.keys())[0]
    college_data = data[college_name]
    
    if uc_name not in college_data:
        print(f"❌ UC campus '{uc_name}' not found in {college_name}")
        print(f"Available UCs: {', '.join(college_data.keys())}")
        return
    
    if req_name not in college_data[uc_name]:
        print(f"❌ Requirement '{req_name}' not found for {uc_name} at {college_name}")
        print(f"Available requirements: {', '.join(college_data[uc_name].keys())}")
        return
    
    req_data = college_data[uc_name][req_name]
    
    print(f"🏫 {college_name}")
    print(f"🎯 {uc_name} - {req_name}")
    print("=" * 50)
    print(f"Set ID: {req_data.get('set_id', 'N/A')}")
    print(f"Num Required: {req_data.get('num_required', 'N/A')}")
    
    if 'receiving_course' in req_data:
        print(f"UC Course: {req_data['receiving_course']}")
    elif 'receiving_courses' in req_data:
        print(f"UC Courses: {', '.join(req_data['receiving_courses'])}")
    
    course_groups = req_data.get('course_groups', [])
    print(f"\nCourse Options ({len(course_groups)} ways to satisfy):")
    
    for i, group in enumerate(course_groups, 1):
        print(f"\n  OPTION {i}: Complete ALL of these courses")
        for course in group:
            course_name = course.get('course', 'Unknown')
            units = course.get('units', 'N/A')
            print(f"    • {course_name} ({units} units)")

def list_available_files(directory="articulated_courses_json"):
    """List all available JSON files"""
    if not os.path.exists(directory):
        print(f"❌ Directory {directory} does not exist!")
        return []
    
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    json_files.sort()
    
    print(f"📂 Available JSON files in {directory}:")
    for i, filename in enumerate(json_files, 1):
        print(f"  {i:2d}. {filename}")
    
    return json_files

if __name__ == "__main__":
    # List available files
    files = list_available_files()
    
    if not files:
        print("No JSON files found!")
        exit()
    
    # Example usage - uncomment what you want to see:
    
    # Display entire file contents
    print("\n" + "="*80)
    parse_and_display_json("articulated_courses_json/De_Anza_College_articulation.json")
    
    # Display just one specific requirement
    # print("\n" + "="*80)
    # display_specific_requirement("articulated_courses_json/De_Anza_College_articulation.json", "UCSD", "Intro")
    
    # Interactive selection (uncomment to use)
    # print("\nEnter the number of the file you want to parse:")
    # try:
    #     choice = int(input("Choice: ")) - 1
    #     if 0 <= choice < len(files):
    #         filepath = f"articulated_courses_json/{files[choice]}"
    #         parse_and_display_json(filepath)
    #     else:
    #         print("Invalid choice!")
    # except ValueError:
    #     print("Please enter a number!")