#!/usr/bin/env bash
set -euo pipefail

DEMO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/engineering-memlog-baseline.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

cp "$DEMO_DIR/fixture/integration.py" "$WORK_DIR/integration.py"
cp "$DEMO_DIR/fixture/integration-fixed.py" "$WORK_DIR/integration-fixed.py"
cp "$DEMO_DIR/fixture/test_integration.py" "$WORK_DIR/test_integration.py"

printf '=== 1 / 4  Reproduce without memory ===\n'
printf '$ python3 -m unittest -q\n'
if test_output=$(cd "$WORK_DIR" && python3 -m unittest -q 2>&1); then
  printf 'Expected the fixture test to fail before the fix.\n' >&2
  exit 1
else
  printf '%s\n' "$test_output" | grep -m 1 "AssertionError"
fi

printf '\n=== 2 / 4  Re-derive the cause from current code ===\n'
printf '$ grep -n "json.loads\|status" integration.py\n'
grep -n "json.loads\|status" "$WORK_DIR/integration.py"
printf '$ python3 -c "decode_download(404, plain_text_body)"\n'
if probe_output=$(cd "$WORK_DIR" && python3 -c 'from integration import decode_download; decode_download(404, "endpoint is disabled")' 2>&1); then
  printf 'Expected the integration probe to fail.\n' >&2
  exit 1
else
  printf '%s\n' "$probe_output" | grep -m 1 "IntegrationError"
fi
printf 'OBSERVATION: our parser names itself instead of the upstream response.\n'

printf '\n=== 3 / 4  Apply the locally derived fix ===\n'
printf '$ cp integration-fixed.py integration.py\n'
cp "$WORK_DIR/integration-fixed.py" "$WORK_DIR/integration.py"

printf '\n=== 4 / 4  Verify ===\n'
printf '$ python3 -m unittest -q\n'
(cd "$WORK_DIR" && python3 -m unittest -q 2>&1)
printf 'PASS: the fix works, but no prior lesson shortened the diagnosis.\n'

printf '\nBaseline complete. The disposable workspace is removed on exit.\n'
