import csv
import tempfile
import unittest
from pathlib import Path

from verification.export_filtered_from_raw import write_filtered_csv


class ExportFilteredFromRawTests(unittest.TestCase):
    def test_writes_targeted_filtered_csv_from_raw_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "results").mkdir()
            (root / "filtered_results").mkdir()
            (root / "results" / "De_Anza_College_allUC.csv").write_text(
                "UC Campus,CC,UC Course Requirement,Courses Group 1,Courses Group 2\n"
                "University of California Irvine,De Anza College,MATH 2A,MATH 1A (5.00),MATH 1AH (5.00)\n",
                encoding="utf-8",
            )

            path = write_filtered_csv("De Anza College", project_root=root, output_dir=root / "filtered_results")

            with path.open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

        self.assertEqual(1, len(rows))
        self.assertEqual("UCI", rows[0]["UC Name"])
        self.assertEqual("MATH 1A (5.00)", rows[0]["Courses Group 1"])
        self.assertEqual("MATH 1AH (5.00)", rows[0]["Courses Group 2"])


if __name__ == "__main__":
    unittest.main()
