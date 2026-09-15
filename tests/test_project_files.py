import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProjectFileTests(unittest.TestCase):
    def test_plugin_json_files_parse(self) -> None:
        for path in (
            ROOT / ".claude-plugin" / "plugin.json",
            ROOT / ".claude-plugin" / "marketplace.json",
            ROOT / "hooks" / "hooks.json",
        ):
            with self.subTest(path=path):
                self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_bash_failure_recall_is_registered_for_both_exit_paths(self) -> None:
        config = json.loads(
            (ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8")
        )["hooks"]
        for event in ("PostToolUse", "PostToolUseFailure"):
            with self.subTest(event=event):
                registration = config[event][0]
                self.assertEqual(registration["matcher"], "Bash")
                self.assertIn(
                    "post-tool-recall.py",
                    registration["hooks"][0]["command"],
                )

    def test_documentation_has_no_obsolete_engineering_memory_paths(self) -> None:
        for path in (ROOT / "CLAUDE.md", ROOT / "commands" / "recall.md"):
            with self.subTest(path=path):
                self.assertNotIn(
                    "~/engineering-memory",
                    path.read_text(encoding="utf-8"),
                )

    def test_plugin_install_docs_use_the_bundled_cli(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("plugin's `bin/` directory", readme)
        self.assertIn("without a separate clone or `make install`", readme)
        self.assertNotIn("only adds the read-side hooks", readme)

    def test_security_docs_disclose_model_context_and_custom_provider_flow(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("active Claude conversation context", readme)
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
