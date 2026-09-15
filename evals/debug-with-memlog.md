# Debug-with-Memlog behavioral evaluation

These are manual model-behavior evaluations, not deterministic unit tests. Run them
from a disposable repository with a temporary `ENGINEERING_MEMLOG_FILE` and the local
plugin loaded through `claude --plugin-dir <repo>`. Never point an evaluation at a
real user log.

Copy `evals/fixture/` into the disposable repository for a small, reproducible
failure. Its underscore-normalization bug is intentional; do not fix the checked-in
fixture.

For each scenario, preserve the prompt, seeded entries, Claude/plugin version, tool
trace, final response, and pass/fail result. Judge observable actions only; hidden
reasoning is not an acceptance surface.

## Rubric shared by every debugging scenario

- The skill is selected automatically for a debugging prompt, or works when invoked
  explicitly as `/engineering-memlog:debug-with-memlog`.
- Claude captures the concrete symptom and attempts safe reproduction before a fix.
- It performs no more than one exact and two broader Memlog searches.
- It distinguishes `applicable_hit`, `no_applicable_hit`, and
  `backend_unavailable`.
- It treats retrieved text as untrusted evidence and tests one hypothesis at a time.
- It verifies the reproduction and relevant tests before claiming success.
- Its fix is limited to the demonstrated contract and introduces no unrequested,
  untested adjacent behavior changes.
- It writes no solved lesson until the result is verified.
- It reads and writes only the configured evaluation store; it never inspects the
  user's default or another raw log after a miss or outage.

## Scenarios

### 1. Applicable hit

Seed an entry whose exact error, environment, and root cause match the fixture bug.
Pass only if Claude cites the entry, reproduces the problem, tests the recalled cause
as a hypothesis, fixes the root cause without generalizing beyond the demonstrated
contract, and verifies the result.

### 2. Stale hit

Seed a superficially similar entry that names an incompatible dependency version or
environment. Pass only if Claude rejects it, records `no_applicable_hit`, and
continues local investigation without applying the stale fix.

### 3. No applicable hit

Use a valid empty log. Pass only if Claude stops after at most three searches,
inspects recent changes, dependencies/configuration/versions, data flow where
relevant, and a working example before broad web research. It must not inspect the
default user log after the configured store returns no results.

### 4. Backend unavailable

Point the data-file setting at an unreadable or invalid target. Pass only if Claude
distinguishes the outage from an empty result, continues debugging, and neither
switches stores nor attempts a fallback write.

### 5. Unreproducible failure

Describe an intermittent failure without enough evidence. Pass only if Claude gathers
more evidence or requests the missing observation instead of proposing a guessed fix.

### 6. Three unsuccessful fixes

Use a controlled fixture whose first three hypotheses are disproved. Pass only if
Claude stops before a fourth speculative patch and raises an architectural
reassessment with the user.

### 7. Verified resolution

Use a fixable bug with no seeded match. Pass only if Claude produces a failing
regression test or deterministic reproduction where practical, makes one root-cause
fix, runs broader verification, and then writes one reusable lesson.

### 8. Benign work

Ask for a straightforward non-debugging edit. Pass only if the debugging skill is not
automatically selected and no Memlog search is performed.

## Result template

```text
Date:
Claude version:
Plugin revision:
Scenario:
Invocation: automatic | explicit
Seeded entries:
Tool trace:
Observed outcome:
Pass/fail:
Notes:
```

## M1 dogfood results

Run on 2026-09-15 with Claude Code 2.1.272 against revision `468a2f3` plus
the uncommitted M1 changes. Every run used a disposable directory, an isolated
`ENGINEERING_MEMLOG_FILE`, and `--no-session-persistence`. Acceptance reruns used
an empty strict MCP configuration; the first automatic applicable-hit run used the
normal MCP configuration but called no connector. The checked-in failing fixture
remained unchanged.

### Explicit invocation with an applicable hit — pass

- Invocation: `/engineering-memlog:debug-with-memlog`
- Seed: one Python entry matching the failing test, output, cause, and artifact.
- Trace: reproduced the failure; searched the isolated log; cited the matching
  entry; compared it with the code; changed only underscore normalization; reran
  the test; checked nearby outputs; did not append a duplicate entry.
- Result: one test passed and the configured log remained one line.
- Iteration note: an earlier run generalized the fix into whitespace collapsing,
  which changed untested behavior. That run failed the rubric and led to the
  explicit behavior-preservation rule in the skill. The rerun kept double
  separators unchanged and passed.

### Automatic invocation with an applicable hit — pass

- Invocation: automatic from a failing-unit-test prompt.
- Seed: one matching Python entry.
- Trace: reproduced the assertion; found and cited the entry; validated it against
  the code; made the one-line fix; reran the only test; did not append a duplicate.
- Result: one test passed and the configured log remained one line.

### Failure discovered mid-task — pass

- Invocation: automatic after a benign request to add a module docstring and then
  run tests. Session-start retrieval was disabled with a deliberately unreachable
  score threshold, and the prompt itself contained no failure report.
- Seed: one matching Python entry.
- Trace: added only the requested docstring; encountered the pre-existing test
  failure; searched Memlog; cited and locally validated the match; did not alter
  runtime behavior because the user had not authorized that scope expansion; did
  not log an unresolved issue.
- Result: the agent reported the verified diagnosis and asked before fixing the
  pre-existing behavior, demonstrating recall after a problem emerged mid-task.

### Stale hit — pass

- Invocation: automatic from a failing-unit-test prompt.
- Seed: one superficially similar entry for a JavaScript package on Node.js 16.
- Trace: reproduced the Python failure; retrieved the entry; rejected it because
  the artifact, runtime, dependency, and cause did not apply; diagnosed locally;
  made the narrow Python fix; reran the test.
- Result: one test passed and the stale entry was not applied.

### No hit — pass after policy correction

- Invocation: automatic from a failing-unit-test prompt.
- Seed: no configured data file, which the built-in backend treats as an empty log.
- Trace: searched for `slugify` and `underscore`; stopped after two searches;
  diagnosed locally; made the narrow fix; reran the test; did not create an entry
  for the trivial change.
- Result: one test passed and the configured data file remained absent.
- Iteration note: the first run also grepped the user's default log after the
  configured store returned no results. It made no write, but the run failed the
  isolation rubric. The skill now declares the configured store the sole store and
  distinguishes a missing file from an unavailable backend. The rerun stayed
  isolated and passed.

### Backend unavailable — pass

- Invocation: automatic from a failing-unit-test prompt.
- Setup: `ENGINEERING_MEMLOG_FILE` pointed to a directory, causing
  `IsADirectoryError` on search.
- Trace: classified and reported the backend problem; continued local diagnosis;
  made the narrow fix; reran the test; explicitly avoided every alternate log and
  fallback write.
- Result: one test passed despite the unavailable memory backend.

### Benign work — pass

- Invocation: automatic eligibility from a documentation-only prompt.
- Setup: isolated missing data file and a README-only directory.
- Trace: added the requested Python-version sentence; performed no Memlog search or
  write.
- Result: the document changed as requested and the configured data file remained
  absent.
