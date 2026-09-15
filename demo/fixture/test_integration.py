import unittest

from integration import IntegrationError, decode_download


class IntegrationTests(unittest.TestCase):
    def test_preserves_upstream_status_before_parsing(self) -> None:
        with self.assertRaisesRegex(
            IntegrationError,
            "Upstream returned 404: endpoint is disabled",
        ):
            decode_download(404, "endpoint is disabled")


if __name__ == "__main__":
    unittest.main()
