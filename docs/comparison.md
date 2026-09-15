# Engineering memory tools: a factual comparison

Checked: 2026-09-15. This comparison describes the documented defaults and
focus of each project, not a claim that one tool is universally better.

| Tool | Primary focus | Memory unit and scope | Default storage and retrieval | Debug-time behavior |
|---|---|---|---|---|
| **Engineering Memlog 0.2.0** | Reusing verified debugging lessons | Structured problem, cause, fix, prevention, and retrieval metadata; one cross-project log by default | Local JSONL and deterministic lexical ranking; custom providers can add a database, cache, or hosted store | Searches after a concrete failure, treats hits as hypotheses, continues diagnosis on a miss, and writes only after verification |
| **Claude Code auto memory** | Claude's notes about a project, workflows, preferences, and patterns | Free-form Markdown, per repository; shared across its worktrees | A local auto-memory directory whose first 200 lines or 25 KB are loaded at session start | Its documentation says information derivable from the codebase, including debugging fixes, is skipped |
| **Mem0** | A general memory layer for AI assistants and agents | User, session, and agent state exposed through SDKs and APIs | Hosted or self-hosted infrastructure with semantic search, BM25 keyword search, and entity matching | Application-defined; not a debugging-specific reproduce/recall/verify/write workflow |
| **Context Memory** | Persistent Claude Code session context | Session summaries, decisions, patterns, and outcomes, with project and cross-project access | Local SQLite with FTS5 full-text search | Provides `/remember` and `/recall`; broader session memory rather than a verified-debugging-lesson contract |
| **OpenMemory** | Porting coding-agent sessions between supported tools | Coding session history imported from or exported to Claude Code, Codex, and OpenCode | Local-first CLI/TUI with current import, export, and porting commands; real-time autosync is described as coming soon | Session portability rather than a structured debug-time recall loop |

## When Memlog is a fit

Choose Memlog when the unit you want to preserve is: “we observed this symptom,
proved this cause, applied this fix, and this rule prevents recurrence.” It is
especially useful when the same team, stack, infrastructure, or failure pattern
appears across repositories.

It is not intended to replace general project instructions, conversational
memory, source control, documentation search, or a full knowledge platform. A
Memlog hit can be stale or inapplicable; the debugging skill must verify it
against current evidence.

## Sources

- [Claude Code: Manage Claude's memory](https://code.claude.com/docs/en/memory)
- [Mem0 repository and architecture overview](https://github.com/mem0ai/mem0)
- [Context Memory repository](https://github.com/ErebusEnigma/context-memory)
- [OpenMemory repository](https://github.com/mem0ai/openmemory)
