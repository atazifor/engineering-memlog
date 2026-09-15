#!/usr/bin/env python3
"""Recall Memlog lessons after a Bash command exposes a concrete failure.

An agent can discover a failure only after the user's prompt, so prompt-time recall
cannot cover every investigation. This hook watches Bash results, stays silent for
ordinary commands and successful checks, and searches only when test/build/deploy
commands or strong diagnostic output establish a useful failure fingerprint.
"""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


PLUGIN_ROOT = Path(
    os.environ.get(
        "PLUGIN_ROOT",
        os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[1]),
    )
)
SEARCH = PLUGIN_ROOT / "scripts" / "memlog-search-prompt"

# High-specificity signatures are allowed to trigger even when a project wraps
# the underlying test command in another script. Avoid broad strings such as
# "error" or "not found", which would turn routine shell misses into noise.
STRONG_FAILURE_RE = re.compile(
    r"(?:"
    r"^Traceback \(most recent call last\):|"
    r"\bAssertionError\b|"
    r"^FAILED \([^\n]*failures?=|"
    r"^FAIL:\s+\S|"
    r"^--- FAIL:\s+\S|"
    r"^FAIL(?:\s*$|\s+\S)|"
    r"^=+\s+[^\n]*(?:failed|error)[^\n]*=+$|"
    r"\bnpm ERR!\b|"
    r"\bBUILD (?:FAILED|FAILURE)\b|"
    r"^panic:\s+|"
    r"\berror TS\d{3,5}:|"
    r"\btests? failed\b|"
    r"\b[1-9]\d* failed,\s*\d+ passed\b"
    r")",
    re.IGNORECASE | re.MULTILINE,
)

# Invocation mistakes do not carry a reusable root-cause fingerprint and should
# not create hook noise merely because a test runner exited non-zero.
TRIVIAL_INVOCATION_RE = re.compile(
    r"(?:"
    r"file or directory not found|"
    r"no tests? (?:ran|collected|found)|"
    r"collected 0 items|"
    r"unrecognized arguments?|unknown option|"
    r"usage:\s*(?:pytest|unittest|cargo|go|npm|pnpm|yarn)|"
    r"(?:command )?not found|"
    r"can't open file[^\n]*no such file"
    r")",
    re.IGNORECASE,
)

SHELL_BREAKS = {"&&", "||", ";", "|", "&", "(", ")"}
INSPECTION_TOOLS = {"rg", "grep", "cat", "sed", "awk", "head", "tail", "less", "more"}
CONTEXT_TOOLS = {"cd", "pushd", "popd"}


