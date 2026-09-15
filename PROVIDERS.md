# Storage providers

Memlog uses its private append-only JSONL file by default. A provider can route
the same CLI, ranking, validation, skill, and Claude Code hooks to another
datastore without changing those layers.

Set `ENGINEERING_MEMLOG_PROVIDER_COMMAND` to an absolute executable path plus any
arguments:

```sh
export ENGINEERING_MEMLOG_PROVIDER_COMMAND="$PWD/examples/providers/jsonl-provider"
export MEMLOG_PROVIDER_FILE="$PWD/tmp/provider-entries.jsonl"
memlog search "frozen lockfile" --json
```

Memlog parses the value as arguments and executes it directly; it does not use a
shell or resolve the executable through `PATH`. The first argument must be an
absolute path. The provider inherits the current environment so it can receive
its own database URL, credentials, namespace, or cache settings. Do not put
secrets in the command string itself.

## Protocol version 1

One provider process handles one request. Memlog writes exactly one JSON object
followed by a newline to standard input. The request always contains:

```json
{"protocol_version": 1, "operation": "scan", "data_file": "/configured/path/entries.jsonl"}
```

`data_file` preserves the caller's `--file` or `ENGINEERING_MEMLOG_FILE` value as
an optional namespace hint. A provider may ignore it and use its own settings.

The two required operations are:

- `scan`: emit zero or more complete Memlog entries as JSONL on standard output,
  then exit 0. Memlog owns filtering and ranking so all providers behave alike.
- `append`: the request also contains `entry`, a complete entry whose ID,
  timestamp, schema version, and fields Memlog has already generated and
  validated. Persist it durably and exit 0. Standard output may be empty or the
  single acknowledgement `{"ok": true}`.

A provider owns atomicity and concurrency for its persistence layer. Treat the
entry ID as an idempotency key where the datastore permits it. If `append` times
out, the write may have completed even though Memlog could not observe the
acknowledgement; inspect the configured provider before retrying, and never retry
against the default file.

Diagnostics belong on standard error; Memlog forwards them on successful direct
CLI operations while hooks suppress provider diagnostics from user-facing JSON.
During normal reads, a nonzero exit,
malformed or schema-invalid scan output, invalid append acknowledgement, missing
executable, or timeout is a backend error. `memlog validate` is the exception: it
reports malformed and schema-invalid scan records as validation failures so an
operator can diagnose the store. Memlog does **not** fall back to the default
file. This prevents reads and writes from silently splitting across two stores.

The default timeout is 10 seconds. Override it with a positive number in
`ENGINEERING_MEMLOG_PROVIDER_TIMEOUT_SECONDS`. Provider stdout and stderr are
captured outside process memory and rejected when their combined size exceeds 5
MiB; set a different positive byte count with
`ENGINEERING_MEMLOG_PROVIDER_MAX_RESPONSE_BYTES`.

## Design boundaries

The provider owns persistence, any indexes used to produce its scan, and optional caching.
Memlog owns entry IDs, timestamps, schema validation, duplicate reporting,
ranking, output formatting, and agent behavior. Protocol v1 intentionally uses
`scan` rather than provider-specific search so a filesystem, SQLite, hosted
database, or cached API adapter returns identical ranked results.

For a growing remote corpus, a provider can maintain a cached or materialized
entry stream to make `scan` inexpensive. A later protocol version can add native
candidate-query hints without changing version 1; version 1 deliberately favors
portable, identical results over database-specific search behavior.

See [`examples/providers/jsonl-provider`](examples/providers/jsonl-provider) for
a complete stdlib-only adapter.
