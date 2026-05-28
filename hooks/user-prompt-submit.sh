#!/usr/bin/env bash
#
# user-prompt-submit.sh — Claude Code UserPromptSubmit hook for engineering-memlog.
#
# Fires on every user prompt. Reads the prompt from stdin (Claude Code
# convention: hook payload is JSON, with the prompt under .prompt or
# similar — we tolerate both raw-text and JSON inputs). Calls
# memlog-search-prompt which:
#   1. Decides if the prompt LOOKS like a symptom (error / fail / 404 /
#      etc.). If not — silent exit, no injection on benign prompts.
#   2. If yes — extracts quoted strings, known tech tokens, and
#      identifiers. Searches the log. Emits top hits as JSONL.
#
# Output behavior:
#   - On match: prints a system-reminder header + the JSONL matches.
#   - On no symptom OR no match: prints nothing (silent no-op).
#
# Env knobs (same shape as session-start.sh):
#   ENGINEERING_MEMLOG_FILE   — path to entries.jsonl
#   MEMLOG_PLUGIN_DISABLE     — "1" to skip
#   MEMLOG_PLUGIN_PROMPT_LIMIT — top-K (default 5)

set -euo pipefail

if [[ "${MEMLOG_PLUGIN_DISABLE:-0}" == "1" ]]; then
  exit 0
fi

LIMIT="${MEMLOG_PLUGIN_PROMPT_LIMIT:-5}"

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SEARCH="${PLUGIN_ROOT}/scripts/memlog-search-prompt"

if [[ ! -x "$SEARCH" ]]; then
  exit 0
fi

# Read the hook payload. Claude Code passes JSON on stdin; we try to
# extract the prompt text from common fields, falling back to the raw
# stdin if it isn't JSON.
STDIN_RAW="$(cat || true)"
if [[ -z "$STDIN_RAW" ]]; then
  exit 0
fi

PROMPT_TEXT=""
if command -v python3 >/dev/null 2>&1; then
  PROMPT_TEXT="$(printf "%s" "$STDIN_RAW" | python3 -c '
import json, sys
raw = sys.stdin.read()
try:
    data = json.loads(raw)
    if isinstance(data, dict):
        for key in ("prompt", "userPrompt", "user_message", "text", "message"):
            val = data.get(key)
            if isinstance(val, str):
                print(val)
                break
        else:
            # nothing matched — emit the whole JSON so search can still try
            print(raw)
    else:
        print(raw)
except Exception:
    print(raw)
' 2>/dev/null || true)"
fi
# If python failed or returned empty, fall back to the raw stdin.
if [[ -z "$PROMPT_TEXT" ]]; then
  PROMPT_TEXT="$STDIN_RAW"
fi

# Pipe the extracted text to the search script. It exits 0 with no output
# for benign prompts.
HITS="$(printf "%s" "$PROMPT_TEXT" | "$SEARCH" --limit "$LIMIT" 2>/dev/null || true)"
if [[ -z "$HITS" ]]; then
  exit 0
fi

COUNT=$(printf "%s\n" "$HITS" | grep -c . || true)

cat <<EOF
**memlog** — symptom detected in user prompt, ${COUNT} prior lesson(s)
matched. Each line is a full memlog entry (JSON). If one applies, follow
its "prevention" rule and reference it in your reasoning.

$HITS
EOF
