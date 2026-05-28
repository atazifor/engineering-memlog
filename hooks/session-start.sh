#!/usr/bin/env bash
#
# session-start.sh — Claude Code SessionStart hook for engineering-memlog.
#
# Runs once at the start of every session. Sniffs the project signature
# from the cwd, ranks the entries.jsonl against it, and prints the top K
# matches as a system reminder for the LLM to see at session boot.
#
# Hooked via .claude/settings.json (project-level) or ~/.claude/settings.json
# (user-level):
#
#   {
#     "hooks": {
#       "SessionStart": [
#         { "hooks": [{ "type": "command",
#                       "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh" }]}
#       ]
#     }
#   }
#
# Output: a single JSON object with `hookSpecificOutput.additionalContext`
# is the canonical Claude Code v1.0.123+ contract. We keep it simple and
# print to stdout — the harness wraps it as a system reminder.
#
# Env knobs:
#   ENGINEERING_MEMLOG_FILE   — path to entries.jsonl (defaults set in scripts)
#   MEMLOG_PLUGIN_DISABLE     — set to "1" to skip injection (per-session opt-out)
#   MEMLOG_PLUGIN_LIMIT       — top-K (default 6)
#   MEMLOG_PLUGIN_MIN_SCORE   — minimum score to include (default 1.5)

set -euo pipefail

# Allow per-session disable.
if [[ "${MEMLOG_PLUGIN_DISABLE:-0}" == "1" ]]; then
  exit 0
fi

LIMIT="${MEMLOG_PLUGIN_LIMIT:-6}"
MIN_SCORE="${MEMLOG_PLUGIN_MIN_SCORE:-1.5}"

# CLAUDE_PLUGIN_ROOT is set by the Claude Code plugin loader. Fall back to
# the script's own location for direct testing.
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
CTX="${PLUGIN_ROOT}/scripts/memlog-context"
RANK="${PLUGIN_ROOT}/scripts/memlog-shortlist"

# If either script is missing, exit cleanly — don't break the user's
# session over a plugin install glitch.
if [[ ! -x "$CTX" || ! -x "$RANK" ]]; then
  exit 0
fi

# CWD when the hook fires reflects the user's project (Claude Code sets it).
# We pass it explicitly so it survives env-var stripping.
PROJECT_CWD="${PWD:-$(pwd)}"

# Run sniffer → ranker. Capture and only emit if there's at least one match.
SHORTLIST="$("$CTX" --cwd "$PROJECT_CWD" 2>/dev/null \
              | "$RANK" --limit "$LIMIT" --min-score "$MIN_SCORE" 2>/dev/null \
              || true)"

if [[ -z "$SHORTLIST" ]]; then
  exit 0
fi

# Count matches for the prelude.
COUNT=$(printf "%s\n" "$SHORTLIST" | grep -c . || true)

# Compose the system-reminder body. JSONL after a one-line prelude so the
# model sees clear delimiters between header and data.
cat <<EOF
**memlog** — auto-injected by the engineering-memlog plugin.

${COUNT} prior lesson(s) ranked relevant to this project. Each line below
is a full memlog entry (JSON). When a current symptom matches one of
these entries' "problem" or "cause", apply its "prevention" rule rather
than re-deriving. Run \`memlog search <query> --json\` for deeper dives.

$SHORTLIST
EOF
