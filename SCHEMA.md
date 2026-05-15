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
  "id": "mem-1745905159",
  "timestamp": "2026-04-29T05:39:19Z",
  "title": "A Go struct with no json tags serializes as PascalCase and breaks snake_case clients",
  "problem": "A settings page always showed default values regardless of what was saved. The PUT endpoint worked and the DB rows were correct, but the UI never reflected saved values.",
  "cause": "The model had gorm column tags but no json tags. Go's encoding/json defaults to the literal Go field name (PascalCase), so the API returned AutoAcceptDelaySeconds while the client read auto_accept_delay_seconds and fell through to defaults on every read.",
  "fix": "Added explicit snake_case json tags to every field of the struct. Verified end-to-end with curl that the response used snake_case keys.",
  "prevention": "Any Go struct that crosses an HTTP boundary needs explicit json tags from the start. If a struct is both a DB row and an HTTP payload it needs both tag sets: gorm:\"column:foo\" json:\"foo\".",
  "artifact": "Go model struct used as a JSON response body",
  "repo": "api-server",
  "service": "settings",
  "environment": "production",
  "tags": ["go", "gorm", "json", "api-contract"],
  "confidence": 0.95,
  "status": "draft",
  "source": "claude-code"
}
```