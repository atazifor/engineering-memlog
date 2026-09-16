import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProjectFileTests(unittest.TestCase):
    def test_plugin_json_files_parse(self) -> None:
        for path in (
            ROOT / "plugin.json",
            ROOT / ".claude-plugin" / "plugin.json",
            ROOT / ".claude-plugin" / "marketplace.json",
            ROOT / ".agents" / "plugins" / "marketplace.json",
            ROOT / ".codex-plugin" / "plugin.json",
            ROOT / "hooks" / "codex-hooks.json",
            ROOT / "hooks" / "claude-hooks.json",
        ):
            with self.subTest(path=path):
                self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_host_hook_manifests_use_supported_failure_events(self) -> None:
        codex = json.loads(
            (ROOT / "hooks" / "codex-hooks.json").read_text(encoding="utf-8")
        )["hooks"]
        claude = json.loads(
            (ROOT / "hooks" / "claude-hooks.json").read_text(encoding="utf-8")
        )["hooks"]
        self.assertIn("PostToolUse", codex)
        self.assertNotIn("PostToolUseFailure", codex)
        for event in ("PostToolUse", "PostToolUseFailure"):
            with self.subTest(event=event):
                registration = claude[event][0]
                self.assertEqual(registration["matcher"], "Bash")
                self.assertIn(
                    "post-tool-recall.py",
                    registration["hooks"][0]["command"],
                )

    def test_claude_code_loads_one_hook_manifest_with_its_placeholders(self) -> None:
        # Claude Code loads hooks/hooks.json in addition to the manifest's
        # "hooks" path and leaves any other $VAR empty. A second manifest there
        # runs every hook twice, and one written for another host runs as
        # "/hooks/<script>" and fails.
        manifest_hooks = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )["hooks"]
        loaded = (ROOT / manifest_hooks).resolve()
        default = ROOT / "hooks" / "hooks.json"
        self.assertTrue(loaded.is_file())
        self.assertTrue(
            not default.exists() or default.resolve() == loaded,
            "hooks/hooks.json would load alongside the manifest hook file",
        )
        allowed = {"CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DATA", "CLAUDE_PROJECT_DIR"}
        hooks = json.loads(loaded.read_text(encoding="utf-8"))["hooks"]
        for event, registrations in hooks.items():
            for registration in registrations:
                for hook in registration["hooks"]:
                    command = hook.get("command", "")
                    with self.subTest(event=event, command=command):
                        self.assertLessEqual(
                            set(re.findall(r"\$\{?(\w+)", command)), allowed
                        )
                        self.assertIn("${CLAUDE_PLUGIN_ROOT}", command)

    def test_manifests_route_to_their_host_contract(self) -> None:
        claude = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        codex = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        portable = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        codex_marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(claude["hooks"], "./hooks/claude-hooks.json")
        self.assertNotIn("hooks", codex)
        self.assertEqual(
            codex_marketplace["plugins"][0]["source"],
            {"source": "local", "path": "."},
        )
        self.assertEqual(
            portable["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )

    def test_every_manifest_version_matches_the_cli(self) -> None:
        versions = {
            json.loads(path.read_text(encoding="utf-8"))["version"]
            for path in (
                ROOT / "plugin.json",
                ROOT / ".claude-plugin" / "plugin.json",
                ROOT / ".codex-plugin" / "plugin.json",
            )
        }
        self.assertEqual(versions, {"0.3.0"})

    def test_portable_manifest_matches_published_schema_constraints(self) -> None:
        manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        allowed = {
            "$schema",
            "name",
            "version",
            "description",
            "author",
            "homepage",
            "repository",
            "license",
            "keywords",
            "extensions",
        }
        self.assertEqual(
            manifest["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )
        self.assertFalse(set(manifest) - allowed)
        self.assertRegex(
            manifest["name"],
            re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$"),
        )
        self.assertLessEqual(len(manifest["name"]), 64)

    def test_documentation_has_no_obsolete_engineering_memory_paths(self) -> None:
        for path in (ROOT / "CLAUDE.md", ROOT / "commands" / "recall.md"):
            with self.subTest(path=path):
                self.assertNotIn(
                    "~/engineering-memory",
                    path.read_text(encoding="utf-8"),
                )

    def test_plugin_install_docs_use_the_bundled_cli(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertRegex(readme, r"plugin's `bin/`\s+directory")
        self.assertIn("without a separate clone or `make install`", readme)
        self.assertNotIn("only adds the read-side hooks", readme)

    def test_security_docs_disclose_model_context_and_custom_provider_flow(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("active agent conversation context", readme)
        self.assertIn("custom provider controls its own storage", readme)

    def test_release_version_has_one_manifest_source_and_matches_cli(self) -> None:
        plugin = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        version = plugin["version"]

        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertNotIn("version", marketplace["plugins"][0])
        result = subprocess.run(
            [sys.executable, str(ROOT / "memlog"), "--version"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f"memlog {version}")

    def test_release_files_cover_the_manifest_version(self) -> None:
        plugin = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        version = plugin["version"]
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        notes = ROOT / "releases" / f"v{version}.md"

        self.assertIn(f"## [{version}]", changelog)
        self.assertTrue(notes.is_file())
        self.assertIn(f"v{version}", notes.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
