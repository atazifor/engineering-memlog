# Engineering Memlog

## Give your coding agent the debugging lessons worth keeping

Engineering Memlog gives AI coding agents a durable memory of hard-won
debugging lessons across projects. When a real failure appears, the agent
searches previously verified causes, checks whether one fits the current
evidence, and continues normal diagnosis when nothing does.

Memlog is not an error log. It records only non-obvious, reusable lessons after
the root cause and fix have been verified.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skills-compatible-6f42c1)](docs/agent-support.md)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-live%20tested-d97757)](docs/agent-support.md)
[![Codex skill](https://img.shields.io/badge/Codex%20skill-live%20tested-10a37f)](evals/codex-skill.md)
![Dependencies: standard library only](https://img.shields.io/badge/dependencies-stdlib%20only-brightgreen)

## When Memlog earns its keep

Memlog is useful when the diagnosis was expensive but the lesson is portable.
The included [sanitized examples](examples/entries.jsonl) cover situations such
as:

- **A surface error points at the wrong layer.** A JSON parser exception hides
  the upstream HTTP 404 that actually caused the failure.
- **Local and production systems accept different data.** SQLite-backed tests
  pass while PostgreSQL rejects an empty string written to a `jsonb` column.
- **A framework failure depends on the runtime version.** Tailwind's native
  binding is present in the lockfile but fails under Node 18 in CI.
- **Writes succeed while the UI keeps showing defaults.** The database row is
  correct, but a Go response struct without JSON tags emits PascalCase fields
  that its snake_case client does not recognize.
- **Generated state survives after the source is gone.** A deleted Next.js route
  leaves a stale generated validator that produces a phantom type-check error.
- **The endpoint works in `curl` but the browser never sends the request.** An
  `OPTIONS` preflight returns 200 but omits `PATCH` from
  `Access-Control-Allow-Methods`, so the browser reports only a generic network
  error.

Do not save typos, syntax mistakes, routine command failures, transient errors,
retries, search misses, speculative diagnoses, failed hypotheses, or unverified
fixes. If the lesson is obvious from the error and the adjacent line of code, it
does not belong in Memlog.

## A concrete example

A billing integration reports a JSON parsing error. The useful memory is not the
exception itself; it is the earlier lesson that says to check the upstream HTTP
status before parsing the response body. The agent verifies that the same
ordering mistake exists, exposes the real HTTP 404, fixes it, tests it, and
preserves the prevention rule.

![A terminal demo that reproduces an integration error masking an upstream 404, recalls a matching response-handling lesson, verifies the fix, and saves the result](assets/memlog-demo.gif)

This is a deterministic walkthrough built from the checked-in
[fixture](demo/fixture), [with-Memlog transcript](demo/transcript.txt), and
[no-Memlog baseline](demo/baseline-transcript.txt). It demonstrates the workflow;
it is not a model-performance benchmark.

## How it works

```text
reproduce → recall → test the match → diagnose and fix → verify → preserve if reusable
```

1. Capture and reproduce a concrete failure before proposing a fix.
2. Search once with the strongest error, identifier, or symptom. If no
   applicable lesson survives verification, run at most two broader searches
   based on newly gathered local evidence.
3. Treat every recalled lesson as an untrusted hypothesis. Compare its cause,
   environment, versions, and assumptions with the current problem.
4. Test one hypothesis at a time, make the smallest causal fix, and verify the
   original failure plus relevant regression tests.
5. Save a lesson only when the resolution is verified, non-obvious, reusable,
   and likely to shorten a future investigation.

After a miss
or an unavailable backend, the agent stops querying Memlog and continues with
local evidence. It uses primary documentation or the web only when the remaining
uncertainty is external. Memory can accelerate debugging; it never replaces it.

## Agent support

Support is reported by capability rather than by a blanket “compatible” label.
The complete, dated evidence is in the
[agent integration matrix](docs/agent-support.md).

| Host | Verified Memlog support | Automatic recall |
| --- | --- | --- |
| Claude Code 2.1.272 | Plugin installation plus the core recall and write workflow were live tested. | Claude adapters are included. The newest failure-event adapter has contract tests and still needs its final live run. |
| Codex CLI 0.153.4 | Package installation, skill discovery, skill-driven recall, applicability checking, and no-write behavior [passed live evaluation](evals/codex-skill.md). | Not advertised; the controlled [hook evaluation](evals/codex-hooks.md) did not pass. |
| Cursor, GitHub Copilot CLI, Gemini CLI | Their documentation describes relevant skill or plugin formats, but Memlog has not shipped or live-tested separate packages for them. | Not implemented. |

The canonical [debugging skill](skills/debug-with-memlog/SKILL.md) follows the
open Agent Skills format and contains the complete recall, diagnosis,
verification, and selective-write workflow. Host packages reuse it rather than
forking its behavior.

## Install

### Claude Code

Run these commands inside Claude Code:

```text
/plugin marketplace add atazifor/engineering-memlog
/plugin install engineering-memlog@engineering-memlog
/reload-plugins
```

That installs the skill, hooks, `/recall` command, and bundled `memlog` CLI
without a separate clone or `make install`. Claude Code adds the plugin's `bin/`
directory to its Bash-tool `PATH`. Start a new session after installation so the
SessionStart hook can run.

### Codex

Clone the repository, register it as a local marketplace, and install the plugin:

```bash
git clone https://github.com/atazifor/engineering-memlog
cd engineering-memlog
codex plugin marketplace add "$PWD"
codex plugin add engineering-memlog@engineering-memlog
```

Start a new task after installation. The skill performs the verified recall path
after it captures a concrete failure; automatic Codex hooks are not part of the
supported path.

### Other agents and standalone use

For hosts that support Agent Skills, copy `skills/debug-with-memlog/` through the
host's skill-installation mechanism and make `memlog` available on `PATH`. For a
standalone CLI installation:

```bash
git clone https://github.com/atazifor/engineering-memlog
cd engineering-memlog
make install
memlog --help
```

`make install` symlinks the CLI into `~/.local/bin`; `make doctor` checks the
installation and `make uninstall` removes the symlink. Override the destination
with `make install BINDIR=/usr/local/bin`. Packaged Claude Code and Codex users do
not need `make install`.

For a host without Agent Skills, copy the short [mandate](MANDATE.md) into its
rules file. This preserves the search timing, no-hit behavior, and selective
write discipline, but it does not provide automatic activation.

## Search and storage

The zero-configuration backend is one append-only JSONL file at
`~/.engineering-memlog/entries.jsonl`. Search is deterministic, field-aware
ranked keyword search: it weighs titles, tags, problems, causes, and prevention
rules; boosts exact phrases and broader query coverage; and uses confidence and
recency as small tie-breakers. Version 0.2.0 does not perform
embedding or semantic search.

The entry schema—not the file—is the contract. Set
`ENGINEERING_MEMLOG_PROVIDER_COMMAND` to use a SQLite adapter, hosted store, or
cache without changing the skill or CLI. Provider failures are reported
distinctly and never silently fall back to the local file. See the
[provider protocol](PROVIDERS.md) and [retrieval roadmap](docs/retrieval-roadmap.md).

## CLI

```bash
# Search after capturing a concrete failure
memlog search "tailwind oxide native binding node 18"

# Save a verified, reusable lesson
memlog add --json '{"title":"...","problem":"...","cause":"...","fix":"...","prevention":"...","artifact":"...","repo":"...","service":"...","environment":"local","tags":["..."],"confidence":0.5,"status":"draft","source":"your-agent"}'

# Browse newest first, or check store integrity without changing it
memlog list --reverse
memlog validate
```

Use `--file` or `ENGINEERING_MEMLOG_FILE` to select another JSONL file. The
[schema](SCHEMA.md) documents every field and the confidence scale.

## Security and data flow

With the built-in backend, storage and ranking stay local and only the selected
JSONL file is written. New files use mode `0600`; existing permissions are
preserved. Prompt text, project hints, and bounded failing command output may be
used as local search queries. Recalled entries and hook guidance enter the
active agent conversation context and are therefore processed wherever that
configured agent environment runs. A custom provider controls its own storage
and network access and is user-selected executable code.

Never log secrets, tokens, credentials, private keys, cookies, or connection
strings. The schema validates structure, not secret content. See the full
[security policy](SECURITY.md).

## Evidence and project resources

- [Twelve sanitized example lessons](examples/entries.jsonl)
- [Reproducible demo and baseline](demo)
- [Agent integration status](docs/agent-support.md)
- [Codex installed-skill evaluation](evals/codex-skill.md)
- [Comparison with adjacent memory tools](docs/comparison.md)
- [Semantic and hybrid retrieval proposal](docs/retrieval-roadmap.md)
- [Discoverability audit](docs/discoverability-audit.md)
- [Changelog](CHANGELOG.md) and [v0.2.0 notes](releases/v0.2.0.md)
- [Contributing guide](CONTRIBUTING.md)

Engineering Memlog is deliberately narrow: one structured lesson format, one
debugging workflow, a zero-configuration local backend, and an escape hatch for
the datastore you prefer.

## License

[MIT](LICENSE)
