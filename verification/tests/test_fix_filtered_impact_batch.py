import tempfile
import unittest
from pathlib import Path

from verification.fix_filtered_impact_batch import selected_colleges, selected_rows


class FixFilteredImpactBatchTests(unittest.TestCase):
    def test_selects_unique_colleges_for_target_issue_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "impact.csv"
            path.write_text(
                "research_severity,root_cause,filtered_impact,cc,uc,receiving\n"
                "high,flattened_or,yes,A College,UCI,MATH 2A\n"
                "high,flattened_or,yes,A College,UCI,MATH 2B\n"
                "high,flattened_or,yes,B College,UCI,MATH 2A\n"
                "high,not_articulated_mismatch,yes,C College,UCI,MATH 2A\n"
                "info,flattened_or,no,D College,UCI,MATH 2A\n",
                encoding="utf-8",
            )

            rows = selected_rows(
                path,
                severity="high",
                root_cause="flattened_or",
                filtered_impact="yes",
            )

        self.assertEqual(3, len(rows))
        self.assertEqual(["A College", "B College"], selected_colleges(rows))


if __name__ == "__main__":
    unittest.main()
