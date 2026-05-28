# engineering-memlog

A shared engineering log your AI coding agent writes to — and reads from — across sessions.

Your agent figures something out the hard way. The session ends, and that knowledge is gone. A week later a different session re-derives the same fix from scratch.

`memlog` fixes that. Before finishing a task, the agent asks itself whether it learned something worth keeping. If yes, it appends a structured entry — problem, cause, fix, prevention — to a single shared log. Next time the symptom shows up, the agent searches the log and skips the re-derivation.

That's the whole thing. One JSONL file, a ~200-line script, and one paragraph of instructions for your agent.

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

**With the plugin installed (Claude Code only):** a SessionStart hook auto-injects the top relevant entries against the project's sniffed signature before you type. A UserPromptSubmit hook auto-injects matches whenever your prompt looks symptom-shaped (errors, failures, 4xx/5xx, framework names). The agent never has to remember to look — the look already happened. Writing still flows through the mandate. See the next section for install.

## Closing the read-side loop — Claude Code plugin

Prose mandates work for the write side but agents reliably **drift past the "search before you work" half**. The result is a write-mostly system: lessons land but rarely surface in time to prevent a re-derivation.

This repo ships a Claude Code plugin that fixes that by making the read side automatic, not voluntary:

- **SessionStart hook** sniffs the project's languages / frameworks / repo / service from manifest files (`go.mod`, `package.json`, `pom.xml`, `Cargo.toml`, …), ranks entries by tag/repo/service overlap + recency + confidence, and injects the top ~6 as a system reminder at session boot. The agent sees relevant prior lessons before it sees the first user prompt.
- **UserPromptSubmit hook** scans each prompt for symptom-shaped text (errors, failures, 4xx/5xx, framework names) and, on a hit, extracts likely keywords (quoted strings, known tech tokens) and injects matches. Silent on benign prompts — no per-turn token bloat.
- **`/recall <query>`** slash command for explicit deep dive.

The pieces are all stdlib Python plus bash hooks — same "deliberately dumb" discipline as the core CLI. See `scripts/memlog-context`, `scripts/memlog-shortlist`, `scripts/memlog-search-prompt`, and `hooks/`.

### Install the plugin

The plugin lives in this repo. Drop it into the Claude Code plugins directory and the hooks fire on every session:

```bash
# clone if you haven't already
git clone https://github.com/atazifor/engineering-memlog ~/engineering-memlog

# put the memlog CLI on PATH (one-time)
cp ~/engineering-memlog/memlog ~/.local/bin/memlog && chmod +x ~/.local/bin/memlog

# install the plugin (Claude Code 1.0.123+)
mkdir -p ~/.claude/plugins
ln -s ~/engineering-memlog ~/.claude/plugins/engineering-memlog
```

On next session start the hook injects relevant entries; on symptom-shaped prompts the per-prompt hook fires. Per-session opt-out: `MEMLOG_PLUGIN_DISABLE=1`. Other knobs documented in `CLAUDE.md` inside this repo.

## Set up the discipline (without the plugin)

If you're not on Claude Code or don't want hooks, the original prose-only mandate still works for the write side. Copy the block in [MANDATE.md](MANDATE.md) into your agent's rules file. That paragraph turns a logging *tool* into a logging *habit*. The plugin is what closes the read-side loop on top.

## What it isn't

- **Not Claude Code's native auto-memory.** That saves free-form prose about your preferences and project context, per project. This is structured, engineering-incident-shaped, cross-project, and built to be queried as much as read.
- **Not a general agent-memory layer** like Mem0 or OpenMemory. Those are broader and more capable. This is deliberately narrow: one schema, one file, one concern — operational engineering knowledge.

The narrowness is the point. It's an opinion, expressed as 200 lines of code.

## Examples

[examples/entries.jsonl](examples/entries.jsonl) — 12 real lessons (sanitized) from production work: Go / GORM gotchas, Next.js build traps, CI and lockfile failures, API-contract bugs. Skim a few — they're the best demonstration of what's worth logging.

## License

[MIT](LICENSE).