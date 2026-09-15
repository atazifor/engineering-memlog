# engineering-memlog

## Recall verified fixes when debugging

An AI coding agent solves a difficult failure, the session ends, and the next
session solves it again. Engineering Memlog gives compatible coding agents a
small, cross-project log of verified debugging lessons and a systematic skill
that searches it when a concrete failure appears.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)
![Agent Skill](https://img.shields.io/badge/Agent%20Skills-compatible-6f42c1)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-live%20tested-d97757)
![Codex skill](https://img.shields.io/badge/Codex%20skill-live%20tested-10a37f)
![dependencies: stdlib only](https://img.shields.io/badge/dependencies-stdlib%20only-brightgreen)

![A terminal demo that reproduces an integration error masking an upstream 404, recalls a matching response-handling lesson, verifies the fix, and saves the result](assets/memlog-demo.gif)

Without Memlog:

```text
failure -> investigate from scratch -> fix -> session ends -> repeat later
```

With Memlog:

```text
reproduce -> recall a ranked lesson -> verify it applies -> fix and test -> remember
```

The recalled lesson is evidence to test, not an instruction to trust. After a miss
or an unavailable backend, the agent returns to local evidence gathering and then
to primary documentation or the web when the remaining uncertainty is external.
Debugging never stops just because memory has no answer.

Claude Code's auto memory is useful for project context and preferences, but its
current documentation explicitly lists debugging fixes among the information it
skips because they can be derived from the codebase. Memlog deliberately keeps
that narrow class of hard-won knowledge in a reusable format. See the
[factual comparison](docs/comparison.md) and Claude's
[memory documentation](https://code.claude.com/docs/en/memory).

Current source version: **0.2.0** · [changelog](CHANGELOG.md) ·
[draft release notes](releases/v0.2.0.md)

## Install

The canonical `debug-with-memlog` skill follows the open Agent Skills format.
Claude Code and Codex packages reuse that same skill; host-specific files only
handle installation and optional recall triggers. Exact support boundaries and
dated evidence are in the [agent integration matrix](docs/agent-support.md).

### Claude Code

Run these commands inside Claude Code:

```text
/plugin marketplace add atazifor/engineering-memlog
/plugin install engineering-memlog@engineering-memlog
/reload-plugins
```

That installs the skill, hooks, `/recall` command, and bundled `memlog` CLI
without a separate clone or `make install`. Start a new Claude Code session after
installation so the SessionStart hook can run.

### Codex

Clone the repository, register it as a local marketplace, and install the plugin:

```bash
git clone https://github.com/atazifor/engineering-memlog
cd engineering-memlog
codex plugin marketplace add "$PWD"
codex plugin add engineering-memlog@engineering-memlog
```

Start a new Codex task after installation. The installed skill-discovery and
Memlog recall workflow passed the recorded
[Codex evaluation](evals/codex-skill.md). Automatic Codex hook activation did
not pass its live gate, so it is not promised; the skill itself performs the
search after the agent captures a concrete failure.

### Other compatible agents

Install or copy `skills/debug-with-memlog/` using the host's Agent Skills
mechanism and make `memlog` available on `PATH`. If the whole repository is
installed as a plugin, the skill can use its bundled `scripts/memlog` fallback.
For hosts without Agent Skills, copy the short [mandate](MANDATE.md) into the
agent's rules file. Cursor, GitHub Copilot CLI, and Gemini CLI are currently
documented integration targets, not live-tested Memlog packages.

The `debug-with-memlog` skill activates for bugs, errors, failed tests,
builds and deployments, regressions, performance problems, and unexpected
behavior. It follows this bounded loop:

1. Capture and reproduce a concrete failure.
2. Run one exact Memlog search and at most two broader searches.
3. Treat each result as an untrusted hypothesis and test it against current
   evidence.
4. On a miss or backend error, continue systematic local diagnosis; consult
   primary documentation or the web when needed.
5. After the fix passes verification, save only a reusable lesson with the
   problem, cause, fix, and prevention rule.

### What deserves a Memlog entry

Memlog is a curated record of expensive, reusable engineering knowledge—not a
history of every error an agent encounters. Save a lesson only when the root
cause is verified, non-obvious, likely to recur, and useful enough to materially
shorten a future investigation. Good entries preserve framework or
infrastructure behavior, subtle cross-layer causes, and concrete prevention
rules.

Do not save typos, syntax mistakes, routine command failures, transient errors,
retries, search misses, speculative diagnoses, failed hypotheses, or fixes that
were not verified. If the lesson is already obvious from the error and the line
of code beside it, it does not belong in Memlog.

Try the deterministic local walkthrough with `./demo/run-demo.sh`. It runs in a
temporary directory and never touches your real log. The checked-in
[with-Memlog transcript](demo/transcript.txt) records the commands and output
used for the demo above. A separate
[no-Memlog baseline](demo/baseline-transcript.txt) reproduces and fixes the same
fixture by inspecting the implementation from scratch. These are reproducible
command-level walkthroughs, not a model-performance benchmark.

## Default storage and custom providers

The zero-configuration backend is one append-only JSONL file at
`~/.engineering-memlog/entries.jsonl`. Search is a deterministic, field-aware
lexical ranking over that file. There is no database, embedding model, telemetry,
or remote service in the built-in path.

In plain language, the current search is ranked keyword search. It tokenizes the
query and entry fields, gives more weight to titles, tags, problems, causes, and
prevention rules, boosts exact phrases and broader query coverage, and uses
confidence and recency only as small tie-breakers. Version 0.2.0 does not perform
embedding or semantic search.

The entry schema—not the file—is the contract. Set
`ENGINEERING_MEMLOG_PROVIDER_COMMAND` to connect a SQLite adapter, hosted store,
or cache without changing the skill or CLI. Provider failures are reported
distinctly and never silently fall back to the local file. See
[PROVIDERS.md](PROVIDERS.md) for the versioned protocol and a working adapter.

## CLI usage

The packaged integrations bundle the CLI. For standalone shell use or an agent
without a Memlog package:

```bash
git clone https://github.com/atazifor/engineering-memlog
cd engineering-memlog
make install
memlog --help
```

`make install` symlinks the CLI into `~/.local/bin`; `make doctor` checks the
installation and `make uninstall` removes the symlink. Override the location
with `make install BINDIR=/usr/local/bin`.

```bash
# Search after capturing a concrete failure
memlog search "tailwind oxide native binding node 18"

# Append a verified lesson
memlog add --json '{"title":"...","problem":"...","cause":"...","fix":"...","prevention":"...","artifact":"...","repo":"...","service":"...","environment":"local","tags":["..."],"confidence":0.5,"status":"draft","source":"your-agent"}'

# Browse newest first, or check integrity without changing the store
memlog list --reverse
memlog validate
```

Use `--file` or `ENGINEERING_MEMLOG_FILE` to select another JSONL file. The
[schema](SCHEMA.md) documents every field and the confidence scale.

## What the agent integrations do

- `debug-with-memlog` owns the recall-investigate-verify-write loop.
- The Claude Code SessionStart hook supplies up to six relevant lessons based on the repository,
  languages, frameworks, service, recency, and confidence.
- The Claude Code UserPromptSubmit hook recognizes symptom-shaped prompts and injects bounded matches;
  benign prompts stay silent.
- Claude Code PostToolUse and PostToolUseFailure inspect Bash results for strong test, build,
  and deployment failure signals. This catches failures discovered after the
  prompt—even when a pipeline masks the failing process's exit status—while
  ordinary command errors and successful checks stay silent.
- Claude Code's `/recall <query>` gives the user an explicit search path.
- Codex loads the same skill from its package; the live evaluation proves
  skill-driven recall, while automatic Codex hooks remain unverified.
- `MEMLOG_PLUGIN_DISABLE=1` disables all hooks for a session.
- `MEMLOG_MANDATE=manual` keeps recall but disables automatic mandate loading.

The post-command hook searches only after a concrete diagnostic signal. A hit is
injected as an untrusted hypothesis. A no-hit response tells the agent to continue
the debugging skill's local evidence workflow, and an unavailable provider is
reported distinctly. This is not an error collector and does not write entries.
`MEMLOG_PLUGIN_FAILURE_LIMIT` bounds results (default 5), and
`MEMLOG_PLUGIN_MAX_TOOL_OUTPUT_BYTES` bounds inspected command output (default
16384 bytes).

The SessionStart hook reads common manifest files, `git remote get-url origin`,
`git ls-files`, and nearby `CLAUDE.md`, `AGENTS.md`, or `.cursorrules` files for
relevance hints. The plugin's `bin/` directory is added to the Bash-tool PATH by
Claude Code, so the bundled CLI is available to the skill. Details are in the
[Claude plugin file-location reference](https://code.claude.com/docs/en/plugins-reference#file-locations-reference).

Agents without a packaged integration can copy the short [mandate](MANDATE.md)
into their rules file. It preserves the write discipline and the same no-hit
behavior, but does not provide automatic skill or hook activation.

## Security and data flow

With the built-in backend, storage and ranking stay local and only the selected
JSONL file is written. New files use mode `0600`; existing permissions are
preserved. Prompt text, project hints, and bounded failing Bash output may be used
as local search queries. Recalled entries and hook guidance are inserted into the
active agent conversation context and are therefore processed wherever that
configured agent environment runs. A custom provider controls its own storage
and network access and is user-selected executable code.

Do not log secrets, tokens, credentials, private keys, cookies, or connection
strings. The schema checks structure, not secret content. The provider command
must begin with an absolute executable path, receives versioned JSON on stdin,
has response-size and time limits, and is never invoked through a shell.

For the full disclosure and threat boundaries, see [SECURITY.md](SECURITY.md).

## Project resources

- [Twelve sanitized example lessons](examples/entries.jsonl)
- [Provider protocol and adapter](PROVIDERS.md)
- [Entry schema](SCHEMA.md)
- [Comparison with adjacent tools](docs/comparison.md)
- [Semantic and hybrid retrieval proposal](docs/retrieval-roadmap.md)
- [Discoverability audit](docs/discoverability-audit.md)
- [Agent integration status and evidence](docs/agent-support.md)
- [Contributing guide](CONTRIBUTING.md)

Engineering Memlog is deliberately narrow: one structured lesson format, one
debugging workflow, a zero-configuration local backend, and an escape hatch for
the datastore you prefer.

## License

[MIT](LICENSE).
