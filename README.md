# engineering-memlog

A shared engineering log your AI coding agent writes to — and reads from — across sessions.

Your agent figures something out the hard way. The session ends, and that knowledge is gone. A week later a different session re-derives the same fix from scratch.

`memlog` fixes that. Before finishing a task, the agent asks itself whether it learned something worth keeping. If yes, it appends a structured entry — problem, cause, fix, prevention — to a single shared log. Next time the symptom shows up, the agent searches the log and skips the re-derivation.

That's the whole thing. One JSONL file, a ~200-line script, and one paragraph of instructions for your agent.

## How it works

Three pieces. The division is the whole idea.

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

## Set up the discipline

Copy the block in [MANDATE.md](MANDATE.md) into your agent's rules file. That paragraph is what turns a logging *tool* into a logging *habit* — an agent will reliably do what a human won't.

## What it isn't

- **Not Claude Code's native auto-memory.** That saves free-form prose about your preferences and project context, per project. This is structured, engineering-incident-shaped, cross-project, and built to be queried as much as read.
- **Not a general agent-memory layer** like Mem0 or OpenMemory. Those are broader and more capable. This is deliberately narrow: one schema, one file, one concern — operational engineering knowledge.

The narrowness is the point. It's an opinion, expressed as 200 lines of code.

## Examples

[examples/entries.jsonl](examples/entries.jsonl) — 12 real lessons (sanitized) from production work: Go / GORM gotchas, Next.js build traps, CI and lockfile failures, API-contract bugs.

## License

[MIT](LICENSE).