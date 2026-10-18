#!/usr/bin/env bash
# Pre-submission checks, mirroring the auto-fail list:
#  1. the documented entrypoint runs at every budget, through a counting proxy
#  2. every item gets >=1 and <=cap calls, every call carries X-Item-Id
#  3. the output parses as the answer format
#  4. answers change when the model's output changes
# usage: checks/preflight.sh <items.json> [budgets...]
set -euo pipefail
D="$(cd "$(dirname "$0")/.." && pwd)"
ITEMS="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; shift
BUDGETS="${*:-1x 3x 10x}"
OUT="$D/checks/out"; mkdir -p "$OUT"
PORT=8765
UP="$(grep -E '^OPENROUTER_BASE_URL=' "$D/.env" "$D/../.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
UP="${UP:-https://openrouter.ai/api/v1}"
for b in $BUDGETS; do
  rm -f "$OUT/calls.$b.jsonl"
  python3 "$D/checks/count_proxy.py" --port $PORT --upstream "$UP" --log "$OUT/calls.$b.jsonl" &
  PID=$!; sleep 1
  OPENROUTER_BASE_URL="http://127.0.0.1:$PORT" "$D/run" "$ITEMS" --budget "$b" --out "$OUT/answers.$b.json"
  kill $PID
  python3 "$D/checks/budget_report.py" "$OUT/calls.$b.jsonl" "$ITEMS" "$b"
  python3 - "$OUT/answers.$b.json" "$ITEMS" <<'PY'
import json, sys
sys.path.insert(0, __import__("os").path.dirname(sys.argv[2]))
try:
    import score
except ImportError:
    score = None
a = json.load(open(sys.argv[1])); ids = [i["id"] for i in json.load(open(sys.argv[2]))]
missing = [i for i in ids if i not in a]
unparsed = [i for i in ids if score and score.read_sub(a.get(i))[0] is None]
print(f"FORMAT {'OK' if not missing and not unparsed else 'BAD'}: missing {len(missing)}, unparsed {len(unparsed)}")
PY
done
# model dependence: same run with every completion's translations rotated
ROTA_CORRUPT_MODEL=1 "$D/run" "$ITEMS" --budget 1x --out "$OUT/answers.corrupt.json"
python3 - "$OUT/answers.1x.json" "$OUT/answers.corrupt.json" <<'PY'
import json, sys
a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
diff = sum(1 for k in a if json.dumps(a[k], sort_keys=True) != json.dumps(b.get(k), sort_keys=True))
print(f"MODEL DEPENDENCE: {diff}/{len(a)} answers change when the model output is perturbed")
PY
