import unittest
import json
import tempfile
from pathlib import Path

from verification.common import PROJECT_ROOT, load_csv_rows
from verification.verify_district_csv import normalize_district_row, recompute_district_rows, verify_district_csv


class DistrictVerifierTests(unittest.TestCase):
    def test_foothill_deanza_selected_rows_match_golden_fixture(self):
        fixture_path = (
            PROJECT_ROOT
            / "verification"
            / "fixtures"
            / "districts"
            / "foothill_deanza_expected_subset.csv"
        )
        expected = {normalize_district_row(row) for row in load_csv_rows(fixture_path)}
        actual = {
            normalize_district_row(row)
            for row in recompute_district_rows(
                PROJECT_ROOT,
                "Foothill-De Anza Community College District",
            )
            if (
                row["UC Name"],
                row["Group ID"],
                row["Set ID"],
                row["Receiving"],
            )
            in {
                ("UCI", "Intro", "A", "I&C SCI 31; I&C SCI 32; I&C SCI 33"),
                ("UCI", "Programming", "E", "IN4MATX 43"),
                ("UCI", "Programming", "C", "I&C SCI 51"),
                ("UCI", "Programming", "F", "I&C SCI 6B"),
            }
        }
        self.assertEqual(expected, actual)

    def test_best_row_uses_smallest_single_option_not_sum_of_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "filtered_results").mkdir()
            (root / "district_csvs").mkdir()
            (root / "creating_districts").mkdir()
            (root / "creating_districts" / "districts.json").write_text(
                json.dumps(
                    {
                        "districts": {
                            "Example District": {
                                "colleges": ["College A", "College B"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            headers = ",".join(
                ["UC Name", "Group ID", "Set ID", "Num Required", "Receiving"]
                + [f"Courses Group {index}" for index in range(1, 11)]
            )
            option_cells = ",".join(
                f"A{index} (1.00); B{index} (1.00)"
                for index in range(1, 11)
            )
            (root / "filtered_results" / "College_A_filtered.csv").write_text(
                f"{headers}\n"
                f"UCLA,Intro2,A,1,COM SCI 32,{option_cells}\n",
                encoding="utf-8",
            )
            (root / "filtered_results" / "College_B_filtered.csv").write_text(
                f"{headers}\n"
                "UCLA,Intro2,A,1,COM SCI 32,C1 (1.00); C2 (1.00); C3 (1.00),,,,,,,,,\n",
                encoding="utf-8",
            )
            (root / "district_csvs" / "Example_District.csv").write_text(
                f"College Name,{headers}\n"
                f"College A,UCLA,Intro2,A,1,COM SCI 32,{option_cells}\n",
                encoding="utf-8",
            )

            issues = verify_district_csv("Example District", project_root=root)

        self.assertEqual([], issues)


if __name__ == "__main__":
    unittest.main()
