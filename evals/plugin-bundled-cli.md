# Bundled CLI acceptance

Run on 2026-09-15 with Claude Code 2.1.272 against revision `aadaaa5` plus
the uncommitted M3 changes.

## Setup

- Loaded the repository with `claude --plugin-dir`.
- Restricted process `PATH` to system directories, excluding the user's
  standalone `~/.local/bin/memlog` installation.
- Used an isolated `ENGINEERING_MEMLOG_FILE`, strict empty MCP configuration,
  and `--no-session-persistence`.
- Asked Claude to run `command -v memlog` and `memlog --help` without reading or
  writing entries.

## Result — pass

- `command -v memlog` resolved to the plugin's `bin/memlog` entrypoint.
- `memlog --help` exited successfully and exposed `add`, `search`, and `list`.
- Claude correctly reported that the configured temporary log, not the user's
  default log, would be used.
- No Memlog entry was read or written.

Automated coverage also executes the bundled entrypoint from a plugin-style
`PATH`, confirms SessionStart stays quiet when only the bundled CLI is present,
and verifies that an executable wrapper with a missing payload produces a valid
write-half health warning.
