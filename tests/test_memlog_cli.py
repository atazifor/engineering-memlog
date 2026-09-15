import json

from tests.support import IsolatedTestCase, make_entry, write_jsonl


class MemlogCliTests(IsolatedTestCase):
    def test_add_generates_bookkeeping_and_preserves_unicode(self) -> None:
        payload = make_entry(title="Unicode failure — café 🧠")
        payload.pop("id")
        payload.pop("timestamp")

        result = self.run_memlog("add", "--json", json.dumps(payload, ensure_ascii=False))

        self.assertEqual(result.returncode, 0, result.stderr)
        stored = json.loads(self.log.read_text(encoding="utf-8"))
        self.assertEqual(stored["title"], payload["title"])
        self.assertRegex(stored["id"], r"^mem-\d+$")
        self.assertRegex(stored["timestamp"], r"^\d{4}-\d{2}-\d{2}T")

    def test_add_rejects_invalid_payloads(self) -> None:
        cases = [
            ("not-json", "Invalid JSON payload"),
            ("[]", "Payload must be a JSON object"),
            (json.dumps({"title": "incomplete"}), "Missing required fields"),
            (json.dumps(make_entry(tags="postgresql")), "tags"),
            (json.dumps(make_entry(confidence="high")), "confidence"),
            (json.dumps(make_entry(confidence=1.1)), "between 0.0 and 1.0"),
        ]
        for payload, expected in cases:
            with self.subTest(payload=payload):
                result = self.run_memlog("add", "--json", payload)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)

    def test_list_human_json_and_reverse_order(self) -> None:
        older = make_entry(id="old", title="Older lesson")
        newer = make_entry(id="new", title="Newer lesson")
        write_jsonl(self.log, [older, newer])

        human = self.run_memlog("list", "--limit", "2")
        reverse = self.run_memlog("list", "--reverse", "--json", "--limit", "2")

        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertLess(human.stdout.index("Older lesson"), human.stdout.index("Newer lesson"))
        rows = [json.loads(line) for line in reverse.stdout.splitlines()]
        self.assertEqual([row["id"] for row in rows], ["new", "old"])

    def test_search_is_case_insensitive_and_supports_json(self) -> None:
        write_jsonl(
            self.log,
            [
                make_entry(id="match"),
                make_entry(
                    id="miss",
                    title="Redis cache miss",
                    problem="A cached value was absent.",
                    cause="The cache key expired.",
                    fix="Repopulated the cache.",
                    prevention="Monitor cache-key expiry.",
                    artifact="cache.py",
                    tags=["redis"],
                ),
            ],
        )

        human = self.run_memlog("search", "POSTGRESQL")
        machine = self.run_memlog("search", "postgresql", "--json")

        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertIn("PostgreSQL connection timeout", human.stdout)
        self.assertEqual(json.loads(machine.stdout)["id"], "match")

    def test_search_no_hit_and_missing_or_empty_file_are_successful(self) -> None:
        missing = self.run_memlog("search", "redis")
        self.assertEqual(missing.returncode, 0, missing.stderr)
        self.assertEqual(missing.stdout.strip(), "No matches found.")

        self.log.write_text("", encoding="utf-8")
        empty = self.run_memlog("list", "--json")
        self.assertEqual(empty.returncode, 0, empty.stderr)
        self.assertEqual(empty.stdout, "")

    def test_malformed_and_non_object_lines_are_skipped(self) -> None:
        self.log.write_text(
            "not-json\n[]\nnull\n" + json.dumps(make_entry(id="valid")) + "\n",
            encoding="utf-8",
        )

        result = self.run_memlog("search", "postgresql", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["id"], "valid")
        self.assertIn("Skipping invalid JSON on line 1", result.stderr)
        self.assertIn("Skipping non-object JSON on line 2", result.stderr)
        self.assertIn("Skipping non-object JSON on line 3", result.stderr)

    def test_non_positive_limits_are_rejected(self) -> None:
        for command in ("search", "list"):
            for limit in ("0", "-1"):
                with self.subTest(command=command, limit=limit):
                    args = [command]
                    if command == "search":
                        args.append("postgresql")
                    args.extend(["--limit", limit])
                    result = self.run_memlog(*args)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("positive integer", result.stderr)


if __name__ == "__main__":
    import unittest

    unittest.main()
