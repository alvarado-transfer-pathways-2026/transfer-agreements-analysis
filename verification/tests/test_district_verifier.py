import unittest

from verification.common import PROJECT_ROOT, load_csv_rows
from verification.verify_district_csv import normalize_district_row, recompute_district_rows


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


if __name__ == "__main__":
    unittest.main()

