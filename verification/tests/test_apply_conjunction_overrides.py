import csv
import tempfile
import unittest
from pathlib import Path

from verification.apply_conjunction_overrides import apply_conjunction_overrides


class ApplyConjunctionOverridesTests(unittest.TestCase):
    def test_applies_de_anza_uci_override_to_results_and_filtered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "results").mkdir()
            (root / "filtered_results").mkdir()
            (root / "verification" / "fixtures").mkdir(parents=True)

            overrides = root / "verification" / "fixtures" / "conjunction_overrides.json"
            overrides.write_text(
                """
                {
                  "overrides": [{
                    "cc": "De Anza College",
                    "uc": "University of California Irvine",
                    "uc_abbr": "UCI",
                    "receiving": "MATH 2A",
                    "sending_options": [["MATH 1A (5.00)"], ["MATH 1AH (5.00)"], ["MATH 12 (5.00)"]]
                  }]
                }
                """,
                encoding="utf-8",
            )

            raw_path = root / "results" / "De_Anza_College_allUC.csv"
            raw_path.write_text(
                "UC Campus,CC,UC Course Requirement,Courses Group 1\n"
                "University of California Irvine,De Anza College,MATH 2A,MATH 1A (5.00); MATH 1AH (5.00); MATH 12 (5.00)\n",
                encoding="utf-8",
            )

            filtered_path = root / "filtered_results" / "De_Anza_College_filtered.csv"
            filtered_path.write_text(
                "UC Name,Group ID,Set ID,Num Required,Receiving,Courses Group 1\n"
                "UCI,Calc1,A,1,MATH 2A,MATH 1A (5.00); MATH 1AH (5.00); MATH 12 (5.00)\n",
                encoding="utf-8",
            )

            messages = apply_conjunction_overrides(
                project_root=root,
                overrides_path=overrides,
                cc_name="De Anza College",
                uc_name="UCI",
            )

            self.assertTrue(any(message.startswith("UPDATED") for message in messages))

            with raw_path.open(newline="", encoding="utf-8") as fh:
                row = next(csv.DictReader(fh))
            self.assertEqual("MATH 1A (5.00)", row["Courses Group 1"])
            self.assertEqual("MATH 1AH (5.00)", row["Courses Group 2"])
            self.assertEqual("MATH 12 (5.00)", row["Courses Group 3"])

            with filtered_path.open(newline="", encoding="utf-8") as fh:
                row = next(csv.DictReader(fh))
            self.assertEqual("MATH 1A (5.00)", row["Courses Group 1"])
            self.assertEqual("MATH 1AH (5.00)", row["Courses Group 2"])
            self.assertEqual("MATH 12 (5.00)", row["Courses Group 3"])


if __name__ == "__main__":
    unittest.main()

