from datetime import datetime, timezone
import unittest

from memlog_retrieval import rank_entries, score_entry
from tests.support import make_entry


NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)


class RetrievalRankingTests(unittest.TestCase):
    def test_short_query_uses_token_boundaries(self) -> None:
        go_entry = make_entry(id="go", title="Go JSON tags", tags=["go"])
        django_entry = make_entry(id="django", title="Django migration", tags=["django"])

        ranked = rank_entries([django_entry, go_entry], ["go"], NOW)

        self.assertEqual([entry["id"] for _, entry in ranked], ["go"])

    def test_prefix_matching_handles_close_identifier_variants_only(self) -> None:
        postgresql = make_entry(id="postgres", tags=["postgresql"])
        redistricting = make_entry(
            id="redistricting",
            title="Redistricting import",
            problem="A geographic import changed boundaries.",
            cause="The source map was outdated.",
            fix="Updated the map.",
            prevention="Pin the source revision.",
            artifact="map.json",
            repo="geo",
            service="maps",
            environment="local",
            tags=["redistricting"],
        )

        self.assertGreater(score_entry(postgresql, ["postgres"], NOW), 0.0)
        self.assertEqual(score_entry(redistricting, ["redis"], NOW), 0.0)

    def test_invalid_optional_ranking_metadata_does_not_break_search(self) -> None:
        entry = make_entry(
            id="invalid-metadata",
            confidence="unknown",
            timestamp="not-a-timestamp",
        )

        ranked = rank_entries([entry], ["postgresql"], NOW)

        self.assertEqual(ranked[0][1]["id"], "invalid-metadata")

    def test_equal_scores_and_timestamps_preserve_append_order(self) -> None:
        first = make_entry(id="first")
        second = make_entry(id="second")

        ranked = rank_entries([first, second], ["postgresql"], NOW)

        self.assertEqual([entry["id"] for _, entry in ranked], ["first", "second"])


if __name__ == "__main__":
    unittest.main()
