import csv
import tempfile
import unittest
from pathlib import Path

from verification.summarize_assist_report import (
    filtered_impact_rows,
    issue_root_cause,
    summarize,
    write_filtered_impact_csv,
    write_triage_csv,
)


class SummarizeAssistReportTests(unittest.TestCase):
    def test_groups_likely_root_causes(self):
        report = {
            "metadata": {"agreement_count": 1},
            "agreements": [
                {
                    "uc": "University of California Irvine",
                    "cc": "Example College",
                    "issues": [
                        {
                            "receiving": "MATH 2A",
                            "issue_type": "flattened_or",
                            "expected": [["MATH 1A"], ["MATH 1AH"]],
                            "actual": [["MATH 1A", "MATH 1AH"]],
                            "exception_covered": False,
                        },
                        {
                            "receiving": "Requirement",
                            "issue_type": "missing_row",
                            "expected": [["ENGL 1A"]],
                            "actual": None,
                            "exception_covered": False,
                        },
                    ],
                }
            ],
        }

        summary = summarize(report)

        self.assertEqual(1, summary["by_root_cause"]["flattened_or"])
        self.assertEqual(1, summary["by_root_cause"]["non_course_requirement_placeholder"])
        self.assertEqual(1, summary["by_severity"]["high"])
        self.assertEqual(1, summary["by_severity"]["info"])
        self.assertEqual(2, summary["by_uc"]["UCI"])

    def test_detects_option_order_only(self):
        issue = {
            "issue_type": "sending_options_mismatch",
            "receiving": "MATH 54",
            "expected": [["B"], ["A"]],
            "actual": [["A"], ["B"]],
        }

        self.assertEqual("option_order_only", issue_root_cause(issue))

    def test_writes_triage_csv_sorted_by_severity(self):
        report = {
            "agreements": [
                {
                    "uc": "University of California Irvine",
                    "cc": "Example College",
                    "status": "fail",
                    "url": "https://example.test",
                    "view_by_key": "key",
                    "issues": [
                        {
                            "receiving": "Requirement",
                            "issue_type": "missing_row",
                            "message": "missing raw CSV row",
                            "expected": [["ENGL 1A"]],
                            "actual": None,
                            "exception_covered": False,
                        },
                        {
                            "receiving": "MATH 2A",
                            "issue_type": "flattened_or",
                            "message": "sending options differ",
                            "expected": [["MATH 1A"], ["MATH 1AH"]],
                            "actual": [["MATH 1A", "MATH 1AH"]],
                            "exception_covered": False,
                        },
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "triage.csv"
            counts = write_triage_csv(report, path)
            with path.open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

        self.assertEqual(1, counts["high"])
        self.assertEqual(1, counts["info"])
        self.assertEqual("high", rows[0]["severity"])
        self.assertEqual("flattened_or", rows[0]["root_cause"])
        self.assertIn("Fix exporter/parser", rows[0]["recommended_action"])

    def test_filtered_impact_marks_non_course_req_as_info(self):
        report = {
            "agreements": [
                {
                    "uc": "University of California Irvine",
                    "cc": "Example College",
                    "issues": [
                        {
                            "receiving": "NOT A CS REQUIREMENT",
                            "issue_type": "flattened_or",
                            "expected": [["A"], ["B"]],
                            "actual": [["A", "B"]],
                            "exception_covered": False,
                        }
                    ],
                }
            ]
        }

        rows = filtered_impact_rows(report)

        self.assertEqual("info", rows[0]["research_severity"])
        self.assertEqual("no", rows[0]["filtered_impact"])
        self.assertEqual(False, rows[0]["in_course_reqs"])

    def test_filtered_impact_detects_configured_requirement_difference(self):
        report = {
            "agreements": [
                {
                    "uc": "University of California Irvine",
                    "cc": "De Anza College",
                    "issues": [
                        {
                            "receiving": "MATH 2A",
                            "issue_type": "flattened_or",
                            "expected": [["MATH 1A (5.00)"], ["MATH 1AH (5.00)"]],
                            "actual": [["MATH 1A (5.00)", "MATH 1AH (5.00)"]],
                            "exception_covered": False,
                        }
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "filtered_results").mkdir()
            (root / "filtered_results" / "De_Anza_College_filtered.csv").write_text(
                "UC Name,Group ID,Set ID,Num Required,Receiving,Courses Group 1\n"
                "UCI,Calc1,A,1,MATH 2A,MATH 1A (5.00); MATH 1AH (5.00)\n",
                encoding="utf-8",
            )
            path = root / "impact.csv"
            counts = write_filtered_impact_csv(report, path, project_root=root)
            with path.open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

        self.assertEqual(1, counts["high"])
        self.assertEqual("yes", rows[0]["filtered_impact"])
        self.assertEqual("True", rows[0]["in_course_reqs"])


if __name__ == "__main__":
    unittest.main()
