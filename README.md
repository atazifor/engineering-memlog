# engineering-memlog

**Durable engineering memory for AI coding agents.** A discipline, and a
~200-line implementation.

Your AI coding agent is brilliant and completely amnesiac. Every session
starts from zero and re-derives things it — or another session — already
worked out last week. `memlog` is a small, opinionated practice that
captures what an agent learns, so the next session doesn't pay for it again.

It is not a product, not a service, and not trying to be. One JSONL file,
one ~200-line script, one paragraph of instructions for your agent.

## The idea

Git records *what changed*. Code comments record *what the code does*.
Neither records the **operational lesson** — what broke, why it was
possible, and the rule that prevents it next time. That knowledge is
exactly what an agent generates constantly and retains never.

The reframe that makes this work: **the log is not documentation for
humans — it is prior knowledge for the next agent.** Every lesson written
once is a lesson no future session has to rediscover.

## How it works — three parts

**1. A structured log.** One append-only file, `entries.jsonl` — one JSON
object per line, shared across every project. See [SCHEMA.md](SCHEMA.md).

**2. A mandate.** A standing instruction in your agent's always-loaded
rules file (`CLAUDE.md`, `.cursorrules`, `AGENTS.md`). It tells the agent
to *search* the log before non-trivial work, and *append* a lesson after
it. See [CLAUDE-snippet.md](CLAUDE-snippet.md) — copy it verbatim.

**3. A CLI.** `memlog` — `add`, `search`, `list`. ~200 lines of Python,
standard library only.

**The division is the whole idea.** The script is deliberately dumb: it
appends a JSON line and greps the file. It has *zero* judgment. All the
intelligence — what is worth logging, what never to log, when to search —
lives in the mandate. That is why the script is small, and why it is
replaceable: the file format is the contract, the Python is one
implementation.

## Install

`memlog` is a single file. `python3` (3.8+) is the only requirement — no
packages, no service.

```bash
git clone https://github.com/atazifor/engineering-memlog
cp engineering-memlog/memlog ~/.local/bin/memlog   # or anywhere on PATH
chmod +x ~/.local/bin/memlog
memlog --help
```

The log lives at `~/.engineering-memlog/entries.jsonl` by default. Point
it elsewhere — e.g. a path inside a repo, so a team can commit and share
it — with `--file` or the `ENGINEERING_MEMLOG_FILE` environment variable.

## Usage

```bash
# append a lesson
memlog add --json '{ "title": "...", "problem": "...", ... }'

# search before starting work
memlog search "frozen-lockfile"

# browse, newest first
memlog list --reverse
```

In practice you rarely run `add` by hand — your agent does, because the
mandate tells it to.

## Set up the discipline

Copy the block in [CLAUDE-snippet.md](CLAUDE-snippet.md) into your
project's agent rules file. That single paragraph is what turns a logging
*tool* into a logging *habit* — an agent will reliably do what a human
won't.

## What it isn't

- **Not Claude Code's native auto-memory.** That saves free-form prose
  about your preferences and project context, per project. This is
  structured, engineering-incident-shaped, cross-project, and built to be
  *queried* as much as read.
- **Not a general agent-memory layer** like Mem0 or OpenMemory. Those are
  broader and more capable. This is deliberately narrow: one schema, one
  file, one concern — operational engineering knowledge.

The narrowness is the point. It is an opinion, expressed as 200 lines of
code.

## Examples

[examples/entries.jsonl](examples/entries.jsonl) — 12 real lessons
(sanitized) from production work: Go / GORM gotchas, Next.js build traps,
CI and lockfile failures, API-contract bugs.

## License

TBD.