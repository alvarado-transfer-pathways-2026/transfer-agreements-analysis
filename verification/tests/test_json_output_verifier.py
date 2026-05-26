import json
import tempfile
import unittest
from pathlib import Path

from verification.verify_json_output import verify_json_output


class JsonOutputVerifierTests(unittest.TestCase):
    def test_json_preserves_filtered_course_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "filtered_results").mkdir()
            (root / "articulated_courses_json").mkdir()

            (root / "filtered_results" / "Example_College_filtered.csv").write_text(
                "UC Name,Group ID,Set ID,Num Required,Receiving,Courses Group 1,Courses Group 2\n"
                "UCI,Calc1,A,1,MATH 2A,MATH 1A (5.00),MATH 1AH (5.00)\n",
                encoding="utf-8",
            )
            (root / "articulated_courses_json" / "Example_College_articulation.json").write_text(
                json.dumps(
                    {
                        "Example_College": {
                            "UCI": {
                                "Calc1": {
                                    "set_id": "A",
                                    "num_required": 1,
                                    "course_groups": [
                                        [{"course": "MATH 1A", "units": 5.0}],
                                        [{"course": "MATH 1AH", "units": 5.0}],
                                    ],
                                    "receiving_course": "MATH 2A",
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual([], verify_json_output("Example College", project_root=root))


if __name__ == "__main__":
    unittest.main()
