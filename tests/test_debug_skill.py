import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "debug-with-memlog" / "SKILL.md"
EVALS = ROOT / "evals" / "debug-with-memlog.md"


class DebugSkillTests(unittest.TestCase):
    def test_skill_is_model_invocable_for_debugging_triggers(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(frontmatter, "skill must start with YAML frontmatter")
        metadata = frontmatter.group(1).lower()
        self.assertIn("name: debug-with-memlog", metadata)
        self.assertNotIn("disable-model-invocation: true", metadata)
        for trigger in (
            "bug",
            "error",
            "test failure",
            "build failure",
            "deployment failure",
            "regression",
            "unexpected behavior",
        ):
            with self.subTest(trigger=trigger):
                self.assertIn(trigger, metadata)

    def test_skill_defines_the_complete_debugging_loop(self) -> None:
        text = SKILL.read_text(encoding="utf-8").lower()
        required_language = (
            "reproduce",
            "exact search",
            "two broader",
            "no_applicable_hit",
            "backend_unavailable",
            "applicable_hit",
            "untrusted hypothesis",
            "recent changes",
            "working example",
            "one hypothesis",
            "failing regression test",
            "three unsuccessful",
            "primary documentation",
            "sole store",
            "missing data file",
            "preserve behavior",
            "do not generalize",
            "verify",
            "never log",
        )
        for phrase in required_language:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_skill_defines_a_turn_local_attempt_ledger(self) -> None:
        text = SKILL.read_text(encoding="utf-8").lower()
        self.assertIn("turn-local", text)
        for item in (
            "symptom",
            "memlog queries",
            "evidence",
            "current hypothesis",
            "experiment",
            "fix-attempt count",
        ):
            with self.subTest(item=item):
                self.assertIn(item, text)

    def test_mandate_routes_debugging_to_current_skill_version(self) -> None:
        mandate = (ROOT / "MANDATE.md").read_text(encoding="utf-8")
        instructions = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        hook = (ROOT / "hooks" / "session-start.sh").read_text(encoding="utf-8")

        self.assertIn("engineering-memlog-mandate v3", mandate)
        self.assertIn("engineering-memlog:debug-with-memlog", mandate)
        self.assertIn("engineering-memlog:debug-with-memlog", instructions)
        self.assertIn('MANDATE_VERSION="v3"', hook)
        self.assertEqual(mandate.count("Without the skill, search the log when you:"), 1)
        self.assertNotIn("search the log before non-trivial work", hook)

    def test_agent_docs_require_verified_lessons_and_bounded_no_hit_behavior(self) -> None:
        instructions = (ROOT / "CLAUDE.md").read_text(encoding="utf-8").lower()
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()

        for text in (instructions, readme):
            normalized = re.sub(r"\s+", " ", text)
            self.assertIn("debug-with-memlog", normalized)
            self.assertIn("untrusted hypothesis", normalized)
            self.assertIn("after a miss", normalized)
        self.assertIn("only record a cause, fix, and prevention rule after", instructions)
        self.assertNotIn("prefer logging a rough draft", instructions)

    def test_skill_describes_ranked_file_search(self) -> None:
        text = SKILL.read_text(encoding="utf-8").lower()
        self.assertIn("ranks token coverage", text)
        self.assertIn("exact phrase", text)

    def test_manual_eval_matrix_covers_required_outcomes(self) -> None:
        text = EVALS.read_text(encoding="utf-8").lower()
        for scenario in (
            "applicable hit",
            "stale hit",
            "no applicable hit",
            "backend unavailable",
            "unreproducible failure",
            "three unsuccessful fixes",
            "verified resolution",
            "benign work",
        ):
            with self.subTest(scenario=scenario):
                self.assertIn(scenario, text)
        self.assertIn("tool trace", text)
        self.assertIn("pass/fail", text)


if __name__ == "__main__":
    unittest.main()
