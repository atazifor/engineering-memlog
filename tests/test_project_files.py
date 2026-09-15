import json
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
