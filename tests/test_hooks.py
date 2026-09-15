import json

from tests.support import PROMPT_HOOK, SESSION_HOOK, IsolatedTestCase, make_entry, write_jsonl


class PromptHookTests(IsolatedTestCase):
    def test_disabled_and_benign_prompts_are_silent(self) -> None:
        write_jsonl(self.log, [make_entry()])

        disabled = self.run_hook(
            PROMPT_HOOK,
            json.dumps({"prompt": "PostgreSQL timeout error"}),
            {"MEMLOG_PLUGIN_DISABLE": "1"},
        )
        benign = self.run_hook(PROMPT_HOOK, json.dumps({"prompt": "Add a button"}))

        self.assertEqual(disabled.returncode, 0, disabled.stderr)
        self.assertEqual(disabled.stdout, "")
        self.assertEqual(benign.returncode, 0, benign.stderr)
        self.assertEqual(benign.stdout, "")

    def test_symptom_without_hit_is_silent(self) -> None:
        write_jsonl(self.log, [make_entry()])
        result = self.run_hook(PROMPT_HOOK, json.dumps({"prompt": "Redis error"}))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_supported_prompt_fields_emit_valid_hook_json(self) -> None:
        write_jsonl(self.log, [make_entry()])

        for field in ("prompt", "userPrompt", "user_message", "text", "message"):
            with self.subTest(field=field):
                result = self.run_hook(
                    PROMPT_HOOK,
                    json.dumps({field: "PostgreSQL timeout error"}),
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                hook_output = payload["hookSpecificOutput"]
                self.assertEqual(hook_output["hookEventName"], "UserPromptSubmit")
                self.assertIn("PostgreSQL connection timeout", hook_output["additionalContext"])

    def test_raw_and_invalid_json_input_fall_back_to_prompt_text(self) -> None:
        write_jsonl(self.log, [make_entry()])
        for prompt in ("PostgreSQL timeout error", '{"broken": PostgreSQL timeout error}'):
            with self.subTest(prompt=prompt):
                result = self.run_hook(PROMPT_HOOK, prompt)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"],
                    "UserPromptSubmit",
                )


class SessionHookTests(IsolatedTestCase):
    def test_disabled_hook_is_silent(self) -> None:
        result = self.run_hook(SESSION_HOOK, env_updates={"MEMLOG_PLUGIN_DISABLE": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_auto_mode_injects_mandate_in_valid_json(self) -> None:
        self.install_healthy_cli_marker()

        result = self.run_hook(SESSION_HOOK)

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertIn("engineering-memlog-mandate v3", output["additionalContext"])

    def test_manual_mode_is_silent_without_matches(self) -> None:
        self.install_healthy_cli_marker()
        result = self.run_hook(SESSION_HOOK, env_updates={"MEMLOG_MANDATE": "manual"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_current_project_marker_suppresses_duplicate_mandate(self) -> None:
        self.install_healthy_cli_marker()
        (self.project / "CLAUDE.md").write_text(
            "<!-- engineering-memlog-mandate v3 -->\n",
            encoding="utf-8",
        )

        result = self.run_hook(SESSION_HOOK)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_project_match_injects_ranked_entry(self) -> None:
        self.install_healthy_cli_marker()
        (self.project / "package.json").write_text(
            json.dumps({"dependencies": {"react": "latest"}}),
            encoding="utf-8",
        )
        write_jsonl(
            self.log,
            [make_entry(title="React hydration mismatch", tags=["react"])],
        )

        result = self.run_hook(SESSION_HOOK, env_updates={"MEMLOG_MANDATE": "manual"})

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertIn("React hydration mismatch", output["additionalContext"])

    def test_missing_cli_warning_is_valid_hook_output(self) -> None:
        result = self.run_hook(SESSION_HOOK, env_updates={"MEMLOG_MANDATE": "manual"})
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertIn("write-half unavailable", output["additionalContext"])


if __name__ == "__main__":
    import unittest

    unittest.main()
