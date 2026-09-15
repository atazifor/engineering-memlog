#!/usr/bin/env bash
set -euo pipefail

DEMO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(CDPATH= cd -- "$DEMO_DIR/.." && pwd)
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/engineering-memlog-demo.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

cp "$DEMO_DIR/fixture/integration.py" "$WORK_DIR/integration.py"
cp "$DEMO_DIR/fixture/integration-fixed.py" "$WORK_DIR/integration-fixed.py"
cp "$DEMO_DIR/fixture/test_integration.py" "$WORK_DIR/test_integration.py"
cp "$DEMO_DIR/entries.jsonl" "$WORK_DIR/entries.jsonl"

frame() {
  printf '\n=== %s ===\n' "$1"
}

frame "1 / 8  Reproduce the concrete failure"
printf '$ python3 -m unittest -q\n'
if test_output=$(cd "$WORK_DIR" && python3 -m unittest -q 2>&1); then
  printf 'Expected the fixture test to fail before the fix.\n' >&2
  exit 1
else
  printf '%s\n' "$test_output" | grep -m 1 "AssertionError"
  printf 'FAIL: a local parser error hides the upstream HTTP 404\n'
fi

frame "2 / 8  Search memory using evidence from the failure"
printf '$ memlog search "integration JSON parse error upstream response"\n'
python3 "$REPO_DIR/memlog" --file "$WORK_DIR/entries.jsonl" \
  search "integration JSON parse error upstream response" --limit 1

frame "3 / 8  Treat recall as a hypothesis"
printf '[skill] Candidate says parsing may be erasing the upstream failure.\n'
printf '[skill] Inspect current code; do not apply memory blindly.\n'
printf '$ grep -n "json.loads\|status" integration.py\n'
grep -n "json.loads\|status" "$WORK_DIR/integration.py"
printf 'MATCH: the body is parsed before status is ever checked\n'

frame "4 / 8  Apply the smallest causal fix"
printf '$ cp integration-fixed.py integration.py\n'
cp "$WORK_DIR/integration-fixed.py" "$WORK_DIR/integration.py"
printf 'Preserved non-2xx status and body before parsing success JSON.\n'

frame "5 / 8  Verify the original failure"
printf '$ python3 -m unittest -q\n'
(cd "$WORK_DIR" && python3 -m unittest -q 2>&1)
printf 'PASS: the error now identifies the upstream 404 and explanation\n'

frame "6 / 8  Save only after verification"
printf '$ memlog add --json <verified-lesson>\n'
python3 "$REPO_DIR/memlog" --file "$WORK_DIR/entries.jsonl" add --json \
  '{"title":"Verified upstream status is preserved before response parsing","problem":"A plain-text HTTP 404 was misreported as a local JSON parsing failure.","cause":"The integration decoded every body before checking response status, so deserialization masked the upstream failure.","fix":"Handled non-2xx status and sanitized body before parsing successful JSON and reran the regression test.","prevention":"Test every integration with a non-JSON error response and preserve upstream status before deserialization.","artifact":"integration response decoder","repo":"sanitized-demo","service":"billing-integration","environment":"local","tags":["python","http","integration","error-handling","regression-test"],"confidence":0.5,"status":"draft","source":"demo"}'

frame "7 / 8  A later session can retrieve the verified lesson"
printf '$ memlog search "verified upstream status response parsing" --limit 1\n'
python3 "$REPO_DIR/memlog" --file "$WORK_DIR/entries.jsonl" \
  search "verified upstream status response parsing" --limit 1

frame "8 / 8  A miss continues the investigation"
printf '$ memlog search "postgres deadlock transaction retry"\n'
python3 "$REPO_DIR/memlog" --file "$WORK_DIR/entries.jsonl" \
  search "postgres deadlock transaction retry"
printf '[skill] No match is not a stop condition: return to local evidence,\n'
printf '[skill] then use primary documentation or the web if uncertainty is external.\n'

printf '\nDemo complete. The disposable store is removed on exit.\n'
