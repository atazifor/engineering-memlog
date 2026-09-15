# Contributing

Thanks for helping make Engineering Memlog more dependable or easier to adopt.

## Before opening a change

- Use a focused issue template for a bug, installation problem, or feature
  request when discussion would help.
- Never include secrets or an unsanitized private memory entry in an issue,
  fixture, screenshot, or test.
- Keep the core CLI compatible with Python 3.8+ and the standard library.
- Preserve the zero-configuration JSONL backend. Optional providers may add
  storage capabilities without changing the skill's debugging contract.

## Local checks

```bash
make test
./demo/run-demo.sh
```

If Claude Code's plugin developer tools are available, also run:

```text
/plugin validate .
```

Changes to shell hooks should pass `bash -n`. Documentation changes should keep
all repository-relative links valid; the unit suite checks them.

## Pull requests

Explain the failure or limitation being addressed, why the chosen change solves
it, and how you verified it. Provider contributions should document their data
flow, failure behavior, timeout expectations, and whether they access a network.
New retrieval behavior should include ranking cases or regression tests.

For a new coding-agent integration, follow the gates in
[`docs/agent-support.md`](docs/agent-support.md). Reuse the canonical
`debug-with-memlog` skill and shared retrieval scripts; keep event-schema and
packaging differences in a small host adapter. Do not advertise an agent as
supported until its installed-agent evaluation is recorded.

Semantic retrieval work should begin with the evaluation and interface sequence
in the [retrieval proposal](docs/retrieval-roadmap.md). The project is ready for
design and evaluation contributions, but not an unreviewed vector-database or
mandatory embedding dependency.

Keep commits small enough to review and avoid unrelated formatting changes.
