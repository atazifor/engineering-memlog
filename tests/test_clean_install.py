import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import REPO_ROOT, make_entry, write_jsonl


class CleanInstallE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.temp = Path(self._tempdir.name)
        self.plugin = self.temp / "plugin-cache" / "engineering-memlog" / "0.2.0"
        shutil.copytree(
            REPO_ROOT,
            self.plugin,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".DS_Store"),
        )

        self.project = self.temp / "slugify-project"
        self.project.mkdir()
        self.home = self.temp / "fresh-home"
        self.home.mkdir()
        self.log = self.temp / "fresh-entries.jsonl"

        python_bin = self.temp / "python-bin"
        python_bin.mkdir()
        (python_bin / "python3").symlink_to(Path(sys.executable))

        self.env = os.environ.copy()
        self.env.pop("PYTHONPATH", None)
        self.env.update(
            {
                "HOME": str(self.home),
                "PATH": f"{self.plugin / 'bin'}:{python_bin}:/usr/bin:/bin",
                "CLAUDE_PLUGIN_ROOT": str(self.plugin),
                "CLAUDE_PROJECT_DIR": str(self.project),
                "ENGINEERING_MEMLOG_FILE": str(self.log),
                "MEMLOG_MANDATE": "manual",
                "MEMLOG_PLUGIN_MIN_SCORE": "0",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )

    def tearDown(self) -> None:
        self._tempdir.cleanup()

    def run_command(self, command, input_text=None, cwd=None):
        return subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            env=self.env,
            cwd=cwd or self.project,
            timeout=10,
            check=False,
        )

    def test_fresh_plugin_recall_fix_write_and_later_recall(self) -> None:
        self.assertEqual(
            shutil.which("memlog", path=self.env["PATH"]),
            str(self.plugin / "bin" / "memlog"),
        )
        self.assertFalse((self.home / ".local" / "bin" / "memlog").exists())

        (self.project / "pyproject.toml").write_text(
            '[project]\nname = "slugify-project"\nversion = "0.0.0"\n',
            encoding="utf-8",
        )
        (self.project / "slugify.py").write_text(
            "def slugify(value):\n    return value.lower().replace(' ', '-')\n",
            encoding="utf-8",
        )
        (self.project / "test_slugify.py").write_text(
            "import unittest\n"
            "from slugify import slugify\n\n"
            "class SlugifyTest(unittest.TestCase):\n"
            "    def test_underscore_separator(self):\n"
            "        self.assertEqual(slugify('Cache_Key'), 'cache-key')\n",
            encoding="utf-8",
        )

        prior = make_entry(
            id="prior-slugify",
            title="Slugifier leaves underscores in cache keys",
            problem="The slugify underscore regression test fails.",
            cause="The normalizer handles spaces but not underscores.",
            fix="Normalize underscores before lowercasing.",
            prevention="Cover every supported separator with a regression test.",
            artifact="slugify.py",
            repo="slugify-project",
            service="",
            environment="local",
            tags=["python", "slugify", "underscore"],
        )
        write_jsonl(self.log, [prior])

        failing = self.run_command(
            [sys.executable, "-m", "unittest", "test_slugify.py"],
        )
        self.assertNotEqual(failing.returncode, 0)

        recalled = self.run_command(
            ["/bin/bash", str(self.plugin / "hooks" / "user-prompt-submit.sh")],
            input_text=json.dumps(
                {"prompt": "The slugify underscore regression test is failing"}
            ),
        )
        self.assertEqual(recalled.returncode, 0, recalled.stderr)
        self.assertIn("prior-slugify", recalled.stdout)

        (self.project / "slugify.py").write_text(
            "def slugify(value):\n"
            "    return value.lower().replace('_', '-').replace(' ', '-')\n",
            encoding="utf-8",
        )
        verified = self.run_command(
            [sys.executable, "-m", "unittest", "test_slugify.py"],
        )
        self.assertEqual(verified.returncode, 0, verified.stderr)

        lesson = {
            "title": "Normalize underscores when slugifying cache keys",
            "problem": "The underscore regression test failed.",
            "cause": "The normalizer only handled spaces.",
            "fix": "Converted underscores and spaces to hyphens.",
            "prevention": "Keep separator cases in the slugify regression suite.",
            "artifact": "slugify.py",
            "repo": "slugify-project",
            "service": "",
            "environment": "local",
            "tags": ["python", "slugify", "underscore"],
            "confidence": 0.5,
            "status": "draft",
            "source": "clean-install-e2e",
        }
        appended = self.run_command(
            ["memlog", "add", "--json", json.dumps(lesson)],
        )
        self.assertEqual(appended.returncode, 0, appended.stderr)

        later_session = self.run_command(
            ["/bin/bash", str(self.plugin / "hooks" / "session-start.sh")],
        )
        self.assertEqual(later_session.returncode, 0, later_session.stderr)
        self.assertIn(lesson["title"], later_session.stdout)

        later_search = self.run_command(
            ["memlog", "search", "slugify underscore", "--json"],
        )
        self.assertEqual(later_search.returncode, 0, later_search.stderr)
        self.assertIn(lesson["title"], later_search.stdout)

    def test_skill_bundled_cli_works_without_plugin_bin_on_path(self) -> None:
        env = self.env.copy()
        env["PATH"] = env["PATH"].replace(f"{self.plugin / 'bin'}:", "")
        wrapper = (
            self.plugin
            / "skills"
            / "debug-with-memlog"
            / "scripts"
            / "memlog"
        )

        result = subprocess.run(
            [str(wrapper), "--help"],
            text=True,
            capture_output=True,
            env=env,
            cwd=self.project,
            timeout=10,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Durable engineering memory", result.stdout)


if __name__ == "__main__":
    unittest.main()
