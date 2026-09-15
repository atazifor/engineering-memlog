# Codex installed-skill evaluation

Run on 2026-09-15 with Codex CLI 0.153.4 and Python 3.14.5 against the
checked-in `evals/fixture` project. This is a sanitized capability evaluation,
not a claim about model performance in general.

## Package setup

1. Copy the repository to a disposable directory.
2. Register that directory with `codex plugin marketplace add <path> --json`.
3. Install `engineering-memlog@<disposable-marketplace> --json`.
4. Verify that the installed package contains the canonical skill and that its
   bundled `skills/debug-with-memlog/scripts/memlog --version` reports
   `memlog 0.2.0`.

All four steps passed using the repository-root package selected by
`.agents/plugins/marketplace.json` and `.codex-plugin/plugin.json`.

## Scenario

The fixture's `slugify()` normalizes spaces but not underscores. A separate
temporary Memlog file contained one applicable, sanitized lesson with ID
`mem-codex-eval-hit`. The authenticated agent was run in a read-only sandbox and
asked to diagnose the failing test, use an installed debugging skill, report any
applicable lesson ID, and make no changes.

Pass criteria:

- load the installed `debug-with-memlog` skill;
- reproduce the test failure before searching;
- search through `memlog` rather than opening the JSONL file;
- cite `mem-codex-eval-hit` only after checking it against current evidence;
- diagnose missing underscore normalization; and
- leave the fixture and Memlog file unchanged.

## Result: passed

The event stream showed the skill loaded from the installed disposable package.
Codex reproduced the assertion failure, searched for
`slugify underscores user_profile-name`, found `mem-codex-eval-hit`, and confirmed
the lesson with the implementation plus space-only, underscore-only, and mixed
inputs. Its final response classified the lesson as an `applicable_hit` and
reported that no fix was attempted.

SHA-256 values before and after the run were identical:

```text
fbdf78e280e55aa96d611f55192e8c9fe7d41f23c726b1169d95a2732f2cc071  entries.jsonl
7001bd3ad5936f62ce90b471bb7b58ae55906d735288fe05b2c2b5c8808efd96  slugify.py
e4841f5bf339b67dee5f034f1de18a4d4410f5ff00daa37143f3c05830c63931  test_slugify.py
```

This passes the Codex package, skill discovery, read workflow, applicability,
and no-write gates. It does not prove automatic hook activation; that is tracked
separately in [codex-hooks.md](codex-hooks.md).
