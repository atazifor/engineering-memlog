# Schema and integrity acceptance

Run on 2026-09-15 against revision `95bebf5` plus the uncommitted M4 changes.
All writes used temporary test directories; the user's Memlog was not read or
modified.

## Automated checks

- Twelve concurrent `memlog add` processes produced twelve complete JSON lines
  with twelve distinct UUID-backed IDs.
- A newly created log had mode `0600`; appending to an existing `0640` shared log
  preserved its configured mode.
- Invalid text fields, empty tags, boolean/out-of-range confidence, caller-supplied
  IDs/timestamps, and unsupported schema versions were rejected.
- `memlog validate --json` detected malformed JSON, incomplete records, duplicate
  IDs, and unsupported schema versions without changing the input file.
- Directory paths and other backend errors returned a concise
  `backend unavailable` error without a Python traceback.

## Compatibility — pass

The twelve checked-in example records predate `schema_version`. The read-only
validator accepted all twelve as legacy schema version 1 with zero errors.

## New-record smoke test — pass

One record written to a disposable log contained `schema_version: 1`, an ID in
the form `mem-<32 lowercase hex characters>`, and an RFC3339 UTC timestamp. The
file mode was `0600`, and a subsequent validation reported one valid and zero
invalid records.
