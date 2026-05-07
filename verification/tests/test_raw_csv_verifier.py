import unittest

from verification.verify_raw_csv import verify_raw_csv


class RawCsvVerifierTests(unittest.TestCase):
    def test_de_anza_ucsd_matches_golden_fixture(self):
        issues = verify_raw_csv(
            "De Anza College",
            "University of California San Diego",
            source="fixture",
        )
        self.assertEqual([], issues)

    def test_de_anza_uci_matches_after_temporary_conjunction_overrides(self):
        issues = verify_raw_csv(
            "De Anza College",
            "University of California Irvine",
            source="fixture",
        )
        self.assertEqual([], issues)


if __name__ == "__main__":
    unittest.main()
