import unittest

from course_group_semantics import (
    articulated_options,
    best_option,
    best_option_course_count,
    greedy_requirement_cover,
    is_articulated,
    option_is_satisfied,
    parse_course_group_cell,
)


class CourseGroupSemanticsTests(unittest.TestCase):
    def test_parses_or_options_with_and_courses(self):
        row = {
            "Courses Group 1": "CIS 22C (4.50); CIS 22A (4.50)",
            "Courses Group 2": "CIS 22CH (4.50); CIS 22B (4.50)",
        }

        self.assertEqual(
            [
                ("CIS 22C (4.50)", "CIS 22A (4.50)"),
                ("CIS 22CH (4.50)", "CIS 22B (4.50)"),
            ],
            articulated_options(row),
        )

    def test_not_articulated_blank_and_nan_are_not_options(self):
        self.assertIsNone(parse_course_group_cell("Not Articulated"))
        self.assertIsNone(parse_course_group_cell(""))
        self.assertIsNone(parse_course_group_cell("nan"))
        self.assertFalse(is_articulated({"Courses Group 1": "Not Articulated"}))

    def test_best_option_uses_one_course_group_not_all_groups(self):
        row = {
            "Courses Group 1": "A; B",
            "Courses Group 2": "C",
            "Courses Group 3": "D; E; F",
        }

        self.assertEqual(("C",), best_option(row))
        self.assertEqual(1, best_option_course_count(row))

    def test_option_satisfaction_requires_all_and_courses(self):
        option = ("CIS 22C", "CIS 22A")

        self.assertFalse(option_is_satisfied(option, {"CIS 22C"}))
        self.assertTrue(option_is_satisfied(option, {"CIS 22C", "CIS 22A"}))

    def test_greedy_cover_adds_whole_and_option(self):
        selected, req_to_option, uncovered = greedy_requirement_cover(
            ["req1"],
            {"req1": [("A", "B")]},
        )

        self.assertEqual({"A", "B"}, selected)
        self.assertEqual(("A", "B"), req_to_option["req1"])
        self.assertEqual(set(), uncovered)

    def test_greedy_cover_reuses_shared_courses_across_complete_options(self):
        selected, req_to_option, uncovered = greedy_requirement_cover(
            ["req1", "req2"],
            {
                "req1": [("A", "B")],
                "req2": [("A", "C")],
            },
        )

        self.assertEqual({"A", "B", "C"}, selected)
        self.assertEqual(("A", "B"), req_to_option["req1"])
        self.assertEqual(("A", "C"), req_to_option["req2"])
        self.assertEqual(set(), uncovered)


if __name__ == "__main__":
    unittest.main()
