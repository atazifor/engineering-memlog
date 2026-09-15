# Release-readiness acceptance — Milestone 6

Date: 2026-09-15
Release candidate: 0.2.0

## Completion checklist

- [x] `plugin.json` has one SemVer source of truth; the marketplace entry does
  not duplicate it.
- [x] `memlog --version` reports the same release version.
- [x] The changelog records 0.2.0 and the existing 0.1.0 release history.
- [x] Release notes explain the debugging loop, ranked recall, bundled CLI,
  integrity guarantees, provider option, no-hit behavior, and upgrade path.
- [x] Existing JSONL data remains readable without migration.
- [x] A fresh copied plugin cache works without a repository clone, `make
  install`, or a PATH-installed standalone CLI.
- [x] The clean-install E2E reproduces a failure, recalls the seeded lesson,
  applies and verifies the fix, appends through the bundled CLI, and retrieves
  the new lesson from a later hook process.
- [x] The full Python 3.8+/3.13 regression suite is wired into CI.
- [x] Plugin validation, shell syntax checks, and diff checks pass.
- [x] No release tag, GitHub release, marketplace submission, repository-setting
  change, or public post occurs without separate approval.

## Verification command

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`

The E2E runs entirely in a disposable directory and never reads or writes the
user's real Memlog store.

Result: 74 tests passed on Python 3.13. Plugin validation completed without
warnings; shell syntax and diff checks passed. Python 3.8 and 3.13 remain the CI
matrix for pushes and pull requests.
