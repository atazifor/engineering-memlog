import re
from pathlib import Path
import struct
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DocumentationAssetTests(unittest.TestCase):
    def test_relative_markdown_links_resolve(self) -> None:
        pattern = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")
        failures = []
        for document in ROOT.rglob("*.md"):
            if ".git" in document.parts:
                continue
            for raw_target in pattern.findall(document.read_text(encoding="utf-8")):
                target = raw_target.strip().split("#", 1)[0]
                if not target or "://" in target or target.startswith(("#", "mailto:")):
                    continue
                candidate = (document.parent / target).resolve()
                if not candidate.exists():
                    failures.append("{} -> {}".format(document.relative_to(ROOT), raw_target))
        self.assertEqual(failures, [])

    def test_social_preview_is_1280_by_640(self) -> None:
        data = (ROOT / "assets" / "social-preview.png").read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual((width, height), (1280, 640))

    def test_demo_gif_is_60_to_90_seconds(self) -> None:
        data = (ROOT / "assets" / "memlog-demo.gif").read_bytes()
        self.assertIn(data[:6], (b"GIF87a", b"GIF89a"))
        width, height = struct.unpack("<HH", data[6:10])
        self.assertEqual((width, height), (1280, 720))

        delays = []
        marker = b"\x21\xf9\x04"
        offset = 0
        while True:
            offset = data.find(marker, offset)
            if offset < 0:
                break
            delays.append(struct.unpack("<H", data[offset + 4 : offset + 6])[0])
            offset += len(marker)
        self.assertEqual(len(delays), 8)
        self.assertGreaterEqual(sum(delays), 6000)
        self.assertLessEqual(sum(delays), 9000)

        transcript = (ROOT / "demo" / "transcript.txt").read_text(encoding="utf-8")
        headings = re.findall(r"^=== (\d+) / (\d+)  .+ ===$", transcript, re.MULTILINE)
        self.assertEqual(len(headings), len(delays))
        self.assertEqual(
            headings,
            [(str(index), str(len(delays))) for index in range(1, len(delays) + 1)],
        )

    def test_readme_leads_with_plugin_install_and_no_hit_behavior(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertLess(
            readme.index("## Install for Claude Code"),
            readme.index("## CLI usage"),
        )
        self.assertIn("After a miss\nor an unavailable backend", readme)
        self.assertIn("assets/memlog-demo.gif", readme)
        self.assertIn("docs/comparison.md", readme)
        self.assertIn("not a\nhistory of every error", readme)
        self.assertIn("does not perform\nembedding or semantic search", readme)


class ReproducibleDemoTests(unittest.TestCase):
    def test_no_memlog_baseline_reproduces_and_fixes_the_same_fixture(self) -> None:
        result = subprocess.run(
            [str(ROOT / "demo" / "run-baseline.sh")],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Reproduce without memory", result.stdout)
        self.assertIn("Re-derive the cause from current code", result.stdout)
        self.assertIn("PASS: the fix works", result.stdout)
        self.assertNotIn("memlog search", result.stdout.lower())

    def test_demo_reproduces_recalls_verifies_writes_and_continues_on_miss(self) -> None:
        result = subprocess.run(
            [str(ROOT / "demo" / "run-demo.sh")],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        for evidence in (
            "FAIL: deleting a project leaves an orphan task",
            "SQLite foreign-key enforcement must be enabled",
            "MATCH: an ordinary application connection",
            "PASS: deleting a project now cascades",
            "Appended memory entry: Verified SQLite foreign-key enforcement",
            "A later session can retrieve",
            "No matches found.",
            "No match is not a stop condition",
        ):
            with self.subTest(evidence=evidence):
                self.assertIn(evidence, output)

    def test_demo_does_not_touch_the_default_store(self) -> None:
        script = (ROOT / "demo" / "run-demo.sh").read_text(encoding="utf-8")
        self.assertIn("mktemp -d", script)
        self.assertIn('--file "$WORK_DIR/entries.jsonl"', script)
        self.assertNotIn(".engineering-memlog", script)


if __name__ == "__main__":
    unittest.main()
