#!/usr/bin/env bash
#
# session-start.sh — Claude Code SessionStart hook for engineering-memlog.
#
# Runs once at the start of every session. Sniffs the project signature
# from $CLAUDE_PROJECT_DIR, ranks entries.jsonl against it, and emits a
# JSON envelope with the top K matches in hookSpecificOutput.additionalContext.
# Claude Code injects that string into the conversation as additional
# context the model sees before the first user prompt.
#
# Output contract (Claude Code 1.0.123+):
#   {
#     "hookSpecificOutput": {
#       "hookEventName": "SessionStart",
#       "additionalContext": "<human-readable text with JSONL inside>"
#     }
#   }
#
# Raw stdout outside this envelope is silently dropped — the plugin loader
# only routes the additionalContext string into the model's context. That
# was the bug that kept us mute through the first round of testing.
#
# Env knobs:
#   ENGINEERING_MEMLOG_FILE   — path to entries.jsonl (defaults set in scripts)
#   MEMLOG_PLUGIN_DISABLE     — set to "1" to skip injection (per-session opt-out)
#   MEMLOG_PLUGIN_LIMIT       — top-K (default 6)
#   MEMLOG_PLUGIN_MIN_SCORE   — minimum score to include (default 1.5)

set -euo pipefail

# Allow per-session disable. Empty JSON envelope is fine — Claude Code
# just ignores it.
if [[ "${MEMLOG_PLUGIN_DISABLE:-0}" == "1" ]]; then
  exit 0
fi

LIMIT="${MEMLOG_PLUGIN_LIMIT:-6}"
MIN_SCORE="${MEMLOG_PLUGIN_MIN_SCORE:-1.5}"

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
CTX="${PLUGIN_ROOT}/scripts/memlog-context"
RANK="${PLUGIN_ROOT}/scripts/memlog-shortlist"

# If either script is missing, exit cleanly — don't break the user's
# session over a plugin install glitch.
if [[ ! -x "$CTX" || ! -x "$RANK" ]]; then
  exit 0
fi

# CLAUDE_PROJECT_DIR is the documented project-cwd env var for hooks.
# Fall back to PWD if not set (e.g. when running this script directly).
PROJECT_CWD="${CLAUDE_PROJECT_DIR:-${PWD:-$(pwd)}}"

# Run sniffer → ranker. Capture; if there's no match, emit nothing
# (still exit 0 — silence is the right answer for "no relevant lessons").
SHORTLIST="$("$CTX" --cwd "$PROJECT_CWD" 2>/dev/null \
              | "$RANK" --limit "$LIMIT" --min-score "$MIN_SCORE" 2>/dev/null \
              || true)"

if [[ -z "$SHORTLIST" ]]; then
  exit 0
fi

# Count matches for the human prelude.
COUNT=$(printf "%s\n" "$SHORTLIST" | grep -c . || true)

# Compose the additionalContext body. The model will see this as a system
# reminder injected at session start. Header explains the format and the
# instruction (consult before re-deriving); JSONL entries follow.
BODY="$(cat <<EOF
**memlog** — auto-injected by the engineering-memlog plugin.

${COUNT} prior lesson(s) ranked relevant to this project (by tag / repo /
service / framework overlap + recency + confidence). Each line below is
a full memlog entry as JSON. When a current symptom matches one of
these entries' "problem" or "cause", apply its "prevention" rule rather
than re-deriving. Reference the entry's title or id in your reasoning.

Run \`memlog search <query> --json\` (or /recall <query>) for deeper
queries against the full log.

${SHORTLIST}
EOF
)"

# Emit the JSON envelope Claude Code expects. python3 is used for the
# string→JSON escape because doing it in bash is error-prone for content
# that contains newlines, quotes, and backslashes (which our JSONL does).
python3 -c '
import json, sys
body = sys.stdin.read()
out = {
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": body
    }
}
print(json.dumps(out, ensure_ascii=False))
' <<<"$BODY"
