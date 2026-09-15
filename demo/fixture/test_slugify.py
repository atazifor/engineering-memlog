import unittest

from slugify import slugify


class SlugifyTests(unittest.TestCase):
    def test_normalizes_spaces_and_underscores(self) -> None:
        self.assertEqual(slugify("User_Profile Name"), "user-profile-name")


if __name__ == "__main__":
    unittest.main()
