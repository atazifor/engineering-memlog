import json
import os
import subprocess
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
MEMLOG = REPO_ROOT / "memlog"
SHORTLIST = REPO_ROOT / "scripts" / "memlog-shortlist"
SEARCH_PROMPT = REPO_ROOT / "scripts" / "memlog-search-prompt"
CONTEXT = REPO_ROOT / "scripts" / "memlog-context"
SESSION_HOOK = REPO_ROOT / "hooks" / "session-start.sh"
PROMPT_HOOK = REPO_ROOT / "hooks" / "user-prompt-submit.sh"
EXAMPLE_PROVIDER = REPO_ROOT / "examples" / "providers" / "jsonl-provider"


def make_entry(**overrides: Any) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "id": "mem-test-1",
        "timestamp": "2026-01-02T03:04:05Z",
        "title": "PostgreSQL connection timeout during deploy",
        "problem": "The API failed with a PostgreSQL connection timeout.",
        "cause": "The connection pool used the wrong host.",
        "fix": "Configured the correct database host.",
        "prevention": "Verify the resolved database host before deploying.",
        "artifact": "config/database.env",
        "repo": "sample-api",
        "service": "api",
        "environment": "staging",
        "tags": ["postgresql", "deployment"],
        "confidence": 0.75,
        "status": "draft",
        "source": "test",
    }
    entry.update(overrides)
    return entry


def write_jsonl(path: Path, values: Iterable[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(value, ensure_ascii=False) + "\n" for value in values),
        encoding="utf-8",
    )


class IsolatedTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.temp = Path(self._tempdir.name)
        self.home = self.temp / "home"
        self.home.mkdir()
        self.log = self.temp / "entries.jsonl"
        self.project = self.temp / "project"
        self.project.mkdir()
        self.provider_log = self.temp / "provider-entries.jsonl"

        python_bin = self.temp / "bin"
        python_bin.mkdir()
        (python_bin / "python3").symlink_to(Path(sys.executable))

        self.env = os.environ.copy()
        self.env.update(
            {
                "HOME": str(self.home),
                "ENGINEERING_MEMLOG_FILE": str(self.log),
                "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT),
                "CLAUDE_PROJECT_DIR": str(self.project),
                "PATH": f"{python_bin}:/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )

    def tearDown(self) -> None:
        self._tempdir.cleanup()

    def run_program(
        self,
        program: Path,
        *args: str,
        input_text: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(program), *args],
            input=input_text,
            text=True,
            capture_output=True,
            env=env or self.env,
            timeout=10,
            check=False,
        )

    def run_memlog(self, *args: str) -> subprocess.CompletedProcess:
        return self.run_program(MEMLOG, "--file", str(self.log), *args)

    def provider_env(self) -> Dict[str, str]:
        env = self.env.copy()
        env.update(
            {
                "ENGINEERING_MEMLOG_PROVIDER_COMMAND": shlex.join(
                    [sys.executable, str(EXAMPLE_PROVIDER)]
                ),
                "MEMLOG_PROVIDER_FILE": str(self.provider_log),
            }
        )
        return env

    def run_hook(
        self,
        hook: Path,
        input_text: str = "",
        env_updates: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        env = self.env.copy()
        env.update(env_updates or {})
        return subprocess.run(
            ["/bin/bash", str(hook)],
            input=input_text,
            text=True,
            capture_output=True,
            env=env,
            cwd=self.project,
            timeout=10,
            check=False,
        )

    def install_healthy_cli_marker(self) -> None:
        bin_dir = self.home / ".local" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "memlog").symlink_to(MEMLOG)
