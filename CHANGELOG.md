# Changelog

All notable changes to engineering-memlog are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] — 2026-09-15

### Added

- A model-invocable `debug-with-memlog` skill that searches after reproducing a
  concrete failure, evaluates recalled lessons as hypotheses, continues local
  diagnosis after a miss, and writes back only verified reusable lessons.
- Deterministic field-aware retrieval with query coverage, exact-phrase boosts,
  bounded identifier-prefix matching, confidence and recency tie-breakers, and
  curated relevance evaluations.
- A plugin-bundled `memlog` executable, so Claude Code users no longer need a
  separate repository clone or standalone CLI installation.
- Collision-resistant entry IDs, schema version 1, strict field validation,
  atomic append behavior for the built-in JSONL store, private new-file
  permissions, and the read-only `memlog validate` command.
- A versioned `scan`/`append` provider protocol for custom datastores and caches,
  with a runnable JSONL adapter example and explicit no-fallback behavior.
- Regression coverage for the CLI, hooks, retrieval ranking, skill contract,
  schema integrity, provider failures, and clean plugin installation.

### Changed

- Session-start and prompt-time recall are bounded by entry count and byte size.
- Backend outages are distinguished from successful empty searches and tell the
  agent to continue local diagnosis without switching stores.
- The mandate marker is now `v4` so existing installations load the current
  provider-aware debugging policy once.

### Security

- Provider executables must use absolute paths and run without a shell.
- Provider execution has configurable time and response-size limits.
- Documentation now distinguishes local built-in storage, Claude conversation
  context, and custom-provider data handling.

## [0.1.0] — 2026-05-27

### Added

- The first Claude Code plugin release with project-aware SessionStart recall,
  symptom-triggered UserPromptSubmit recall, and `/recall`.
- The original append-only JSONL CLI and agent mandate.

[Unreleased]: https://github.com/atazifor/engineering-memlog/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/atazifor/engineering-memlog/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/atazifor/engineering-memlog/releases/tag/v0.1.0
