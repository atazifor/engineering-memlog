# Discoverability acceptance — Milestone 7

Date: 2026-09-15

## Completion checklist

- [x] The README leads with verified debug-time recall and a concrete
  reproduce → recall → verify → remember flow.
- [x] Claude Code plugin installation appears before optional standalone CLI
  setup and accurately describes the bundled CLI.
- [x] A reproducible no-Memlog baseline and with-Memlog walkthrough use the same
  sanitized fixture and disposable workspaces.
- [x] The with-Memlog walkthrough demonstrates failure reproduction, ranked
  recall, hypothesis checking, verification, write-back, later retrieval, and a
  no-hit continuation path.
- [x] The 64-second GIF is generated from the checked-in transcript, has eight
  ordered frames, and is readable without clipping.
- [x] The 1280×640 social-preview image is ready to upload but has not changed
  repository settings.
- [x] A dated, sourced comparison distinguishes Memlog from Claude auto memory,
  Mem0, Context Memory, and OpenMemory without claiming general superiority.
- [x] The audit records the owner-provided traffic baseline, public repository
  evidence, working diagnosis, proposed metadata, and approval-gated actions.
- [x] CONTRIBUTING, SECURITY, and focused issue forms cover contribution,
  installation, vulnerability, and sanitization expectations.
- [x] Tests check documentation links, README positioning, asset dimensions,
  GIF duration and transcript order, the baseline, the full Memlog demo, and
  the no-hit branch.
- [x] Follow-on acceptance uses 3–5 independent installs with friction triage
  and dated weekly measurements rather than a star target.
- [x] No tag, GitHub release, marketplace submission, repository-setting change,
  public post, or tester outreach happened during this milestone.

## Verification

- `make check`: 81 tests passed, then both disposable demos passed.
- `claude plugin validate .`: passed without warnings.
- `bash -n` on plugin hooks and both demo scripts: passed.
- GitHub issue-form YAML parse: passed.
- `git diff --check`: passed.
- Visual inspection: the GIF's eight frames and social preview are readable and
  unclipped.

An independent validation agent first blocked the milestone on inaccurate Mem0
and OpenMemory descriptions, unpublished-release wording, an omitted traffic
baseline, and a missing no-Memlog transcript. After those corrections, the
agent independently reran the checks above and approved Milestone 7.
