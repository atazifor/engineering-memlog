#!/usr/bin/env bash
set -euo pipefail

DEMO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/engineering-memlog-baseline.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

cp "$DEMO_DIR/fixture/slugify.py" "$WORK_DIR/slugify.py"
cp "$DEMO_DIR/fixture/slugify-fixed.py" "$WORK_DIR/slugify-fixed.py"
cp "$DEMO_DIR/fixture/test_slugify.py" "$WORK_DIR/test_slugify.py"

printf '=== 1 / 4  Reproduce without memory ===\n'
printf '$ python3 -m unittest -q\n'
if test_output=$(cd "$WORK_DIR" && python3 -m unittest -q 2>&1); then
  printf 'Expected the fixture test to fail before the fix.\n' >&2
  exit 1
else
  printf '%s\n' "$test_output" | grep -m 1 "AssertionError"
fi

printf '\n=== 2 / 4  Re-derive the cause from current code ===\n'
printf '$ grep replace slugify.py\n'
grep "replace" "$WORK_DIR/slugify.py"
printf 'OBSERVATION: the implementation replaces spaces but not underscores.\n'

printf '\n=== 3 / 4  Apply the locally derived fix ===\n'
printf '$ cp slugify-fixed.py slugify.py\n'
cp "$WORK_DIR/slugify-fixed.py" "$WORK_DIR/slugify.py"

printf '\n=== 4 / 4  Verify ===\n'
printf '$ python3 -m unittest -q\n'
(cd "$WORK_DIR" && python3 -m unittest -q 2>&1)
printf 'PASS: the fix works, but no prior lesson shortened the diagnosis.\n'

printf '\nBaseline complete. The disposable workspace is removed on exit.\n'
