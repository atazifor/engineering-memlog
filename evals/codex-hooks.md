# Codex automatic-hook evaluation

Run on 2026-09-15. Result: **not passed, not advertised as supported**.

The shared hook programs and Codex-shaped payloads pass repository tests, and the
current Codex documentation describes `SessionStart`, `UserPromptSubmit`, and
`PostToolUse` plugin hooks. Direct execution of `hooks/post-tool-recall.py` with a
Codex `PostToolUse` payload returned the expected Memlog context.

## Controlled trust-bypass run

The repository-root marketplace package at commit `3abfaf1` was installed as
`engineering-memlog@engineering-memlog` on Codex CLI 0.153.4. The environment
set `ENGINEERING_MEMLOG_FILE` to the temporary store containing
`mem-codex-eval-hit`, the same sanitized entry described in
[codex-skill.md](codex-skill.md). Before the run, `codex features list` reported
both `hooks` and `plugins` as stable and enabled.
Both checks used the documented one-off `--dangerously-bypass-hook-trust` option;
the JSON event stream confirmed twice per run that enabled hooks could run without
review for that invocation. This bypasses exact hook-hash review and is distinct
from trusting the fixture repository.

Both used this command shape with an ephemeral thread and read-only sandbox:

```text
ENGINEERING_MEMLOG_FILE=<temporary-store> codex \
  --ask-for-approval never --dangerously-bypass-hook-trust \
  exec --ephemeral --json --sandbox read-only \
  -C evals/fixture "<scenario prompt>"
```

Prompt-time check:

- The prompt named the seeded symptom `slugify leaves underscores in cache keys`
  and instructed the agent not to run tools or invoke a skill.
- The final response was: `No automatic Memlog hook context was supplied; no
  recalled entry ID was present.`

Post-tool check:

- The prompt instructed the agent not to invoke a skill or call Memlog directly,
  then to run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v`.
- The command exited 1 with the expected `user_profile-name` versus
  `user-profile-name` assertion failure.
- The final response was: `No—automatic Memlog hook context was not supplied
  after the command.`

These controlled results cover SessionStart/UserPromptSubmit before the first
response and a non-zero PostToolUse event without a manual search obscuring the
outcome.

## Reproductions

The same absence had already been reproduced with:

- Codex CLI 0.153.4 using conventional `hooks/hooks.json` discovery;
- Codex CLI 0.153.4 with the hook file explicitly declared in the compatibility
  manifest;
- the failing fixture inside a trusted repository; and
- Codex CLI 0.154.0 in the same prompt-only check.

The skill-driven explicit recall path still passed independently. Until a future
run shows actual automatic context injection, the README and support matrix must
describe Codex as installed-skill support and must not promise Codex automatic
recall hooks.
