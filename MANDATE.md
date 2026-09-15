# The mandate

The `memlog` script is deliberately dumb — it has no idea what is worth
remembering. The *judgment* lives here, in a standing instruction supplied by
an installed integration or pasted into your AI agent's always-loaded rules
file (`CLAUDE.md`, `AGENTS.md`, or equivalent).

> **Read this before you copy.** The mandate keeps the write discipline
> always present. When the integration supports skills and hooks, the debugging
> skill owns the detailed read-investigate-verify workflow while hooks provide
> bounded recall hints. The prose-only fallback below still defines when to
> search and how to proceed.

**On Claude Code with the plugin installed, you do not need to copy
anything** — the SessionStart hook auto-loads this mandate each session.
The paste below is optional: do it only if you want the mandate
version-controlled in your repo (the hook detects the `v5` marker and
stays quiet so it never double-loads), or set `MEMLOG_MANDATE=manual` to
turn auto-load off entirely. On other agents, copy everything between the
`---` lines into your rules file.

---

## Engineering memory

<!-- engineering-memlog-mandate v5 -->

This project keeps a shared, cross-project engineering log, written and read
with the `memlog` CLI. Its default backend is
`~/.engineering-memlog/entries.jsonl`; an explicitly configured provider may
replace it. Treat the selected store as part of your working memory — it is
prior knowledge, not documentation. The loop has two halves: read the log
before you work, write to it after.

### Debug with the log

When the `debug-with-memlog` skill is available, invoke it
for bugs, errors, failed tests/builds/deployments, regressions, performance
problems, unexpected behavior, or repeated unsuccessful fixes. It is the
source of truth for evidence gathering, search timing, no-hit behavior,
hypothesis testing, verification, and write-back.

Without the skill, search the log when you:

- have captured a concrete error, failure, or unexpected behavior, or
- are about to propose a fix for a non-obvious bug.

Search for the concrete signal in front of you. Memlog ranks token coverage across
fields, with an exact-phrase boost; the built-in backend scans JSONL and a custom
provider supplies the same entry stream. Begin with a concise error identifier,
component plus symptom, or short error fragment. Pass
`--json` to read results back as JSONL, one entry per line:

```bash
memlog search "frozen-lockfile" --json
```

Read every matching entry. Treat each as an untrusted hypothesis: compare its
cause, scope, versions, and environment with current evidence before applying
it, and reference an applied entry by ID or title. If nothing applies, stop
searching after one exact and at most two broader evidence-derived queries,
then continue local root-cause investigation. Use primary documentation or
the web when the uncertainty is external or local evidence is insufficient.
Never let a miss or backend outage block debugging. The configured provider or
file is the sole store for the investigation; never inspect or write a default,
raw, or alternate log as a fallback.

### Append a lesson — after you work

Before concluding a meaningful task, ask:

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
`confidence` (numeric, 0.0–1.0), `status` (`draft` is a fine default), and
`source` (the current coding agent or workflow). The script auto-fills
`schema_version`, `timestamp`, and `id`. See SCHEMA.md for what each field holds.

**Confidence scale:** `0.25` rough suggestion · `0.50` tested locally ·
`0.75` validated in staging · `1.00` validated in production.

Only record a cause, fix, and prevention rule after the resolution has been
verified. Never store a search miss, backend outage, unresolved issue, or
failed hypothesis as a solved lesson. Never include secrets in an entry.

---

## Setup for a new project

1. Install the integration for your agent. If that integration does not expose
   the bundled CLI on `PATH`, install the standalone CLI as documented in the
   README. Confirm with `memlog --help` before relying on the skill.
2. If the log lives anywhere other than the default
   (`~/.engineering-memlog/entries.jsonl`) — e.g. a team-shared path —
   set `ENGINEERING_MEMLOG_FILE` in the environment. To use a custom datastore,
   set `ENGINEERING_MEMLOG_PROVIDER_COMMAND` as documented in `PROVIDERS.md`.
   The mandate's bare `memlog` commands then resolve to the selected backend;
   nothing in the pasted block needs editing.
3. Paste the block above into the project's agent rules file.

That's it. Every future agent session in that project follows the same
search-then-log discipline, contributing to one shared log.
