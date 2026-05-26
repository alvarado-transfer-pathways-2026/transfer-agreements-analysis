import unittest

from verification.verify_overrides import verify_overrides


class VerifyOverridesTests(unittest.TestCase):
    def test_reviewed_overrides_match_fixture_source(self):
        self.assertEqual([], verify_overrides(source="fixture"))


if __name__ == "__main__":
    unittest.main()
