# engineering-memlog

**Your AI coding agent keeps solving the same problems from scratch every session.** Give it a memory — a shared, searchable log of fixes it writes after work and auto-recalls before, across sessions and projects. Works with Claude Code (one-command plugin), Cursor, and any agent that reads a `CLAUDE.md` / `AGENTS.md` / `.cursorrules`.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-d97757)
![dependencies: stdlib only](https://img.shields.io/badge/dependencies-stdlib%20only-brightgreen)

> **The problem:** an AI agent figures something out the hard way, the session ends, and that knowledge is gone. A week later a different session re-derives the same fix from scratch.
>
> **The fix:** before finishing a task, the agent appends a structured lesson — *problem, cause, fix, prevention* — to one shared JSONL log. Next time the symptom shows up, it searches the log and skips the re-derivation.

That's the default: **one JSONL file, a small stdlib CLI, and a focused debugging workflow for your agent.** No database, embeddings, or network calls are required. On Claude Code, a plugin combines that workflow with automatic retrieval hints so relevant prior lessons surface while the failure is being investigated. An optional provider protocol lets you keep the workflow while swapping in your own datastore or cache.

**Keywords:** AI agent memory · persistent memory for LLM coding assistants · Claude Code plugin · Cursor / AGENTS.md · cross-project knowledge base · stop repeating bugs.

## The three pieces

The division is the whole idea.

**1. A structured log.** By default, one append-only file, `entries.jsonl` — one JSON object per line, shared across every project. See [SCHEMA.md](SCHEMA.md).

**2. An agent policy.** The [mandate](MANDATE.md) defines when to preserve a verified lesson. The Claude Code plugin also ships `debug-with-memlog`, a model-invocable skill that searches after a concrete failure is captured, validates any hit as a hypothesis, continues local diagnosis on a miss, and writes back only after verification.

**3. A CLI.** `memlog add`, `search`, `list`. Python standard library only.

The default storage layer is deliberately dumb: append one JSON line and scan the file on reads. Search uses deterministic lexical ranking, while judgment—what is worth logging, when to search, and whether a result applies—stays with the agent workflow. The entry schema and the small [provider protocol](PROVIDERS.md) are the contracts; the bundled JSONL backend remains the zero-configuration implementation.

## Install

`python3` (3.8+) is the only requirement.

For standalone shell use, Cursor, or another non-plugin agent:

```bash
git clone https://github.com/atazifor/engineering-memlog
cd engineering-memlog
make install        # symlinks memlog onto your PATH, verifies it, checks PATH
memlog --help
```

`make install` symlinks (not copies) the CLI into `~/.local/bin`, so a later
`git pull` updates it in place — no stale copy. Override the location with
`make install BINDIR=/usr/local/bin`. Run `make doctor` any time to check the
install, PATH, and python3; `make uninstall` removes the symlink. (Prefer the
manual way? Copy `memlog`, `memlog_retrieval.py`, `memlog_provider.py`, and
`memlog_schema.py` into the same bin directory, then make `memlog` executable.
Re-copy all four after each pull.)

The log lives at `~/.engineering-memlog/entries.jsonl` by default. Override with `--file` or `ENGINEERING_MEMLOG_FILE` — point it inside a repo if you want a team to share one. To use SQLite, a hosted store, or a cached adapter instead, set `ENGINEERING_MEMLOG_PROVIDER_COMMAND`; see [Storage providers](PROVIDERS.md).

## Usage

```bash
# append a lesson
memlog add --json '{ "title": "...", "problem": "...", ... }'

# search after capturing a concrete failure
memlog search "frozen lockfile install failure"

# browse, newest first
memlog list --reverse

# check schemas and duplicate IDs without changing the file
memlog validate
```

In practice you rarely run `add` by hand. Your agent does, because the mandate tells it to.

Search is case-insensitive and field-aware. It ranks query-token coverage across
the title, tags, problem, cause, prevention, artifact, fix, repo, service, and
environment; exact phrases receive a boost, while confidence and recency break
close ties. Multi-term queries must match more than one term, which keeps a generic
word such as “failure” from flooding the results. Retrieval still performs a
linear scan with the built-in JSONL backend—simple and appropriate for a personal
log, with no index or cache to maintain. An external provider can maintain an
index or cache while returning the same entry stream to the ranker.

## How your agent uses the log

The agent uses the same CLI you do — no embeddings, no MCP server required. Two paths, depending on whether the plugin is installed.

**With the [mandate](MANDATE.md) only (any agent, any IDE):** after a verified, meaningful resolution, the agent runs `memlog add` to append a structured entry. Once it has captured a concrete failure, it searches with a concise evidence-bearing query and treats each ranked result as an untrusted hypothesis. A miss leads back to local evidence gathering, then primary documentation or the web when the uncertainty is external—not to more unbounded Memlog queries.

**With the plugin installed (Claude Code only):** the model-invocable debugging skill owns the read-investigate-verify loop. SessionStart and UserPromptSubmit hooks supply bounded retrieval hints, including failures discovered after the session begins. **The SessionStart hook also auto-loads the [mandate](MANDATE.md)**, so plugin users do not need to paste anything into a project rules file. The auto-load is idempotent: if you *do* paste the mandate into a `CLAUDE.md` (it carries a version marker), the hook detects it and stays quiet; set `MEMLOG_MANDATE=manual` to turn auto-load off entirely.

## Closing the read-side loop — Claude Code plugin

Prose mandates work for the write side but agents reliably **drift past retrieval during debugging**. The result is a write-mostly system: lessons land but rarely surface in time to prevent a re-derivation.

This repo ships a Claude Code plugin that fixes that by making the read side automatic, not voluntary:

- **`debug-with-memlog` skill** activates for bugs, errors, failed tests/builds/deployments, regressions, performance problems, and unexpected behavior. It reproduces first, performs one exact and at most two broader searches, treats results as untrusted hypotheses, continues systematic local diagnosis after a miss or backend outage, tests one cause at a time, and preserves only a verified lesson.
- **SessionStart hook** sniffs the project's languages / frameworks / repo / service from manifest files (`go.mod`, `package.json`, `pom.xml`, `Cargo.toml`, …), ranks entries by tag/repo/service overlap + recency + confidence, and injects the top ~6 as a system reminder at session boot. The agent sees relevant prior lessons before it sees the first user prompt.
- **UserPromptSubmit hook** scans each prompt for symptom-shaped text (errors, failures, 4xx/5xx, framework names) and, on a hit, extracts likely keywords (quoted strings, known tech tokens) and injects matches. Silent on benign prompts — no per-turn token bloat.
- **`/recall <query>`** slash command for explicit deep dive.

The pieces are all stdlib Python plus bash hooks — same "deliberately dumb" discipline as the core CLI. See `scripts/memlog-context`, `scripts/memlog-shortlist`, `scripts/memlog-search-prompt`, and `hooks/`.

### Install the plugin

Requires Claude Code 1.0.123+. Run these slash commands inside any Claude Code session:

```
/plugin marketplace add atazifor/engineering-memlog
/plugin install engineering-memlog@engineering-memlog
/reload-plugins
```

The `/reload-plugins` step registers the plugin's skill, commands, hooks, and
bundled CLI in the current session. Claude Code automatically adds executables
from a plugin's `bin/` directory to Bash-tool `PATH`, so `memlog search` and
`memlog add` work without a separate clone or `make install`. See Claude Code's
[plugin file-location reference](https://code.claude.com/docs/en/plugins-reference#file-locations-reference).
Without a reload, `debug-with-memlog`, `/recall`, and the prompt hook will not
appear until the next launch.

The **SessionStart** hook fires once per session at startup, so it won't trigger inside the session you installed from. To see it work, **quit Claude Code and open a brand-new session in a project directory** (one with a `package.json` / `go.mod` / `pom.xml` / `Cargo.toml` / etc. for the sniffer to read). The auto-injection lands as a system reminder before the first user prompt.

For a quick sanity check in a fresh session, ask: *"What memlog entries do you have in your starting context? Show me the top 3 titles."* If the hook fired, the model will list them.

The bundled CLI and hooks use the same selected backend. By default that is
`~/.engineering-memlog/entries.jsonl`; set `ENGINEERING_MEMLOG_FILE` before
starting Claude Code to select a different file, or set
`ENGINEERING_MEMLOG_PROVIDER_COMMAND` to use a custom provider. Provider errors
are reported distinctly and never fall back to the file. Use the standalone installation
above only when you also want `memlog` in ordinary terminal sessions or in another
agent that does not load this plugin.

Per-session opt-out: set `MEMLOG_PLUGIN_DISABLE=1` in your shell to skip the whole hook, or `MEMLOG_MANDATE=manual` to keep the ranked-entry injection but turn off mandate auto-load (e.g. when you maintain the mandate by hand in `CLAUDE.md`). Other knobs (entry limit, score threshold, custom log path) documented in `CLAUDE.md` inside this repo.

> Once accepted into Anthropic's official marketplace, you'll also be able to install via `/plugin install engineering-memlog@claude-plugins-official` and browse from `/plugin > Discover`.

## Set up the discipline (without the plugin)

If you're not on Claude Code or don't want hooks, the original prose-only mandate still works for the write side. Copy the block in [MANDATE.md](MANDATE.md) into your agent's rules file. That paragraph turns a logging *tool* into a logging *habit*. The plugin is what closes the read-side loop on top.

## What it isn't

- **Not Claude Code's native auto-memory.** That saves free-form prose about your preferences and project context, per project. This is structured, engineering-incident-shaped, cross-project, and built to be queried as much as read.
- **Not a general agent-memory layer** like Mem0 or OpenMemory. Those are broader and more capable. This is deliberately narrow: one schema, one default file (or a provider you choose), one concern — operational engineering knowledge.

The narrowness is the point. It's an opinion, expressed as a small codebase.

## Security & data flow

**What the built-in plugin reads locally:**

- Manifest files at the project cwd: `go.mod`, `package.json`, `pom.xml`, `Cargo.toml`, `pyproject.toml`, `Gemfile`, etc. — to detect languages and frameworks for the relevance ranker.
- `git remote get-url origin` and `git ls-files` — to detect repo name and run a file-extension census. Both are read-only.
- `CLAUDE.md` / `AGENTS.md` / `.cursorrules` in the cwd (and its parents) — for optional `stack:` / `tags:` hint lines.
- Your engineering-memlog entries — from the default JSONL file. When you
  configure a provider, that executable supplies entries instead.

**What it writes:**

- With the built-in backend, only `entries.jsonl` — append-only, when the agent
  runs `memlog add`. New files are created with mode `0600`; existing permissions
  are preserved. A custom provider receives the validated entry and controls its
  own write surface.

**What it sends over the network:**

- The storage and ranking code sends nothing over the network with the built-in
  backend. The Claude Code hooks place a bounded selection of recalled entries
  into the active Claude conversation context, so those entries are processed
  wherever your configured Claude environment runs under its data-handling terms.
- A custom provider is executable code chosen by you and may access whatever
  network or service you configure it to use; review it and its data handling
  separately. Memlog includes no telemetry, remote API, or embeddings service.

**What it never does:**

- The mandate explicitly forbids logging secrets — tokens, passwords, credentials, private keys, session cookies, connection strings. The schema enforces structure but not secret detection; that's on the agent following the rule.
- The built-in backend does not exfiltrate, transmit, or upload your log anywhere. A custom provider controls its own storage and transmission.

**Sandboxing the plugin per-session:** `MEMLOG_PLUGIN_DISABLE=1` in your shell skips both hooks. Useful when working in a sensitive context where you'd rather not have prior lessons injected.

## Examples

[examples/entries.jsonl](examples/entries.jsonl) — 12 real lessons (sanitized) from production work: Go / GORM gotchas, Next.js build traps, CI and lockfile failures, API-contract bugs. Skim a few — they're the best demonstration of what's worth logging.

## License

[MIT](LICENSE).
