---
description: Search the engineering memlog and inject the top matching prior lessons. Use when you suspect a recurring issue.
argument-hint: <free-text query>
allowed-tools: Bash
---

You will run a memlog search for the query and read the JSONL output back to the user.

Steps:

1. Run the memlog search command with the user's query:

```bash
~/engineering-memory/bin/memlog search "$ARGUMENTS" --json --limit 10
```

If `$ARGUMENTS` is empty, instead run:

```bash
~/engineering-memlog/scripts/memlog-context | ~/engineering-memlog/scripts/memlog-shortlist --file ~/engineering-memory/data/entries.jsonl --limit 10
```

2. Parse each JSONL line. For every hit, show the user a compact summary:
   - `timestamp` (date only, YYYY-MM-DD)
   - `title`
   - one-line excerpt of `problem` (first ~120 chars)
   - `tags` (joined with commas)
   - `confidence`

3. After the list, ask the user which entry (if any) looks relevant to the current task. If they confirm one, retrieve and read its full `prevention` field aloud — that's the rule they should apply.

4. If `memlog` is not installed or the data file is missing, report that clearly and link to the install instructions in the engineering-memlog README.

Important:
- Don't dump raw JSON unless the user asks — present a readable summary.
- Don't paraphrase the `prevention` rule when reading it back; quote it verbatim. Paraphrasing loses precision.
- If zero hits, say so and suggest alternate queries (e.g. broader keywords from the user's question).
