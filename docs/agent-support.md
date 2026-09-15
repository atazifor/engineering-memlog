# Agent integration status

Verified on 2026-09-15. This page distinguishes package compatibility from a
real agent run so the project does not imply support that has not been tested.

## Status meanings

- **Documented**: the host's official documentation describes the required
  skill, plugin, or hook capability. No Memlog package or agent run is implied.
- **Package validated**: Memlog's files pass the host or open-format validator,
  plus the repository's automated compatibility tests.
- **Live tested**: an installed, authenticated host completed the recorded
  Memlog scenario. The dated evidence file and host version are linked.

## Current matrix

| Host or format | Skill | Plugin package | Automatic recall hooks | Memlog status |
| --- | --- | --- | --- | --- |
| Agent Skills open format | `skills/debug-with-memlog/SKILL.md` | n/a | n/a | The reference validator passes; the skill remains host-neutral. |
| Agent Plugins 1.0 | same canonical skill | root `plugin.json` | Host-specific | The root manifest passes the published 1.0 JSON Schema. |
| Claude Code 2.1.272 | same canonical skill | `.claude-plugin/plugin.json` | Session, prompt, successful-tool, and failed-tool adapters | Core install/recall/write was live tested; the newer failure-triggered hook has contract tests but still needs its final live run. |
| Codex CLI 0.153.4 | same canonical skill | `.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json` | Not advertised; live activation did not pass | Package installation, skill discovery, recall, applicability checking, and no-write behavior [passed live evaluation](../evals/codex-skill.md). Automatic hooks remain [explicitly unverified](../evals/codex-hooks.md). |
| Cursor | documented Agent Skills and plugin/hooks support | not packaged separately | adapter not implemented | Documented only. |
| GitHub Copilot CLI | documented Agent Plugins and hooks support | not packaged separately | adapter not implemented | Documented only. |
| Gemini CLI | documented extension skills and hooks support | not packaged separately | adapter not implemented | Documented only. |

The canonical skill contains the whole read → diagnose → verify → selective-write
workflow. Host adapters may decide when to inject a recall hint, but they must not
change what counts as evidence, a successful miss, a backend outage, or a lesson
worth preserving.

## Verified format and host facts

- The [Agent Skills specification](https://agentskills.io/specification) defines
  a `SKILL.md` directory format and the portable frontmatter used here.
- The [Agent Plugins 1.0 schema](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json)
  defines the root `plugin.json`; skills are discovered under `skills/`.
- [Claude Code plugins](https://code.claude.com/docs/en/plugins-reference) support
  skills, commands, a bundled `bin/` directory, and plugin hooks. Claude's
  [hook reference](https://code.claude.com/docs/en/hooks) documents both
  `PostToolUse` and `PostToolUseFailure`.
- [Codex plugins](https://learn.chatgpt.com/docs/build-plugins) use a
  `.codex-plugin/plugin.json` compatibility manifest and an
  `.agents/plugins/marketplace.json` marketplace catalog. Codex's
  [hook reference](https://learn.chatgpt.com/docs/hooks) documents one
  `PostToolUse` event for Bash success and non-zero exits, and the plugin-root
  environment variables used by this adapter.
- Cursor documents [Agent Skills](https://prod.cursor.com/docs/skills),
  [plugins](https://prod.cursor.com/docs/plugins), and
  [hooks](https://prod.cursor.com/docs/hooks).
- GitHub documents [Copilot CLI plugins](https://docs.github.com/en/copilot/concepts/agents/about-plugins)
  and its [hooks contract](https://docs.github.com/en/copilot/reference/hooks-reference).
- Gemini CLI documents [extensions](https://geminicli.com/docs/extensions/reference/)
  and [hooks](https://geminicli.com/docs/hooks/reference/).

## Adding another host

Do not copy and rewrite the debugging skill. Add the smallest adapter around the
canonical skill and shared search scripts, then complete these gates:

1. Link the host's current primary documentation for skill/package/hook support.
2. Record the exact host version and event/input/output differences.
3. Add package validation and fixture tests for hit, no-hit, backend outage,
   successful command, meaningful failure, pipeline-masked failure, and trivial
   command failure.
4. Confirm that no hook writes an entry and that a verified, non-obvious resolution
   can be written through the bundled or installed CLI.
5. Run an installed-agent evaluation in a disposable project and log sanitized
   evidence under `evals/`.
6. Only then change the matrix entry to **Live tested** and advertise support in
   the README.

Passing one capability does not promote adjacent capabilities. For example, the
Codex installed-skill row is live tested while automatic Codex hook activation
remains outside the advertised support boundary.
