import os
import subprocess

ARTIC_DIR = "articulated_courses_json"
GE_FILE = "prerequisites/ge_reqs.json"

for filename in os.listdir(ARTIC_DIR):
    if filename.endswith("_articulation.json"):
        path = os.path.join(ARTIC_DIR, filename)
        print(f"🔁 Tagging and overwriting {filename}...")
        subprocess.run(["python", "json_editing_programs/course_tagger.py", path, path, GE_FILE])

print("✅ All articulation files tagged and overwritten.")
