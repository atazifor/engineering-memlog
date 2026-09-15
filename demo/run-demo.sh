#!/usr/bin/env bash
set -euo pipefail

DEMO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(CDPATH= cd -- "$DEMO_DIR/.." && pwd)
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/engineering-memlog-demo.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

cp "$DEMO_DIR/fixture/slugify.py" "$WORK_DIR/slugify.py"
cp "$DEMO_DIR/fixture/slugify-fixed.py" "$WORK_DIR/slugify-fixed.py"
cp "$DEMO_DIR/fixture/test_slugify.py" "$WORK_DIR/test_slugify.py"
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
  printf 'FAIL: underscores remain in the generated slug\n'
fi

frame "2 / 8  Search memory using evidence from the failure"
printf '$ memlog search "slugify underscore separator"\n'
python3 "$REPO_DIR/memlog" --file "$WORK_DIR/entries.jsonl" \
  search "slugify underscore separator" --limit 1

frame "3 / 8  Treat recall as a hypothesis"
printf '[skill] Candidate says spaces-only replacement misses underscores.\n'
printf '[skill] Inspect current code; do not apply memory blindly.\n'
printf '$ grep replace slugify.py\n'
grep "replace" "$WORK_DIR/slugify.py"
printf 'MATCH: current implementation has the remembered failure mode\n'

frame "4 / 8  Apply the smallest causal fix"
printf '$ cp slugify-fixed.py slugify.py\n'
cp "$WORK_DIR/slugify-fixed.py" "$WORK_DIR/slugify.py"
printf 'Changed the separator rule from a literal space to [whitespace_or_underscore]+.\n'

frame "5 / 8  Verify the original failure"
printf '$ python3 -m unittest -q\n'
(cd "$WORK_DIR" && python3 -m unittest -q 2>&1)
printf 'PASS: mixed spaces and underscores normalize to one hyphen\n'

frame "6 / 8  Save only after verification"
printf '$ memlog add --json <verified-lesson>\n'
python3 "$REPO_DIR/memlog" --file "$WORK_DIR/entries.jsonl" add --json \
  '{"title":"Verified slug separator normalization in the demo","problem":"The slugify regression left underscores in mixed-separator input.","cause":"The implementation handled literal spaces instead of the full accepted separator class.","fix":"Collapsed whitespace and underscore runs to a single hyphen and reran the regression test.","prevention":"Keep a mixed-separator regression test whenever slug rules accept both spaces and underscores.","artifact":"slugify.py","repo":"sanitized-demo","service":"routing","environment":"local","tags":["python","slugify","normalization","regression-test"],"confidence":0.5,"status":"draft","source":"demo"}'

frame "7 / 8  A later session can retrieve the verified lesson"
printf '$ memlog search "verified slug separator regression" --limit 1\n'
python3 "$REPO_DIR/memlog" --file "$WORK_DIR/entries.jsonl" \
  search "verified slug separator regression" --limit 1

frame "8 / 8  A miss continues the investigation"
printf '$ memlog search "postgres deadlock transaction retry"\n'
python3 "$REPO_DIR/memlog" --file "$WORK_DIR/entries.jsonl" \
  search "postgres deadlock transaction retry"
printf '[skill] No match is not a stop condition: return to local evidence,\n'
printf '[skill] then use primary documentation or the web if uncertainty is external.\n'

printf '\nDemo complete. The disposable store is removed on exit.\n'
