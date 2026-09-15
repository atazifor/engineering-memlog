#!/usr/bin/env bash
set -euo pipefail

DEMO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(CDPATH= cd -- "$DEMO_DIR/.." && pwd)
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/engineering-memlog-demo.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

cp "$DEMO_DIR/fixture/database.py" "$WORK_DIR/database.py"
cp "$DEMO_DIR/fixture/database-fixed.py" "$WORK_DIR/database-fixed.py"
cp "$DEMO_DIR/fixture/test_database.py" "$WORK_DIR/test_database.py"
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
  printf 'FAIL: deleting a project leaves an orphan task\n'
fi

frame "2 / 8  Search memory using evidence from the failure"
printf '$ memlog search "sqlite delete cascade orphan foreign_keys"\n'
python3 "$REPO_DIR/memlog" --file "$WORK_DIR/entries.jsonl" \
  search "sqlite delete cascade orphan foreign_keys" --limit 1

frame "3 / 8  Treat recall as a hypothesis"
printf '[skill] Candidate says foreign-key enforcement is connection-local.\n'
printf '[skill] Inspect current code; do not apply memory blindly.\n'
printf '$ python3 -c "from database import connect; ... PRAGMA foreign_keys"\n'
(cd "$WORK_DIR" && python3 -c 'from database import connect; db = connect("probe.db"); print("PRAGMA foreign_keys =", db.execute("PRAGMA foreign_keys").fetchone()[0]); db.close()')
printf 'MATCH: an ordinary application connection has enforcement disabled\n'

frame "4 / 8  Apply the smallest causal fix"
printf '$ cp database-fixed.py database.py\n'
cp "$WORK_DIR/database-fixed.py" "$WORK_DIR/database.py"
printf 'Moved PRAGMA foreign_keys = ON into the shared connection factory.\n'

frame "5 / 8  Verify the original failure"
printf '$ python3 -m unittest -q\n'
(cd "$WORK_DIR" && python3 -m unittest -q 2>&1)
printf 'PASS: deleting a project now cascades to its tasks\n'

frame "6 / 8  Save only after verification"
printf '$ memlog add --json <verified-lesson>\n'
python3 "$REPO_DIR/memlog" --file "$WORK_DIR/entries.jsonl" add --json \
  '{"title":"Verified SQLite foreign-key enforcement on runtime connections","problem":"Deleting a project left an orphan task even though the schema declared ON DELETE CASCADE.","cause":"Only the migration connection enabled PRAGMA foreign_keys; separately opened runtime connections defaulted to disabled enforcement.","fix":"Enabled PRAGMA foreign_keys in the shared connection factory and reran the cascade regression test.","prevention":"Initialize foreign-key enforcement on every SQLite connection and test cascade behavior through the runtime connection path.","artifact":"database.py connection factory","repo":"sanitized-demo","service":"task-api","environment":"local","tags":["python","sqlite","foreign-keys","cascade","regression-test"],"confidence":0.5,"status":"draft","source":"demo"}'

frame "7 / 8  A later session can retrieve the verified lesson"
printf '$ memlog search "verified sqlite foreign key runtime connection" --limit 1\n'
python3 "$REPO_DIR/memlog" --file "$WORK_DIR/entries.jsonl" \
  search "verified sqlite foreign key runtime connection" --limit 1

frame "8 / 8  A miss continues the investigation"
printf '$ memlog search "postgres deadlock transaction retry"\n'
python3 "$REPO_DIR/memlog" --file "$WORK_DIR/entries.jsonl" \
  search "postgres deadlock transaction retry"
printf '[skill] No match is not a stop condition: return to local evidence,\n'
printf '[skill] then use primary documentation or the web if uncertainty is external.\n'

printf '\nDemo complete. The disposable store is removed on exit.\n'