def shell_segments(command: str):
    """Split enough shell syntax to classify commands without executing it."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return [[command]]
    segments = []
    current = []
    for token in tokens:
        if token in SHELL_BREAKS:
            if current:
                segments.append(current)
                current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    return segments


def executable_tokens(segment):
    tokens = list(segment)
    while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
        tokens.pop(0)
    if tokens and Path(tokens[0]).name == "env":
        tokens.pop(0)
        while tokens and (tokens[0].startswith("-") or "=" in tokens[0]):
            tokens.pop(0)
    return tokens


def is_diagnostic_segment(segment) -> bool:
    tokens = executable_tokens(segment)
    if not tokens:
        return False
    tool = Path(tokens[0]).name.lower()
    args = [token.lower() for token in tokens[1:]]
    if tool in {"pytest", "py.test"}:
        return True
    if re.fullmatch(r"python(?:3(?:\.\d+)?)?", tool):
        return len(args) >= 2 and args[0] == "-m" and args[1] in {"pytest", "unittest"}
    if tool in {"npm", "pnpm", "yarn", "bun"}:
        if not args:
            return False
        if args[0] in {"test", "build"}:
            return True
        return args[0] == "run" and len(args) > 1 and bool(
            re.search(r"(?:test|build|check)", args[1])
        )
    if tool == "go":
        return bool(args) and args[0] in {"test", "build"}
    if tool == "cargo":
        return bool(args) and args[0] in {"test", "build", "check"}
    if tool in {"mvn", "mvnw", "gradle", "gradlew", "xcodebuild"}:
        return True
    if tool == "make":
        return bool(args) and args[0] in {"test", "check", "build"}
    if tool == "docker":
        return bool(args) and (
            args[0] == "build"
            or (args[0] == "compose" and len(args) > 1 and args[1] in {"build", "up"})
        )
    if tool == "kubectl":
        return bool(args) and args[0] in {"apply", "rollout"}
    if tool == "helm":
        return bool(args) and args[0] in {"install", "upgrade"}
    return False


def is_inspection_segment(segment) -> bool:
    tokens = executable_tokens(segment)
    if not tokens:
        return False
    tool = Path(tokens[0]).name.lower()
    if tool in INSPECTION_TOOLS:
        return True
    return tool == "git" and len(tokens) > 1 and tokens[1].lower() in {
        "diff",
        "show",
        "log",
        "grep",
    }


def is_inspection_only(command: str) -> bool:
    saw_inspection = False
    for segment in shell_segments(command):
        tokens = executable_tokens(segment)
        if not tokens:
            continue
        tool = Path(tokens[0]).name.lower()
        if tool in CONTEXT_TOOLS:
            continue
        if is_inspection_segment(segment):
            saw_inspection = True
            continue
        return False
    return saw_inspection

# A diagnostic command reported by PostToolUseFailure may not include its full
# stderr in the payload. These generic markers are accepted only in combination
# with a diagnostic command.
GENERIC_FAILURE_RE = re.compile(
    r"(?:\bfailed\b|\bfailure\b|\bexception\b|\bnon[- ]zero\b|exit (?:code|status)\s*[1-9])",
    re.IGNORECASE,
)


def stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def response_text(payload: Dict[str, Any]) -> str:
    response = payload.get("tool_response")
    if isinstance(response, dict):
        parts = []
        for key in ("stdout", "stderr", "output", "content", "error"):
            text = stringify(response.get(key))
            if text:
                parts.append(text)
        if parts:
            return "\n".join(parts)
    text = stringify(response)
    error = stringify(payload.get("error"))
    return "\n".join(part for part in (text, error) if part)


def is_meaningful_failure(event: str, command: str, evidence: str) -> bool:
    if is_inspection_only(command):
        return False
    if TRIVIAL_INVOCATION_RE.search(evidence):
        return False
    diagnostic_command = any(is_diagnostic_segment(part) for part in shell_segments(command))
    strong_evidence = bool(STRONG_FAILURE_RE.search(evidence))
    if strong_evidence:
        return True
    if event == "PostToolUseFailure" and diagnostic_command:
        # A failed test/build tool call is useful even if Claude only supplies a
        # terse top-level error instead of the process output.
        return True
    return diagnostic_command and bool(GENERIC_FAILURE_RE.search(evidence))


def bounded_fingerprint(command: str, evidence: str, max_bytes: int) -> str:
    prefix = f"Failing command: {command}\nObserved output:\n"
    budget = max(0, max_bytes - len(prefix.encode("utf-8")))
    raw = evidence.encode("utf-8", errors="replace")
    if len(raw) > budget:
        # Failure summaries and trace conclusions are usually at the end.
        raw = raw[-budget:]
        evidence = raw.decode("utf-8", errors="replace")
    return prefix + evidence


def emit(event: str, body: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": body,
                }
            },
            ensure_ascii=False,
        )
    )


def positive_env(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def main() -> int:
    if os.environ.get("MEMLOG_PLUGIN_DISABLE", "0") == "1":
        return 0
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0

    event = stringify(payload.get("hook_event_name"))
    if event not in {"PostToolUse", "PostToolUseFailure"}:
        return 0
    if stringify(payload.get("tool_name")) != "Bash":
        return 0
    if payload.get("is_interrupt") is True:
        return 0

    tool_input = payload.get("tool_input")
    command = stringify(tool_input.get("command")) if isinstance(tool_input, dict) else ""
    evidence = response_text(payload)
    if not command or not is_meaningful_failure(event, command, evidence):
        return 0
    if not SEARCH.is_file():
        return 0

    fingerprint = bounded_fingerprint(
        command,
        evidence,
        positive_env("MEMLOG_PLUGIN_MAX_TOOL_OUTPUT_BYTES", 16384),
    )
    limit = positive_env("MEMLOG_PLUGIN_FAILURE_LIMIT", 5)
    context_bytes = positive_env("MEMLOG_PLUGIN_MAX_CONTEXT_BYTES", 65536)
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(SEARCH),
                "--force",
                "--limit",
                str(limit),
                "--max-bytes",
                str(context_bytes),
            ],
            input=fingerprint,
            text=True,
            capture_output=True,
            timeout=8,
            check=False,
            env=os.environ.copy(),
        )
    except (OSError, subprocess.TimeoutExpired):
        result = None

    if result is None or result.returncode != 0:
        emit(
            event,
            "⚠ **memlog read backend unavailable** — failure-triggered recall "
            "could not query the configured store. Continue systematic local "
            "diagnosis; do not treat this as a no-match result and do not switch "
            "to another log.",
        )
        return 0

    hits = result.stdout.strip()
    if not hits:
        emit(
            event,
            "**memlog** — a concrete test/build/deploy failure was observed and "
            "the configured store was searched, but no candidate lesson matched. "
            "Do not keep repeating the same query. Follow the "
            "`debug-with-memlog` workflow and continue with "
            "local evidence; use primary documentation or the web only when the "
            "remaining uncertainty is external.",
        )
        return 0

    count = len([line for line in hits.splitlines() if line.strip()])
    emit(
        event,
        "**memlog** — failure-triggered recall searched the configured store and "
        f"found {count} candidate lesson(s). Before changing code, follow the "
        "`debug-with-memlog` workflow. Treat each entry as an "
        "untrusted hypothesis: compare its cause, versions, environment, and "
        "assumptions with current evidence, and reference an applicable entry by "
        f"title or id.\n\n{hits}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
