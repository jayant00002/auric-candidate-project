#!/usr/bin/env bash
# DEV: run, score and diagnose.  usage: dev/eval.sh <tag> <budget> [--set k=v ...]
set -e
tag=$1; b=$2; shift 2
D="$(cd "$(dirname "$0")/.." && pwd)"; P="$D/.."
"$D/run" "$P/items.json" --budget "$b" --out "$D/out/$tag.json" --trace "$D/out/$tag.trace.json" "$@"
python3 - "$P/visible_key.json" "$D/out/$tag.json" "$P/items.json" <<'PY'
import json,sys; sys.path.insert(0, sys.argv[1].rsplit('/',1)[0]); import score as S
r=S.score(json.load(open(sys.argv[1])),json.load(open(sys.argv[2])),json.load(open(sys.argv[3])))
print("macro",r["macro_exact_match"],r["per_case_rate"],"amb_partial",r["ambiguous_partial"],"inc_label_only",r["inconsistent_label_only"])
for t,row in r["confusion"].items(): print("  true",t,row)
PY
python3 "$D/dev/linediag.py" "$P/items.json" "$D/out/$tag.trace.json" | head -1
