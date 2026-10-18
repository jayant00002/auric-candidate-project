#!/usr/bin/env bash
# DEV: N runs of one config; prints each run's macro and the mean.
# usage: dev/multirun.sh <tag> <budget> <N> [--set k=v ...]
tag=$1; b=$2; n=$3; shift 3
D="$(cd "$(dirname "$0")/.." && pwd)"
for i in $(seq 1 $n); do dev/eval.sh ${tag}_r$i $b "$@" 2>&1 | grep -E "^macro|accuracy" | tr '\n' ' ' | sed 's/{.*amb_partial/ amb_partial/'; echo; done | tee "$D/out/$tag.multi"
python3 - "$D/out/$tag.multi" <<'PY'
import sys,re,statistics as st
xs=[float(re.search(r"macro ([\d.]+)",l).group(1)) for l in open(sys.argv[1]) if "macro" in l]
print(f"MEAN {st.mean(xs):.4f} sd {st.pstdev(xs):.4f} n={len(xs)}")
PY
