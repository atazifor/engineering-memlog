#!/usr/bin/env bash
#
# session-start.sh — Claude Code SessionStart hook for engineering-memlog.
#
# Runs once at the start of every session and emits a JSON envelope whose
# hookSpecificOutput.additionalContext Claude Code injects into the
# conversation before the first user prompt. It contributes two things,
# each independently:
#
#   1. The mandate — the standing debugging-memory and verified-write
#      instruction. Auto-loaded so the user never has to paste it into
#      CLAUDE.md. Self-suppresses if a current-version mandate is already
#      pasted in a rules file, and can be turned off with MEMLOG_MANDATE=manual.
#
#   2. Ranked prior lessons — the top-K memlog entries relevant to this
#      project, if any.
#
# Either part may be present without the other; if neither is, the hook
# stays silent (exit 0).
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
# only routes the additionalContext string into the model's context.
#
# Env knobs:
#   ENGINEERING_MEMLOG_FILE   — path to entries.jsonl (defaults set in scripts)
#   MEMLOG_PLUGIN_DISABLE     — set to "1" to skip the whole hook (per-session)
#   MEMLOG_MANDATE            — "auto" (default) | "manual" (never auto-load
#                               the mandate; user owns the paste instead)
#   MEMLOG_PLUGIN_LIMIT       — top-K ranked entries (default 6)
#   MEMLOG_PLUGIN_MIN_SCORE   — minimum score to include (default 1.5)

set -euo pipefail

# Whole-hook opt-out.
if [[ "${MEMLOG_PLUGIN_DISABLE:-0}" == "1" ]]; then
  exit 0
fi

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# CLAUDE_PROJECT_DIR is the documented project-cwd env var for hooks.
# Fall back to PWD if not set (e.g. when running this script directly).
PROJECT_CWD="${CLAUDE_PROJECT_DIR:-${PWD:-$(pwd)}}"

# Bump this when the mandate text changes in a way that should re-load over
# an older pasted copy. The marker string lives in MANDATE.md's block, so a
# repo that pasted v2 is detected; one stuck on an older (or no) marker is
# treated as "not current" and the hook loads the fresh mandate anyway.
MANDATE_VERSION="v3"
MANDATE_MARKER="engineering-memlog-mandate ${MANDATE_VERSION}"

# ---------------------------------------------------------------------------
# Part 1: the mandate
# ---------------------------------------------------------------------------
MANDATE_BLOCK=""
if [[ "${MEMLOG_MANDATE:-auto}" != "manual" ]]; then
  # Already pasted (at the current version) into a rules file? Then don't
  # double-load — respect the version-controlled copy.
  already_pasted=""
  for f in "${PROJECT_CWD}/CLAUDE.md" \
           "${PROJECT_CWD}/CLAUDE.local.md" \
           "${HOME}/.claude/CLAUDE.md"; do
    if [[ -f "$f" ]] && grep -qF "$MANDATE_MARKER" "$f" 2>/dev/null; then
      already_pasted="1"
      break
    fi
  done

  if [[ -z "$already_pasted" && -f "${PLUGIN_ROOT}/MANDATE.md" ]]; then
    # Extract the block between the first pair of `---` fences in MANDATE.md
    # (the part the docs tell humans to paste). Single source of truth.
    MANDATE_BLOCK="$(awk '/^---[[:space:]]*$/{n++; next} n==1{print}' \
                       "${PLUGIN_ROOT}/MANDATE.md")"
  fi
fi

# ---------------------------------------------------------------------------
# Part 2: ranked prior lessons (best-effort; never blocks the mandate)
# ---------------------------------------------------------------------------
SHORTLIST=""
LIMIT="${MEMLOG_PLUGIN_LIMIT:-6}"
MIN_SCORE="${MEMLOG_PLUGIN_MIN_SCORE:-1.5}"
CTX="${PLUGIN_ROOT}/scripts/memlog-context"
RANK="${PLUGIN_ROOT}/scripts/memlog-shortlist"
if [[ -x "$CTX" && -x "$RANK" ]]; then
  SHORTLIST="$("$CTX" --cwd "$PROJECT_CWD" 2>/dev/null \
                | "$RANK" --limit "$LIMIT" --min-score "$MIN_SCORE" 2>/dev/null \
                || true)"
fi

# ---------------------------------------------------------------------------
# Part 2.5: write-half health check.
# The mandate tells the agent to run `memlog add`/`search`, but those need the
# CLI on PATH — a separate install step from the plugin. The read-half (this
# hook) works without it, which means a missing/dangling CLI fails SILENTLY:
# lessons keep getting injected while add/search are dead. Detect that and warn
# loudly so the agent doesn't burn a turn rediscovering it. Conservative to
# avoid false positives when the hook's non-interactive PATH differs from the
# agent's shell: a healthy memlog in the standard ~/.local/bin counts as OK
# even if it isn't on this hook's PATH. (`command -v` and `-x` both reject a
# dangling symlink, which is exactly the failure we want to catch.)
CLI_WARNING=""
if ! command -v memlog >/dev/null 2>&1 && [[ ! -x "${HOME}/.local/bin/memlog" ]]; then
  LOGFILE="${ENGINEERING_MEMLOG_FILE:-${HOME}/.engineering-memlog/entries.jsonl}"
  CLI_WARNING="⚠ **memlog write-half unavailable** — the \`memlog\` CLI is not on PATH (missing, or a dangling symlink). The read-half below still works, but \`memlog add\`/\`memlog search\` will fail. Do NOT attempt \`memlog\` shell commands until this is fixed: run \`make install\` in ${PLUGIN_ROOT} (then \`make doctor\` to verify). To read the log meanwhile, the raw file is ${LOGFILE}."
fi

# ---------------------------------------------------------------------------
# Compose the body. Write-half warning first (it qualifies everything below),
# then the mandate (the discipline), then the lessons.
# ---------------------------------------------------------------------------
BODY=""

if [[ -n "$CLI_WARNING" ]]; then
  BODY="$CLI_WARNING"
fi

if [[ -n "$MANDATE_BLOCK" ]]; then
  MANDATE_TEXT="**memlog mandate** — auto-loaded by the engineering-memlog plugin (no
manual paste needed). Treat the following as a standing instruction for this
session: use the debugging skill for failures, and preserve only verified,
non-obvious lessons afterward.
${MANDATE_BLOCK}"
  if [[ -n "$BODY" ]]; then
    BODY="${BODY}

${MANDATE_TEXT}"
  else
    BODY="$MANDATE_TEXT"
  fi
fi

if [[ -n "$SHORTLIST" ]]; then
  COUNT=$(printf "%s\n" "$SHORTLIST" | grep -c . || true)
  ENTRIES="**memlog** — ${COUNT} prior lesson(s) ranked relevant to this project
(by tag / repo / service / framework overlap + recency + confidence). Each line
below is a full memlog entry as JSON. When a current symptom matches one of
these entries' \"problem\" or \"cause\", apply its \"prevention\" rule rather
than re-deriving. Reference the entry's title or id in your reasoning.

Run \`memlog search <query> --json\` (or /recall <query>) for deeper queries
against the full log.

${SHORTLIST}"

  if [[ -n "$BODY" ]]; then
    BODY="${BODY}

---

${ENTRIES}"
  else
    BODY="$ENTRIES"
  fi
fi

# Nothing to say → stay silent.
if [[ -z "$BODY" ]]; then
  exit 0
fi

# Emit the JSON envelope. python3 handles the string→JSON escaping because
# the body contains newlines, quotes, and backslashes (our JSONL does).
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
