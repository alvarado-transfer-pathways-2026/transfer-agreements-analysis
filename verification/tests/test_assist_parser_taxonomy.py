import json
import unittest

from verification.assist_parser import parse_assist_payload, taxonomy_for_assist_payload


def course(prefix, number, units=4.0, position=0):
    return {
        "type": "Course",
        "prefix": prefix,
        "courseNumber": number,
        "minUnits": units,
        "position": position,
    }


def sending_group(items, conjunction="And", position=0):
    return {
        "position": position,
        "courseConjunction": conjunction,
        "items": items,
    }


def articulation(receiving, sending):
    prefix, number = receiving.split(" ", 1)
    return {
        "articulation": {
            "type": "Course",
            "course": course(prefix, number),
            "sendingArticulation": sending,
        }
    }


def series_articulation(receiving_courses, sending):
    return {
        "articulation": {
            "type": "Series",
            "series": {
                "conjunction": "And",
                "courses": [
                    course(prefix, number, position=index)
                    for index, (prefix, number) in enumerate(receiving_courses)
                ],
            },
            "sendingArticulation": sending,
        }
    }


def payload(articulations):
    return {
        "result": {
            "templateAssets": "[]",
            "articulations": json.dumps(articulations),
        }
    }


def and_of_or_groups_payload():
    return payload(
        [
            {
                "articulation": {
                    "type": "Course",
                    "course": course("UC", "7"),
                    "sendingArticulation": {
                        "items": [
                            sending_group(
                                [course("CC", "1A", position=0), course("CC", "1B", position=1)],
                                "Or",
                                position=0,
                            ),
                            sending_group(
                                [course("CC", "2A", position=0), course("CC", "2B", position=1)],
                                "Or",
                                position=2,
                            ),
                        ],
                        "courseGroupConjunctions": [
                            {
                                "groupConjunction": "And",
                                "sendingCourseGroupBeginPosition": 0,
                                "sendingCourseGroupEndPosition": 2,
                            }
                        ],
                    },
                }
            }
        ]
    )


class AssistParserTaxonomyTests(unittest.TestCase):
    def test_classifies_all_representative_sending_shapes(self):
        data = payload(
            [
                articulation("UC 1", {"items": [sending_group([course("CC", "1")])]}),
                articulation("UC 2", {"items": [sending_group([course("CC", "2A", position=1), course("CC", "2B", position=2)])]}),
                articulation("UC 3", {"items": [sending_group([course("CC", "3A", position=1), course("CC", "3B", position=2)], "Or")]}),
                articulation(
                    "UC 4",
                    {
                        "items": [
                            sending_group([course("CC", "4A", position=1), course("CC", "4B", position=2)], position=1),
                            sending_group([course("CC", "4C", position=1), course("CC", "4D", position=2)], position=2),
                        ]
                    },
                ),
                articulation("UC 5", {"noArticulationReason": "No Course Articulated"}),
                series_articulation(
                    [("UC", "6A"), ("UC", "6B")],
                    {"items": [sending_group([course("CC", "6A"), course("CC", "6B", position=1)])]},
                ),
            ]
        )

        rows = parse_assist_payload(data)
        self.assertEqual((("CC 3A (4.00)",), ("CC 3B (4.00)",)), rows["UC 3"].sending_options)
        self.assertEqual((("CC 4A (4.00)", "CC 4B (4.00)"), ("CC 4C (4.00)", "CC 4D (4.00)")), rows["UC 4"].sending_options)

        taxonomy = taxonomy_for_assist_payload(data)
        self.assertIn("single_course", taxonomy["UC 1"])
        self.assertIn("pure_and", taxonomy["UC 2"])
        self.assertIn("pure_or", taxonomy["UC 3"])
        self.assertIn("or_of_and_groups", taxonomy["UC 4"])
        self.assertIn("no_articulation", taxonomy["UC 5"])
        self.assertIn("multi_course_receiving_series", taxonomy["UC 6A; UC 6B"])

    def test_expands_and_of_or_groups_to_valid_completion_paths(self):
        rows = parse_assist_payload(and_of_or_groups_payload())

        self.assertEqual(
            (
                ("CC 1A (4.00)", "CC 2A (4.00)"),
                ("CC 1A (4.00)", "CC 2B (4.00)"),
                ("CC 1B (4.00)", "CC 2A (4.00)"),
                ("CC 1B (4.00)", "CC 2B (4.00)"),
            ),
            rows["UC 7"].sending_options,
        )
        self.assertIn("or_of_and_groups", taxonomy_for_assist_payload(and_of_or_groups_payload())["UC 7"])


if __name__ == "__main__":
    unittest.main()
