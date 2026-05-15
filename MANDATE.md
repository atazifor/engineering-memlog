# The mandate

This is the load-bearing part of the system. The `memlog` script is
deliberately dumb — it has no idea what is worth remembering. The
*judgment* lives here, in a standing instruction you paste into your AI
agent's always-loaded rules file (`CLAUDE.md`, `.cursorrules`,
`AGENTS.md`, or equivalent).

Copy everything between the `---` lines into that file.

---

## Engineering memory

This project uses a shared, cross-project engineering log at
`~/.engineering-memlog/entries.jsonl`, written and read with the `memlog`
CLI. Treat the log as part of your working memory — it is prior knowledge,
not documentation.

**Before starting a non-trivial task**, search the log for prior lessons
touching the same area, framework, or failure mode:

```bash
memlog search <keyword>
```

If a relevant entry exists, factor it in before diagnosing from scratch.
A two-minute search can replace a thirty-minute rediscovery.

**Before concluding a meaningful task**, ask:

1. Did I learn something reusable?
2. Did I fix something non-obvious?
3. Did I discover a pattern or prevention rule worth preserving?

If the answer to any is yes, append an entry:

```bash
memlog add --json '<JSON object>'
```

For long payloads, write the JSON to a temp file first to avoid
shell-quoting issues, then `memlog add --json "$(cat /tmp/entry.json)"`,
and delete the temp file afterward.

**Log** a reusable item — anything that took real reasoning to diagnose,
is non-obvious, could recur in this or another project, reveals a
framework / infrastructure / deployment behavior worth remembering, or
would simply be annoying to rediscover later.

**Never log** trivial edits, repeated retries, obvious commands with no
lesson, or secrets of any kind — tokens, passwords, credentials, private
keys, session cookies, or connection strings containing secrets.

**Required fields:** `title`, `problem`, `cause`, `fix`, `prevention`,
`artifact`, `repo`, `service`, `environment`, `tags` (array of strings),
`confidence` (numeric, 0.0–1.0), `status` (`draft` is a fine default),
`source` (`claude-code` is a fine default). The script auto-fills
`timestamp` and `id`. See SCHEMA.md for what each field holds.

**Confidence scale:** `0.25` rough suggestion · `0.50` tested locally ·
`0.75` validated in staging · `1.00` validated in production.

Prefer logging a rough draft over losing the lesson. Never include
secrets in an entry.

---

## Setup for a new project

1. Ensure `memlog` is on your PATH (see README).
2. Paste the block above into the project's agent rules file.

That's it. Every future agent session in that project follows the same
search-then-log discipline, contributing to one shared log.