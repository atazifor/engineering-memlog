# Provider protocol acceptance — Milestone 5

Date: 2026-09-15

## Completion checklist

- [x] JSONL remains the default with no configuration or dependency changes.
- [x] A versioned command protocol exposes `scan` and `append`.
- [x] CLI `add`, `search`, `list`, and `validate` use the selected provider.
- [x] SessionStart and UserPromptSubmit retrieval use the selected provider.
- [x] Memlog still owns generated bookkeeping, schema checks, and ranking.
- [x] A configured provider never silently falls back to the JSONL file.
- [x] Missing, failing, malformed, and timed-out providers are distinguishable
  from a successful empty scan.
- [x] Non-finite timeouts, oversized responses, and schema-invalid provider
  entries fail cleanly instead of reaching ranking or hook injection.
- [x] Provider output and per-hook injected JSONL have configurable byte bounds.
- [x] Hook outages tell the agent to continue local diagnosis rather than treat
  the result as a miss.
- [x] A runnable stdlib example shows how to adapt another datastore or cache.
- [x] Provider and Claude-context data-flow implications are documented.
- [x] Existing JSONL behavior and the full regression suite remain green.

## Automated verification

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`

The provider cases launch `examples/providers/jsonl-provider` as a separate
process and verify write/read/validate behavior, retrieval scripts, both Claude
hooks, no-fallback failure handling, malformed output, and a bounded timeout.
