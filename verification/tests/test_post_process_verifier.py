import unittest

from verification.common import PROJECT_ROOT, load_csv_rows
from verification.verify_post_process import normalize_filtered_row, recompute_filtered_rows, verify_post_process


class PostProcessVerifierTests(unittest.TestCase):
    def test_de_anza_full_filtered_csv_matches_recomputed_post_process(self):
        issues = verify_post_process("De Anza College")
        self.assertEqual([], issues)

    def test_de_anza_uci_ucsd_subset_matches_golden_fixture(self):
        fixture_path = (
            PROJECT_ROOT
            / "verification"
            / "fixtures"
            / "post_process"
            / "de_anza_uci_ucsd_expected_subset.csv"
        )
        expected = {normalize_filtered_row(row) for row in load_csv_rows(fixture_path)}
        actual = {
            normalize_filtered_row(row)
            for row in recompute_filtered_rows(PROJECT_ROOT, "De Anza College")
            if row["UC Name"] in {"UCI", "UCSD"}
        }
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()

