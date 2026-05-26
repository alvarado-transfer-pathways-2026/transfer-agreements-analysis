import unittest

from verification.common import CsvIssue
from verification.report_conjunction_issues import is_probable_flattened_or, report_for_pairs


class ConjunctionReportTests(unittest.TestCase):
    def test_identifies_probable_flattened_or(self):
        issue = CsvIssue(
            "MATH 2A",
            "sending options differ",
            (("MATH 1A (5.00)",), ("MATH 1AH (5.00)",), ("MATH 12 (5.00)",)),
            (("MATH 1A (5.00)", "MATH 1AH (5.00)", "MATH 12 (5.00)"),),
        )
        self.assertTrue(is_probable_flattened_or(issue))

    def test_fixture_report_is_clear_after_temporary_overrides(self):
        lines, count = report_for_pairs(
            [("De Anza College", "University of California Irvine")],
            source="fixture",
            only_probable_flattened_or=True,
        )
        text = "\n".join(lines)
        self.assertEqual(0, count)
        self.assertIn("no conjunction issues found", text)


if __name__ == "__main__":
    unittest.main()
