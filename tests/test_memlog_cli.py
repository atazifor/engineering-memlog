import json
import shutil
import stat
import subprocess
import sys

from tests.support import MEMLOG, REPO_ROOT, IsolatedTestCase, make_entry, write_jsonl


def make_new_entry(**overrides):
    entry = make_entry(**overrides)
    entry.pop("id")
    entry.pop("timestamp")
    return entry


class MemlogCliTests(IsolatedTestCase):
    def test_plugin_bin_exposes_the_bundled_cli_on_path(self) -> None:
        write_jsonl(self.log, [make_entry()])
        env = self.env.copy()
        env["PATH"] = f"{REPO_ROOT / 'bin'}:{env['PATH']}"

        result = subprocess.run(
            [
                "memlog",
                "--file",
                str(self.log),
                "search",
                "postgres timeout",
                "--json",
            ],
            text=True,
            capture_output=True,
            env=env,
            timeout=10,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["id"], "mem-test-1")

    def test_cli_can_import_retrieval_code_through_an_installed_symlink(self) -> None:
        installed = self.temp / "bin" / "memlog"
        installed.symlink_to(MEMLOG)
        result = self.run_program(
            installed,
            "--file",
            str(self.log),
            "search",
            "postgresql",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_and_retrieval_module_can_be_installed_as_copies(self) -> None:
        bin_dir = self.temp / "copied-bin"
        bin_dir.mkdir()
        installed = bin_dir / "memlog"
        shutil.copy2(MEMLOG, installed)
        shutil.copy2(REPO_ROOT / "memlog_retrieval.py", bin_dir / "memlog_retrieval.py")

        result = self.run_program(
            installed,
            "--file",
            str(self.log),
            "search",
            "postgresql",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_add_generates_bookkeeping_and_preserves_unicode(self) -> None:
        payload = make_new_entry(title="Unicode failure — café 🧠")

        result = self.run_memlog("add", "--json", json.dumps(payload, ensure_ascii=False))

        self.assertEqual(result.returncode, 0, result.stderr)
        stored = json.loads(self.log.read_text(encoding="utf-8"))
        self.assertEqual(stored["title"], payload["title"])
        self.assertRegex(stored["id"], r"^mem-[0-9a-f]{32}$")
        self.assertRegex(stored["timestamp"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertEqual(stored["schema_version"], 1)
        self.assertEqual(stat.S_IMODE(self.log.stat().st_mode), 0o600)

    def test_concurrent_adds_preserve_every_line_and_generate_unique_ids(self) -> None:
        payload = make_new_entry(title="Concurrent lesson")
        command = [
            sys.executable,
            str(MEMLOG),
            "--file",
            str(self.log),
            "add",
            "--json",
            json.dumps(payload),
        ]

        processes = [
            subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for _ in range(12)
        ]
        results = [process.communicate(timeout=10) for process in processes]

        for process, (_, stderr) in zip(processes, results):
            self.assertEqual(process.returncode, 0, stderr)
        rows = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({row["id"] for row in rows}), 12)
        self.assertTrue(all(row["schema_version"] == 1 for row in rows))

    def test_add_preserves_permissions_on_an_existing_shared_log(self) -> None:
        write_jsonl(self.log, [make_entry()])
        self.log.chmod(0o640)

        result = self.run_memlog("add", "--json", json.dumps(make_new_entry()))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE(self.log.stat().st_mode), 0o640)

    def test_add_rejects_invalid_payloads(self) -> None:
        cases = [
            ("not-json", "Invalid JSON payload"),
            ("[]", "Payload must be a JSON object"),
            (json.dumps({"title": "incomplete"}), "Missing required fields"),
            (json.dumps(make_new_entry(tags="postgresql")), "tags"),
            (json.dumps(make_new_entry(tags=["postgresql", ""])), "tags"),
            (json.dumps(make_new_entry(title="")), "title"),
            (json.dumps(make_new_entry(problem=42)), "problem"),
            (json.dumps(make_new_entry(confidence=True)), "confidence"),
            (json.dumps(make_new_entry(confidence="high")), "confidence"),
            (json.dumps(make_new_entry(confidence=1.1)), "between 0.0 and 1.0"),
            (json.dumps(make_new_entry(schema_version=2)), "schema_version"),
        ]
        for payload, expected in cases:
            with self.subTest(payload=payload):
                result = self.run_memlog("add", "--json", payload)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)

    def test_add_rejects_caller_supplied_bookkeeping_fields(self) -> None:
        for field in ("id", "timestamp"):
            with self.subTest(field=field):
                payload = make_new_entry()
                payload[field] = "caller-value"

                result = self.run_memlog("add", "--json", json.dumps(payload))

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("generated by memlog", result.stderr)

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

    def test_search_matches_noncontiguous_terms_and_ranks_by_relevance(self) -> None:
        write_jsonl(
            self.log,
            [
                make_entry(
                    id="partial",
                    timestamp="2026-09-15T00:00:00Z",
                    title="Slugify helper cleanup",
                    problem="A formatting helper needs maintenance.",
                    tags=["python"],
                    confidence=1.0,
                ),
                make_entry(
                    id="relevant",
                    timestamp="2025-01-01T00:00:00Z",
                    title="Slugifier leaves underscores in cache keys",
                    problem="The slugify test reports a failure for underscore input.",
                    cause="Underscore separators are not normalized.",
                    tags=["slugify", "underscore"],
                    confidence=0.25,
                ),
            ],
        )

        result = self.run_memlog(
            "search",
            "slugify underscore failure",
            "--json",
            "--limit",
            "2",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([row["id"] for row in rows], ["relevant"])

    def test_search_boosts_an_exact_phrase_over_scattered_terms(self) -> None:
        write_jsonl(
            self.log,
            [
                make_entry(
                    id="scattered",
                    timestamp="2026-09-15T00:00:00Z",
                    title="Frozen install failure",
                    problem="The dependency step stopped.",
                    cause="The lockfile changed.",
                    confidence=1.0,
                ),
                make_entry(
                    id="phrase",
                    timestamp="2025-01-01T00:00:00Z",
                    title="Frozen lockfile install failure",
                    confidence=0.25,
                ),
            ],
        )

        result = self.run_memlog(
            "search",
            "frozen lockfile install failure",
            "--json",
            "--limit",
            "2",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([row["id"] for row in rows], ["phrase", "scattered"])

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

    def test_validate_reports_schema_errors_and_duplicate_ids_without_mutating(self) -> None:
        valid = make_entry(id="duplicate")
        duplicate = make_entry(id="duplicate", title="Second copy")
        incomplete = {"id": "incomplete", "title": "Missing fields"}
        unsupported = make_entry(id="unsupported", schema_version=2)
        original = "".join(
            (
                json.dumps(valid) + "\n",
                json.dumps(duplicate) + "\n",
                json.dumps(incomplete) + "\n",
                json.dumps(unsupported) + "\n",
                "not-json\n",
            )
        )
        self.log.write_text(original, encoding="utf-8")

        result = self.run_memlog("validate", "--json")

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["valid"], 1)
        self.assertEqual(report["invalid"], 4)
        self.assertTrue(any("duplicate id" in error["message"] for error in report["errors"]))
        self.assertTrue(any("invalid JSON" in error["message"] for error in report["errors"]))
        self.assertTrue(any("schema_version" in error["message"] for error in report["errors"]))
        self.assertEqual(self.log.read_text(encoding="utf-8"), original)

    def test_validate_accepts_legacy_entries_without_schema_version(self) -> None:
        write_jsonl(self.log, [make_entry()])

        result = self.run_memlog("validate", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"valid": 1, "invalid": 0, "errors": []})

    def test_backend_errors_are_reported_without_a_traceback(self) -> None:
        for command in (("search", "postgresql"), ("list",), ("validate",)):
            with self.subTest(command=command[0]):
                result = self.run_program(
                    MEMLOG,
                    "--file",
                    str(self.project),
                    *command,
                    "--json",
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn("backend unavailable", result.stderr.lower())
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    import unittest

    unittest.main()
