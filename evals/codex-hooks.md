# Codex automatic-hook evaluation

Run on 2026-09-15. Result: **not passed, not advertised as supported**.

The shared hook programs and Codex-shaped payloads pass repository tests, and the
current Codex documentation describes `SessionStart`, `UserPromptSubmit`, and
`PostToolUse` plugin hooks. Direct execution of `hooks/post-tool-recall.py` with a
Codex `PostToolUse` payload returned the expected Memlog context.

Installed-plugin runs did not show automatic Memlog context at session start,
prompt submission, or after the failing test. This was reproduced with:

- Codex CLI 0.153.4 using conventional `hooks/hooks.json` discovery;
- Codex CLI 0.153.4 with the hook file explicitly declared in the compatibility
  manifest;
- the failing fixture inside a trusted repository; and
- Codex CLI 0.154.0 in the same prompt-only check.

The skill-driven explicit recall path still passed independently. Until a future
run shows actual automatic context injection, the README and support matrix must
describe Codex as installed-skill support and must not promise Codex automatic
recall hooks.
