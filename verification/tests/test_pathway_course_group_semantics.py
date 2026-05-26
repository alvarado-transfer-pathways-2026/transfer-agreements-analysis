import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PATHWAY_DIR = PROJECT_ROOT / "pathway_generator"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PATHWAY_DIR) not in sys.path:
    sys.path.insert(0, str(PATHWAY_DIR))

from major_checker import MajorRequirements  # noqa: E402


class PathwayCourseGroupSemanticsTests(unittest.TestCase):
    def test_and_block_requires_all_courses(self):
        requirements = object.__new__(MajorRequirements)
        requirements.group_defs = {
            "UCLA": {
                "Data Structures": {
                    "num_required": 1,
                }
            }
        }
        requirements.group_block_map = {
            ("UCLA", "Data Structures"): [["CIS 22C", "CIS 22A"]]
        }
        articulated = {
            "CIS 22C": {"units": 4.5},
            "CIS 22A": {"units": 4.5},
        }

        remaining = requirements.get_remaining_courses({"CIS 22C"}, articulated)

        self.assertEqual(["CIS 22A"], [course["courseCode"] for course in remaining])
        self.assertEqual([], requirements.get_remaining_courses({"CIS 22C", "CIS 22A"}, articulated))


if __name__ == "__main__":
    unittest.main()
