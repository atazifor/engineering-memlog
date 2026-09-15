import json
import shlex
import sys

from tests.support import CONTEXT, SEARCH_PROMPT, SHORTLIST, IsolatedTestCase, make_entry, write_jsonl


class RetrievalScriptTests(IsolatedTestCase):
    def test_context_detects_manifest_language_and_framework(self) -> None:
        (self.project / "requirements.txt").write_text("fastapi==1.0\n", encoding="utf-8")
        (self.project / "app.py").write_text("print('hello')\n", encoding="utf-8")

        result = self.run_program(CONTEXT, "--cwd", str(self.project))

        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)
        self.assertIn("python", context["languages"])
        self.assertIn("fastapi", context["frameworks"])

    def test_shortlist_ranks_relevant_entries_and_honors_limit(self) -> None:
        write_jsonl(
            self.log,
            [
                make_entry(id="redis", title="Redis issue", tags=["redis"], repo="other"),
                make_entry(id="postgres", tags=["postgresql"], repo="sample-api"),
            ],
        )
        context = json.dumps({"repo": "sample-api", "tags": ["postgresql"]})

        result = self.run_program(
            SHORTLIST,
            "--file",
            str(self.log),
            "--limit",
            "1",
            input_text=context,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["id"], "postgres")

    def test_retrieval_scripts_skip_malformed_and_non_object_records(self) -> None:
        self.log.write_text(
            "bad\n[]\n" + json.dumps(make_entry(id="valid")) + "\n",
            encoding="utf-8",
        )

        shortlist = self.run_program(
            SHORTLIST,
            "--file",
            str(self.log),
            input_text=json.dumps({"tags": ["postgresql"]}),
        )
        prompt = self.run_program(
            SEARCH_PROMPT,
            "--file",
            str(self.log),
            input_text="PostgreSQL timeout error",
        )

        self.assertEqual(shortlist.returncode, 0, shortlist.stderr)
        self.assertEqual(prompt.returncode, 0, prompt.stderr)
        self.assertEqual(json.loads(shortlist.stdout)["id"], "valid")
        self.assertEqual(json.loads(prompt.stdout)["id"], "valid")

    def test_prompt_search_is_silent_for_benign_prompt_and_no_hit(self) -> None:
        write_jsonl(self.log, [make_entry()])

        benign = self.run_program(
            SEARCH_PROMPT,
            "--file",
            str(self.log),
            input_text="Add a navigation link",
        )
        no_hit = self.run_program(
            SEARCH_PROMPT,
            "--file",
            str(self.log),
            input_text="Kubernetes panic",
        )

        self.assertEqual(benign.returncode, 0, benign.stderr)
        self.assertEqual(benign.stdout, "")
        self.assertEqual(no_hit.returncode, 0, no_hit.stderr)
        self.assertEqual(no_hit.stdout, "")

    def test_prompt_search_emits_matching_unicode_entry(self) -> None:
        write_jsonl(self.log, [make_entry(title="PostgreSQL timeout — café")])

        result = self.run_program(
            SEARCH_PROMPT,
            "--file",
            str(self.log),
            input_text="Unexpected PostgreSQL timeout error",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["title"], "PostgreSQL timeout — café")

    def test_prompt_search_uses_query_coverage_for_ranking(self) -> None:
        write_jsonl(
            self.log,
            [
                make_entry(
                    id="partial",
                    title="Unexpected helper failure",
                    problem="A generic helper failed.",
                    tags=["python"],
                ),
                make_entry(
                    id="relevant",
                    title="Slugifier leaves underscores",
                    problem="The slugify test has an underscore failure.",
                    tags=["slugify", "underscore"],
                ),
            ],
        )

        result = self.run_program(
            SEARCH_PROMPT,
            "--file",
            str(self.log),
            "--limit",
            "2",
            input_text="Unexpected slugify underscore failure",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([row["id"] for row in rows], ["relevant", "partial"])

    def test_non_positive_script_limits_are_rejected(self) -> None:
        for program in (SHORTLIST, SEARCH_PROMPT):
            with self.subTest(program=program.name):
                result = self.run_program(program, "--limit", "0", input_text="{}")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("positive integer", result.stderr)

    def test_both_retrieval_scripts_read_the_external_provider(self) -> None:
        write_jsonl(self.provider_log, [make_entry(id="provider-hit")])
        env = self.provider_env()

        shortlist = self.run_program(
            SHORTLIST,
            "--limit",
            "1",
            input_text=json.dumps({"repo": "sample-api"}),
            env=env,
        )
        prompt = self.run_program(
            SEARCH_PROMPT,
            input_text="Unexpected PostgreSQL timeout error",
            env=env,
        )

        self.assertEqual(shortlist.returncode, 0, shortlist.stderr)
        self.assertEqual(json.loads(shortlist.stdout)["id"], "provider-hit")
        self.assertEqual(prompt.returncode, 0, prompt.stderr)
        self.assertEqual(json.loads(prompt.stdout)["id"], "provider-hit")

    def test_retrieval_scripts_reject_invalid_provider_entries_cleanly(self) -> None:
        invalid = make_entry(confidence="not-a-number")
        env = self.env.copy()
        env["ENGINEERING_MEMLOG_PROVIDER_COMMAND"] = shlex.join(
            [sys.executable, "-c", f"print({json.dumps(json.dumps(invalid))})"]
        )

        shortlist = self.run_program(
            SHORTLIST, input_text=json.dumps({"repo": "sample-api"}), env=env
        )
        prompt = self.run_program(
            SEARCH_PROMPT, input_text="PostgreSQL timeout error", env=env
        )

        for result in (shortlist, prompt):
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid entry", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_retrieval_output_byte_limit_keeps_complete_jsonl_records(self) -> None:
        first = make_entry(id="first")
        second = make_entry(id="second")
        write_jsonl(self.log, [first, second])
        one_line_bytes = len((json.dumps(first) + "\n").encode("utf-8"))

        shortlist = self.run_program(
            SHORTLIST,
            "--max-bytes",
            str(one_line_bytes),
            input_text=json.dumps({"repo": "sample-api"}),
        )
        prompt = self.run_program(
            SEARCH_PROMPT,
            "--max-bytes",
            str(one_line_bytes),
            input_text="PostgreSQL timeout error",
        )

        self.assertEqual(len(shortlist.stdout.splitlines()), 1)
        self.assertEqual(json.loads(shortlist.stdout)["id"], "first")
        self.assertEqual(len(prompt.stdout.splitlines()), 1)
        self.assertEqual(json.loads(prompt.stdout)["id"], "first")


if __name__ == "__main__":
    import unittest

    unittest.main()
