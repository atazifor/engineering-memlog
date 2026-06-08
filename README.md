# engineering-memlog

**Your AI coding agent keeps solving the same problems from scratch every session.** Give it a memory — a shared, searchable log of fixes it writes after work and auto-recalls before, across sessions and projects. Works with Claude Code (one-command plugin), Cursor, and any agent that reads a `CLAUDE.md` / `AGENTS.md` / `.cursorrules`.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-d97757)
![dependencies: stdlib only](https://img.shields.io/badge/dependencies-stdlib%20only-brightgreen)

> **The problem:** an AI agent figures something out the hard way, the session ends, and that knowledge is gone. A week later a different session re-derives the same fix from scratch.
>
> **The fix:** before finishing a task, the agent appends a structured lesson — *problem, cause, fix, prevention* — to one shared JSONL log. Next time the symptom shows up, it searches the log and skips the re-derivation.

That's the whole thing: **one JSONL file, a ~200-line stdlib script, and one paragraph of instructions for your agent.** No database, no embeddings, no network calls. On Claude Code, a plugin makes the read-half automatic — relevant prior lessons are injected into context before you type.

**Keywords:** AI agent memory · persistent memory for LLM coding assistants · Claude Code plugin · Cursor / AGENTS.md · cross-project knowledge base · stop repeating bugs.

## The three pieces

The division is the whole idea.

**1. A structured log.** One append-only file, `entries.jsonl` — one JSON object per line, shared across every project. See [SCHEMA.md](SCHEMA.md).

**2. A mandate.** One paragraph in your agent's rules file (`CLAUDE.md`, `.cursorrules`, `AGENTS.md`). It tells the agent to search the log before non-trivial work and append a lesson after. See [MANDATE.md](MANDATE.md) — copy it verbatim.

**3. A CLI.** `memlog add`, `search`, `list`. ~200 lines of Python, standard library only.

The script is deliberately dumb: it appends a JSON line and greps the file. Zero judgment. All the intelligence — what's worth logging, what never to log, when to search — lives in the mandate. That's why the script is small, and why it's replaceable: the file format is the contract, the Python is one implementation.

## Install

`python3` (3.8+) is the only requirement.

```bash
git clone https://github.com/atazifor/engineering-memlog
cp engineering-memlog/memlog ~/.local/bin/memlog   # or anywhere on PATH
chmod +x ~/.local/bin/memlog
memlog --help
```

The log lives at `~/.engineering-memlog/entries.jsonl` by default. Override with `--file` or `ENGINEERING_MEMLOG_FILE` — point it inside a repo if you want a team to share one.

## Usage

```bash
# append a lesson
memlog add --json '{ "title": "...", "problem": "...", ... }'

# search before starting work
memlog search "frozen-lockfile"

# browse, newest first
memlog list --reverse
```

In practice you rarely run `add` by hand. Your agent does, because the mandate tells it to.

## How your agent uses the log

The agent uses the same CLI you do — no embeddings, no MCP server required. Two paths, depending on whether the plugin is installed.

**With the [mandate](MANDATE.md) only (any agent, any IDE):** after a meaningful task, the agent runs `memlog add` to append a structured entry. When it remembers, it also runs `memlog search` against a fresh symptom and follows the matching entry's `prevention` rule. The write half is reliable; the read half drifts in practice — that's the gap the plugin fills.

**With the plugin installed (Claude Code only):** a SessionStart hook auto-injects the top relevant entries against the project's sniffed signature before you type. A UserPromptSubmit hook auto-injects matches whenever your prompt looks symptom-shaped (errors, failures, 4xx/5xx, framework names). The agent never has to remember to look — the look already happened. **The same SessionStart hook also auto-loads the [mandate](MANDATE.md)** for the write half, so plugin users don't need to paste anything into a per-project rules file — both halves of the loop travel with the install. The auto-load is idempotent: if you *do* paste the mandate into a `CLAUDE.md` (it carries a version marker), the hook detects it and stays quiet so it never double-loads; set `MEMLOG_MANDATE=manual` to turn auto-load off entirely. See the next section for the install commands.

## Closing the read-side loop — Claude Code plugin

Prose mandates work for the write side but agents reliably **drift past the "search before you work" half**. The result is a write-mostly system: lessons land but rarely surface in time to prevent a re-derivation.

This repo ships a Claude Code plugin that fixes that by making the read side automatic, not voluntary:

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

The `/reload-plugins` step registers the plugin's commands and hooks in the current session — without it, `/recall` and the UserPromptSubmit hook won't appear until you next launch Claude Code.

The **SessionStart** hook fires once per session at startup, so it won't trigger inside the session you installed from. To see it work, **quit Claude Code and open a brand-new session in a project directory** (one with a `package.json` / `go.mod` / `pom.xml` / `Cargo.toml` / etc. for the sniffer to read). The auto-injection lands as a system reminder before the first user prompt.

For a quick sanity check in a fresh session, ask: *"What memlog entries do you have in your starting context? Show me the top 3 titles."* If the hook fired, the model will list them.

You'll also want the `memlog` CLI on your PATH so the plugin's hooks can write to a single shared log (the install above only adds the read-side hooks; the CLI lives separately):

```bash
git clone https://github.com/atazifor/engineering-memlog ~/engineering-memlog
cp ~/engineering-memlog/memlog ~/.local/bin/memlog && chmod +x ~/.local/bin/memlog
```

Per-session opt-out: set `MEMLOG_PLUGIN_DISABLE=1` in your shell to skip the whole hook, or `MEMLOG_MANDATE=manual` to keep the ranked-entry injection but turn off mandate auto-load (e.g. when you maintain the mandate by hand in `CLAUDE.md`). Other knobs (entry limit, score threshold, custom log path) documented in `CLAUDE.md` inside this repo.

> Once accepted into Anthropic's official marketplace, you'll also be able to install via `/plugin install engineering-memlog@claude-plugins-official` and browse from `/plugin > Discover`.

## Set up the discipline (without the plugin)

If you're not on Claude Code or don't want hooks, the original prose-only mandate still works for the write side. Copy the block in [MANDATE.md](MANDATE.md) into your agent's rules file. That paragraph turns a logging *tool* into a logging *habit*. The plugin is what closes the read-side loop on top.

## What it isn't

- **Not Claude Code's native auto-memory.** That saves free-form prose about your preferences and project context, per project. This is structured, engineering-incident-shaped, cross-project, and built to be queried as much as read.
- **Not a general agent-memory layer** like Mem0 or OpenMemory. Those are broader and more capable. This is deliberately narrow: one schema, one file, one concern — operational engineering knowledge.

The narrowness is the point. It's an opinion, expressed as 200 lines of code.

## Security & data flow

**What it reads** (locally only):

- Manifest files at the project cwd: `go.mod`, `package.json`, `pom.xml`, `Cargo.toml`, `pyproject.toml`, `Gemfile`, etc. — to detect languages and frameworks for the relevance ranker.
- `git remote get-url origin` and `git ls-files` — to detect repo name and run a file-extension census. Both are read-only.
- `CLAUDE.md` / `AGENTS.md` / `.cursorrules` in the cwd (and its parents) — for optional `stack:` / `tags:` hint lines.
- Your engineering-memlog JSONL file — by default `~/.engineering-memlog/entries.jsonl` (override with `ENGINEERING_MEMLOG_FILE`).

**What it writes:**

- `entries.jsonl` — append-only, when the agent runs `memlog add`. That's the entire write surface.

**What it sends over the network:**

- **Nothing.** All processing — sniffing, ranking, searching — runs in stdlib Python locally. No telemetry, no remote API calls, no embeddings service, no LLM-in-the-loop. The mandate prose tells the agent what to remember; the deterministic ranker decides what to surface. There is no network code in this plugin.

**What it never does:**

- The mandate explicitly forbids logging secrets — tokens, passwords, credentials, private keys, session cookies, connection strings. The schema enforces structure but not secret detection; that's on the agent following the rule.
- It does not exfiltrate, transmit, or upload your log anywhere. The log is your file on your disk.

**Sandboxing the plugin per-session:** `MEMLOG_PLUGIN_DISABLE=1` in your shell skips both hooks. Useful when working in a sensitive context where you'd rather not have prior lessons injected.

## Examples

[examples/entries.jsonl](examples/entries.jsonl) — 12 real lessons (sanitized) from production work: Go / GORM gotchas, Next.js build traps, CI and lockfile failures, API-contract bugs. Skim a few — they're the best demonstration of what's worth logging.

## License

[MIT](LICENSE).