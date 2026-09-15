import json
from datetime import datetime, timezone
from pathlib import Path
import unittest

from memlog_retrieval import rank_entries


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "entries.jsonl"
CASES = ROOT / "evals" / "retrieval-cases.json"
NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)


class RetrievalQualityTests(unittest.TestCase):
    def test_curated_queries_retrieve_the_expected_example(self) -> None:
        entries = [
            json.loads(line)
            for line in EXAMPLES.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cases = json.loads(CASES.read_text(encoding="utf-8"))

        for case in cases:
            with self.subTest(query=case["query"]):
                ranked = rank_entries(entries, [case["query"]], NOW)
                ids = [entry.get("id") for _, entry in ranked]
                expected = case["expected_id"]
                if expected is None:
                    self.assertEqual(ids, [])
                else:
                    self.assertIn(expected, ids[: case["max_rank"]])


if __name__ == "__main__":
    unittest.main()
