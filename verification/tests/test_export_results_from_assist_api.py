import csv
import tempfile
import unittest
from pathlib import Path

from verification.export_results_from_assist_api import export_cc
from verification.tests.test_assist_parser_taxonomy import articulation, course, payload, sending_group


class ExportResultsFromAssistApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        agreement_dir = self.root / "cc_agreements" / "Example_College"
        agreement_dir.mkdir(parents=True)
        (agreement_dir / "agreements.txt").write_text(
            "University of California Example: https://assist.org/transfer/results?viewByKey=example-key\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def fake_payload(self, _key):
        return payload(
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
                ),
                articulation(
                    "UC 2",
                    {
                        "items": [
                            sending_group(
                                [course("CC", "2A", position=1), course("CC", "2B", position=2)],
                                "And",
                            )
                        ]
                    },
                ),
            ]
        )

    def test_dry_run_does_not_write_csv(self):
        output_dir = self.root / "generated"

        summary = export_cc(
            "Example College",
            project_root=self.root,
            output_dir=output_dir,
            dry_run=True,
            fetch_payload=self.fake_payload,
        )

        self.assertEqual(2, summary.row_count)
        self.assertFalse(summary.path.exists())

    def test_write_preserves_or_and_and_group_shapes(self):
        output_dir = self.root / "generated"

        summary = export_cc(
            "Example College",
            project_root=self.root,
            output_dir=output_dir,
            dry_run=False,
            fetch_payload=self.fake_payload,
        )

        with summary.path.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))

        self.assertEqual("CC 1A (4.00)", rows[0]["Courses Group 1"])
        self.assertEqual("CC 1B (4.00)", rows[0]["Courses Group 2"])
        self.assertEqual("CC 2A (4.00); CC 2B (4.00)", rows[1]["Courses Group 1"])
        self.assertEqual("", rows[1]["Courses Group 2"])


if __name__ == "__main__":
    unittest.main()
