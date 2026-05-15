# Entry schema

The log is one append-only file — `entries.jsonl` — with one JSON object
per line ([JSONL](https://jsonlines.org/)). **The file format is the
contract.** The `memlog` script is one reference implementation; anything
that can append a valid line and grep the file is a valid client.

## Fields

An entry has 13 author-supplied fields, in three groups, plus 2 the tool
fills in.

### The lesson — the reason the entry exists

| field | what it holds |
|---|---|
| `title` | one-line summary, specific enough to recognize in a search |
| `problem` | the observed symptom — what looked wrong |
| `cause` | the root cause — *why* it was possible |
| `fix` | what resolved it |
| `prevention` | the rule that stops it recurring |

`cause` and `prevention` are the point. Git already records the `fix` —
it's the diff. Git does not record why the bug was possible, or how to
avoid it next time.

### Retrieval metadata — so you can find it later

| field | what it holds |
|---|---|
| `artifact` | the file, function, config, or command involved |
| `repo` | repository name |
| `service` | service / app / package within the repo |
| `environment` | `local`, `ci`, `staging`, `production`, ... |
| `tags` | array of strings — frameworks, tools, themes |

### Bookkeeping

| field | what it holds |
|---|---|
| `confidence` | number `0.0`–`1.0` — how sure the lesson generalizes |
| `status` | `draft` (default); promote or prune later |
| `source` | who wrote it — e.g. `claude-code` |

### Auto-filled by the tool

`timestamp` (RFC3339, UTC) and `id`. Do not supply these — `memlog add`
sets them.

## Confidence scale

| value | meaning |
|---|---|
| `0.25` | rough agent suggestion |
| `0.50` | tested locally |
| `0.75` | validated in staging |
| `1.00` | validated in production |

## One entry, formatted

`examples/entries.jsonl` holds 12 real (sanitized) entries. Each is a
single line; shown here formatted for readability:

```json
{
  "id": "mem-1747300720",
  "timestamp": "2026-05-15T09:18:40Z",
  "title": "A backend field feeding a client-side formatter must be machine-parseable, not pre-formatted",
  "problem": "A list view's relative-date formatting silently did nothing — every row showed a raw string instead of 'Today' / 'Yesterday'.",
  "cause": "The API returned the date as a pre-formatted display string ('27th Apr 2025'). The client formatter calls Date.parse(), which cannot read that format, fails silently, and falls back to the raw value.",
  "fix": "Return the field as an ISO-8601 / RFC3339 timestamp; let the client own all presentation formatting.",
  "prevention": "Any field that feeds a client-side formatter must be machine-parseable. Keep display formatting on the client — the API sends timestamps, not sentences.",
  "artifact": "API response builder",
  "repo": "api-server",
  "service": "",
  "environment": "production",
  "tags": ["api-contract", "date-formatting", "frontend"],
  "confidence": 0.9,
  "status": "draft",
  "source": "claude-code"
}
```