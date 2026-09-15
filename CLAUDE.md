# engineering-memlog plugin — agent instructions

This file is auto-loaded by the engineering-memlog plugin and forms the
agent's working contract with the log. Two halves: read before you work,
write after.

## How the log gets into your context

The plugin closes the read side **without relying on you to remember**:

- **SessionStart hook** runs once per session, sniffs the project signature
  (languages, frameworks, repo, service hint), and injects the top 6 most
  relevant prior lessons as a system reminder you see at session boot.
- **UserPromptSubmit hook** scans each prompt for symptom-shaped text
  (errors, failures, HTTP 4xx/5xx, "broken", "not working", framework
  names) and, when triggered, automatically searches the log for likely
  keywords and injects matches before you respond. Silent on benign
  prompts — no per-turn noise.
- **`/recall <query>`** slash command for explicit deep-dive search when
  you suspect something but the hooks didn't catch it.

When the hook injects entries, treat them as **prior knowledge, not
documentation**. Each line is a full JSON memlog entry. If a current
symptom matches one of the entries' `problem` or `cause`, apply its
`prevention` rule rather than re-deriving from scratch. Reference the
entry's `id` or `title` in your reasoning so the human can trace where
the rule came from.

## Search the log yourself when warranted

The hooks fire automatically, but you should also run the log yourself
when:

- The injected entries didn't include something you suspect exists.
- You hit an unfamiliar error during the work (not just at prompt time).
- You're about to propose a fix for a non-obvious bug.

Run it as a Bash command:

```bash
memlog search "frozen-lockfile" --json --limit 10
```

Search for the concrete signal — keywords from the error message, the
observed symptom, the framework or tool involved. No match is normal —
just proceed.

## Append a lesson after you work

Before concluding a meaningful task, ask:

1. Did I learn something reusable?
2. Did I fix something non-obvious?
3. Did I discover a pattern or prevention rule worth preserving?

If the answer to any is yes, append an entry:

```bash
memlog add --json '<JSON object>'
```

For long payloads, write the JSON to a temp file first to avoid shell-
quoting issues, then `memlog add --json "$(cat /tmp/entry.json)"`, and
delete the temp file afterward.

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
`timestamp` and `id`. See SCHEMA.md.

**Confidence scale:** `0.25` rough suggestion · `0.50` tested locally ·
`0.75` validated in staging · `1.00` validated in production.

Prefer logging a rough draft over losing the lesson. Never include
secrets in an entry.

## Plugin knobs (env vars)

If a session needs to opt out or tune behavior:

- `MEMLOG_PLUGIN_DISABLE=1` — skip both hooks for this session
- `MEMLOG_MANDATE=manual` — keep ranked-entry injection but turn off mandate
  auto-load (the SessionStart hook otherwise auto-loads the mandate unless a
  current-version copy is already pasted in a `CLAUDE.md`)
- `MEMLOG_PLUGIN_LIMIT=N` — number of session-start entries to inject (default 6)
- `MEMLOG_PLUGIN_MIN_SCORE=F` — drop session-start entries below this score (default 1.5)
- `MEMLOG_PLUGIN_PROMPT_LIMIT=N` — number of per-prompt hits to inject (default 5)
- `ENGINEERING_MEMLOG_FILE=PATH` — override the log file path
