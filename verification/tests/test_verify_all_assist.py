import tempfile
import unittest
from pathlib import Path

from verification.tests.test_assist_parser_taxonomy import articulation, course, payload, sending_group
from verification.verify_all_assist import build_report


class VerifyAllAssistTests(unittest.TestCase):
    def test_report_classifies_flattened_or_and_unclassified_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "results").mkdir()
            (root / "cc_agreements" / "Example_College").mkdir(parents=True)
            (root / "cc_agreements" / "Example_College" / "agreements.txt").write_text(
                "University of California Example: https://assist.org/transfer/results?viewByKey=example-key\n",
                encoding="utf-8",
            )
            (root / "results" / "Example_College_allUC.csv").write_text(
                "UC Campus,CC,UC Course Requirement,Courses Group 1\n"
                "University of California Example,Example College,UC 1,CC 1A (4.00); CC 1B (4.00)\n",
                encoding="utf-8",
            )

            assist_payload = payload(
                [
                    articulation(
                        "UC 1",
                        {
                            "items": [
                                sending_group(
                                    [course("CC", "1A", position=1), course("CC", "1B", position=2)],
                                    "Or",
                                )
                            ]
                        },
                    )
                ]
            )

            report = build_report(
                [
                    {
                        "cc": "Example College",
                        "uc": "University of California Example",
                        "url": "https://assist.org/transfer/results?viewByKey=example-key",
                    }
                ],
                project_root=root,
                source="live",
                fetch_payload=lambda key: assist_payload,
            )

        self.assertEqual(1, report["metadata"]["unreviewed_mismatch_count"])
        self.assertEqual(0, report["metadata"]["unclassified_count"])
        issue = report["agreements"][0]["issues"][0]
        self.assertEqual("flattened_or", issue["issue_type"])

    def test_duplicate_assist_receiving_rows_are_metadata_when_merged_csv_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "results").mkdir()
            (root / "results" / "Example_College_allUC.csv").write_text(
                "UC Campus,CC,UC Course Requirement,Courses Group 1,Courses Group 2\n"
                "University of California Example,Example College,UC 1,CC 1A (4.00),CC 1B (4.00)\n",
                encoding="utf-8",
            )

            assist_payload = payload(
                [
                    articulation(
                        "UC 1",
                        {"items": [sending_group([course("CC", "1A")], "And")]},
                    ),
                    articulation(
                        "UC 1",
                        {"items": [sending_group([course("CC", "1B")], "And")]},
                    ),
                ]
            )

            report = build_report(
                [
                    {
                        "cc": "Example College",
                        "uc": "University of California Example",
                        "url": "https://assist.org/transfer/results?viewByKey=example-key",
                    }
                ],
                project_root=root,
                source="live",
                fetch_payload=lambda key: assist_payload,
            )

        agreement = report["agreements"][0]
        self.assertEqual(0, report["metadata"]["unreviewed_mismatch_count"])
        self.assertEqual([], agreement["issues"])
        self.assertEqual(["UC 1"], agreement["duplicate_receiving_rows"]["assist"])

    def test_duplicate_raw_receiving_rows_are_metadata_when_merged_options_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "results").mkdir()
            (root / "results" / "Example_College_allUC.csv").write_text(
                "UC Campus,CC,UC Course Requirement,Courses Group 1\n"
                "University of California Example,Example College,UC 1,CC 1A (4.00)\n"
                "University of California Example,Example College,UC 1,CC 1B (4.00)\n",
                encoding="utf-8",
            )

            assist_payload = payload(
                [
                    articulation(
                        "UC 1",
                        {
                            "items": [
                                sending_group(
                                    [course("CC", "1A", position=1), course("CC", "1B", position=2)],
                                    "Or",
                                )
                            ]
                        },
                    )
                ]
            )

            report = build_report(
                [
                    {
                        "cc": "Example College",
                        "uc": "University of California Example",
                        "url": "https://assist.org/transfer/results?viewByKey=example-key",
                    }
                ],
                project_root=root,
                source="live",
                fetch_payload=lambda key: assist_payload,
            )

        agreement = report["agreements"][0]
        self.assertEqual(0, report["metadata"]["unreviewed_mismatch_count"])
        self.assertEqual([], agreement["issues"])
        self.assertEqual({"UC 1": 2}, agreement["duplicate_receiving_rows"]["raw_csv"])


if __name__ == "__main__":
    unittest.main()
