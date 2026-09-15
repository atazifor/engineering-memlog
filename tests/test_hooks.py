import json
import shutil

from tests.support import (
    POST_TOOL_HOOK,
    PROMPT_HOOK,
    REPO_ROOT,
    SESSION_HOOK,
    IsolatedTestCase,
    make_entry,
    write_jsonl,
)


class PostToolRecallHookTests(IsolatedTestCase):
    def payload(
        self,
        *,
        event: str = "PostToolUse",
        command: str = "python3 -m unittest test_integration.py",
        stdout: str = "",
        stderr: str = "",
        error: str = "",
    ) -> str:
        value = {
            "hook_event_name": event,
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "tool_response": {"stdout": stdout, "stderr": stderr},
        }
        if error:
            value["error"] = error
        return json.dumps(value)

    def test_piped_test_failure_triggers_recall_even_when_bash_succeeds(self) -> None:
        write_jsonl(
            self.log,
            [
                make_entry(
                    id="upstream-status",
                    title="Check upstream status before parsing the response body",
                    problem="A JSONDecodeError masked an upstream HTTP 404 response.",
                    cause="The integration parsed a plain-text error body first.",
                    tags=["python", "http", "integration", "error-handling"],
                )
            ],
        )
        before = self.log.read_bytes()
        result = self.run_hook(
            POST_TOOL_HOOK,
            self.payload(
                command="python3 -m unittest test_integration.py 2>&1 | tail -20",
                stdout=(
                    "Traceback (most recent call last):\n"
                    "json.decoder.JSONDecodeError: Expecting value\n"
                    "AssertionError: IntegrationError not raised\n"
                    "FAILED (failures=1)\n"
                ),
            ),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PostToolUse")
        self.assertIn("upstream-status", output["additionalContext"])
        self.assertIn("untrusted hypothesis", output["additionalContext"])
        self.assertEqual(self.log.read_bytes(), before)

    def test_successful_test_and_routine_shell_failure_are_silent(self) -> None:
        write_jsonl(self.log, [make_entry()])
        successful_test = self.run_hook(
            POST_TOOL_HOOK,
            self.payload(stdout="Ran 10 tests in 0.02s\n\nOK\n"),
        )
        missing_file = self.run_hook(
            POST_TOOL_HOOK,
            self.payload(
                event="PostToolUseFailure",
                command="ls file-that-does-not-exist",
                error="Exit code 2: No such file or directory",
            ),
        )

        self.assertEqual(successful_test.returncode, 0, successful_test.stderr)
        self.assertEqual(successful_test.stdout, "")
        self.assertEqual(missing_file.returncode, 0, missing_file.stderr)
        self.assertEqual(missing_file.stdout, "")

    def test_interrupted_diagnostic_is_silent(self) -> None:
        payload = json.loads(
            self.payload(
                event="PostToolUseFailure",
                command="cargo test --workspace",
                error="Command exited with status 130",
            )
        )
        payload["is_interrupt"] = True
        result = self.run_hook(POST_TOOL_HOOK, json.dumps(payload))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_standard_piped_go_test_failure_triggers_recall(self) -> None:
        write_jsonl(
            self.log,
            [
                make_entry(
                    id="go-widget-race",
                    title="Widget test fails when workers share state",
                    problem="TestWidget fails under the Go test runner.",
                    tags=["go", "testing", "widget"],
                )
            ],
        )
        result = self.run_hook(
            POST_TOOL_HOOK,
            self.payload(
                command="go test ./... 2>&1 | tail -20",
                stdout=(
                    "--- FAIL: TestWidget (0.01s)\n"
                    "    widget_test.go:42: values differ\n"
                    "FAIL\nFAIL\texample/widget\t0.015s\n"
                ),
            ),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("go-widget-race", result.stdout)

    def test_commands_that_only_display_failure_text_are_silent(self) -> None:
        for command in (
            "rg AssertionError tests",
            "grep -R 'FAILED' .",
            "cat saved-test-output.txt",
            "git diff",
            "cd src && rg 'Traceback' .",
        ):
            with self.subTest(command=command):
                result = self.run_hook(
                    POST_TOOL_HOOK,
                    self.payload(
                        command=command,
                        stdout="Traceback (most recent call last):\nAssertionError\nFAILED",
                    ),
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_later_diagnostic_segment_is_not_suppressed_by_inspection(self) -> None:
        write_jsonl(
            self.log,
            [
                make_entry(
                    id="go-widget-compound",
                    title="Widget test fails under Go",
                    problem="TestWidget fails in the widget package.",
                    tags=["go", "testing", "widget"],
                )
            ],
        )
        result = self.run_hook(
            POST_TOOL_HOOK,
            self.payload(
                command="git diff --check && go test ./... 2>&1 | tail -20",
                stdout=(
                    "--- FAIL: TestWidget (0.01s)\n"
                    "FAIL\nFAIL\texample/widget\t0.015s\n"
                ),
            ),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("go-widget-compound", result.stdout)

    def test_trivial_test_invocation_errors_are_silent(self) -> None:
        cases = (
            (
                "pytest does-not-exist.py",
                "ERROR: file or directory not found: does-not-exist.py",
            ),
            ("pytest", "collected 0 items\nno tests ran"),
            (
                "cargo test --wat",
                "error: unrecognized option '--wat'\nUsage: cargo test",
            ),
        )
        for command, output in cases:
            with self.subTest(command=command):
                result = self.run_hook(
                    POST_TOOL_HOOK,
                    self.payload(
                        event="PostToolUseFailure",
                        command=command,
                        error=output,
                    ),
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_meaningful_failure_with_no_match_reports_search_and_next_step(self) -> None:
        write_jsonl(self.log, [make_entry(tags=["postgresql"])])
        before = self.log.read_bytes()
        result = self.run_hook(
            POST_TOOL_HOOK,
            self.payload(
                command="npm run build",
                stdout="BUILD FAILED: webpack module federation conflict",
            ),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("no candidate lesson matched", context)
        self.assertIn("continue with local evidence", context)
        self.assertIn("debug-with-memlog", context)
        self.assertEqual(self.log.read_bytes(), before)

    def test_failed_diagnostic_command_triggers_without_full_stderr(self) -> None:
        result = self.run_hook(
            POST_TOOL_HOOK,
            self.payload(
                event="PostToolUseFailure",
                command="cargo test --workspace",
                error="Command exited with status 101",
            ),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PostToolUseFailure")
        self.assertIn("configured store was searched", output["additionalContext"])

    def test_disabled_hook_is_silent(self) -> None:
        result = self.run_hook(
            POST_TOOL_HOOK,
            self.payload(stdout="AssertionError: expected true"),
            {"MEMLOG_PLUGIN_DISABLE": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_backend_outage_is_distinct_from_no_match(self) -> None:
        write_jsonl(self.log, [make_entry()])
        before = self.log.read_bytes()
        result = self.run_hook(
            POST_TOOL_HOOK,
            self.payload(stdout="AssertionError: expected true"),
            {"ENGINEERING_MEMLOG_PROVIDER_COMMAND": str(self.temp / "missing")},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("backend unavailable", context)
        self.assertIn("do not treat this as a no-match", context)
        self.assertEqual(self.log.read_bytes(), before)


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
                self.assertRegex(
                    hook_output["additionalContext"],
                    r"untrusted\s+hypothesis",
                )

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

    def test_prompt_hook_reads_external_provider_and_reports_outage(self) -> None:
        write_jsonl(self.provider_log, [make_entry(id="provider-hook-hit")])
        available = self.run_hook(
            PROMPT_HOOK,
            json.dumps({"prompt": "PostgreSQL timeout error"}),
            self.provider_env(),
        )
        unavailable = self.run_hook(
            PROMPT_HOOK,
            json.dumps({"prompt": "PostgreSQL timeout error"}),
            {"ENGINEERING_MEMLOG_PROVIDER_COMMAND": str(self.temp / "missing")},
        )

        self.assertIn("provider-hook-hit", available.stdout)
        self.assertIn("backend unavailable", unavailable.stdout.lower())
        self.assertIn("continue local diagnosis", unavailable.stdout.lower())

    def test_prompt_hook_honors_context_byte_limit(self) -> None:
        write_jsonl(self.log, [make_entry(problem="timeout " * 1000)])

        result = self.run_hook(
            PROMPT_HOOK,
            json.dumps({"prompt": "PostgreSQL timeout error"}),
            {"MEMLOG_PLUGIN_MAX_CONTEXT_BYTES": "1"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


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
        self.assertIn("engineering-memlog-mandate v5", output["additionalContext"])

    def test_manual_mode_is_silent_without_matches(self) -> None:
        self.install_healthy_cli_marker()
        result = self.run_hook(SESSION_HOOK, env_updates={"MEMLOG_MANDATE": "manual"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_current_project_marker_suppresses_duplicate_mandate(self) -> None:
        self.install_healthy_cli_marker()
        (self.project / "CLAUDE.md").write_text(
            "<!-- engineering-memlog-mandate v5 -->\n",
            encoding="utf-8",
        )

        result = self.run_hook(SESSION_HOOK)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_codex_payload_cwd_suppresses_duplicate_mandate(self) -> None:
        self.install_healthy_cli_marker()
        (self.project / "AGENTS.md").write_text(
            "<!-- engineering-memlog-mandate v5 -->\n",
            encoding="utf-8",
        )
        env = self.env.copy()
        env.pop("CLAUDE_PROJECT_DIR", None)
        env["PLUGIN_ROOT"] = str(REPO_ROOT)

        result = self.run_hook(
            SESSION_HOOK,
            json.dumps({"hook_event_name": "SessionStart", "cwd": str(self.project)}),
            env,
        )

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
        self.assertRegex(output["additionalContext"], r"untrusted\s+hypothesis")

    def test_bundled_cli_avoids_warning_when_global_cli_is_missing(self) -> None:
        result = self.run_hook(SESSION_HOOK, env_updates={"MEMLOG_MANDATE": "manual"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_missing_bundled_cli_warning_is_valid_hook_output(self) -> None:
        broken_plugin = self.temp / "broken-plugin"
        broken_bin = broken_plugin / "bin"
        broken_bin.mkdir(parents=True)
        shutil.copy2(REPO_ROOT / "bin" / "memlog", broken_bin / "memlog")
        result = self.run_hook(
            SESSION_HOOK,
            env_updates={
                "CLAUDE_PLUGIN_ROOT": str(broken_plugin),
                "MEMLOG_MANDATE": "manual",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertIn("write-half unavailable", output["additionalContext"])

    def test_session_hook_reads_external_provider_and_reports_outage(self) -> None:
        self.install_healthy_cli_marker()
        write_jsonl(
            self.provider_log,
            [make_entry(id="provider-session-hit", tags=["react"])],
        )
        (self.project / "package.json").write_text(
            json.dumps({"dependencies": {"react": "latest"}}), encoding="utf-8"
        )

        available = self.run_hook(
            SESSION_HOOK,
            env_updates={**self.provider_env(), "MEMLOG_MANDATE": "manual"},
        )
        unavailable = self.run_hook(
            SESSION_HOOK,
            env_updates={
                "ENGINEERING_MEMLOG_PROVIDER_COMMAND": str(self.temp / "missing"),
                "MEMLOG_MANDATE": "manual",
            },
        )

        self.assertIn("provider-session-hit", available.stdout)
        self.assertIn("backend unavailable", unavailable.stdout.lower())

    def test_session_hook_honors_context_byte_limit(self) -> None:
        self.install_healthy_cli_marker()
        (self.project / "package.json").write_text(
            json.dumps({"dependencies": {"react": "latest"}}), encoding="utf-8"
        )
        write_jsonl(
            self.log,
            [make_entry(tags=["react"], problem="hydration mismatch " * 1000)],
        )

        result = self.run_hook(
            SESSION_HOOK,
            env_updates={
                "MEMLOG_MANDATE": "manual",
                "MEMLOG_PLUGIN_MAX_CONTEXT_BYTES": "1",
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    import unittest

    unittest.main()
