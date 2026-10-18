#!/usr/bin/env python3
"""Re-run the ablation table.

    python3 ablate.py <items.json> <key.json> [--runs N] [--budgets 1x,3x,10x]
                      [--arms full,no_echo,...] [--parallel P] [--out DIR]

Every arm is the full system with ONE component switched off (or swapped for
its simpler alternative), run through the same ./run entrypoint with
`--set key=value` overrides, and scored with the provided score.py.  Arms that
only act when there is more than one sample (vote, repair) are skipped at 1x,
where they are identical to the full system by construction.
"""
import argparse
import json
import re
import os
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))

# name -> (overrides, description, applies at 1x?)
ARMS = {
    "full":        ([], "full system", True),
    "no_ce":       (["repr=dsl"], "positional DSL instead of controlled English", True),
    "no_echo":     (["repr=ce_terse"], "controlled English without echoing the statement", True),
    "no_normalize": (["normalize=false"], "hedges / restatement lead-ins sent to the model", True),
    "no_realign":  (["realign=false"], "trust the model's line numbers, ignore the echo", True),
    "no_ground":   (["ground=false"], "accept translations naming things the statement does not", True),
    "no_lenient":  (["lenient=false"], "read only the listed output forms (no or/and, no 'one of')", True),
    "no_prefilter": (["prefilter=false"], "send statements that name no person/block/station", True),
    "no_dedupe":   (["dedupe=false"], "send restated statements twice", True),
    "no_min_core": (["min_core=0"], "cite the smallest conflict even if implausibly small", True),
    "no_solver":   (["mode=direct"], "model answers the item directly; no symbolic solver", True),
    "plural_vote": (["vote=plural"], "plain plurality vote instead of asymmetric", False),
    "no_vote":     (["vote=none"], "use only the last sample", False),
    "no_repair":   (["repair=false"], "no re-vote when the outcome is impossible", False),
}


def find_score(key_path):
    for d in (os.path.dirname(os.path.abspath(key_path)), HERE, os.path.dirname(HERE)):
        if os.path.exists(os.path.join(d, "score.py")):
            sys.path.insert(0, d)
            import score
            return score
    raise SystemExit("score.py not found next to the key")


def one(items, key, score, arm, budget, run, outdir):
    sets, _, _ = ARMS[arm]
    out = os.path.join(outdir, f"{arm}.{budget}.r{run}.json")
    cmd = [os.path.join(HERE, "run"), items, "--budget", budget, "--out", out]
    for s in sets:
        cmd += ["--set", s]
    # A run with failed requests measures the endpoint, not the system: it is
    # repeated (up to twice more) so the table only holds clean runs.
    for attempt in range(3):
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            return arm, budget, run, None, p.stderr[-500:]
        m = re.search(r"request errors (\d+)", p.stderr)
        if not m or m.group(1) == "0":
            break
    r = score.score(json.load(open(key)), json.load(open(out)), json.load(open(items)))
    r.pop("per_item")
    return arm, budget, run, r, p.stderr.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("items")
    ap.add_argument("key")
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--budgets", default="1x,3x,10x")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--out", default=os.path.join(HERE, "ablation"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    score = find_score(a.key)
    jobs = [(arm, b, r) for b in a.budgets.split(",") for arm in a.arms.split(",")
            for r in range(1, a.runs + 1) if b != "1x" or ARMS[arm][2]]
    res = []
    with ThreadPoolExecutor(a.parallel) as ex:
        futs = [ex.submit(one, a.items, a.key, score, arm, b, r, a.out) for arm, b, r in jobs]
        for f in futs:
            arm, b, r, sc, log = f.result()
            res.append({"arm": arm, "budget": b, "run": r, "score": sc, "log": log})
            m = sc["macro_exact_match"] if sc else "FAILED"
            print(f"{arm:13s} {b:4s} run {r}: {m}  {log.splitlines()[-1] if log else ''}", flush=True)
    json.dump(res, open(os.path.join(a.out, "results.json"), "w"), indent=1)

    budgets = a.budgets.split(",")
    lines = ["| arm | what changes | " + " | ".join(budgets) + " |",
             "|---|---|" + "---|" * len(budgets)]
    for arm in a.arms.split(","):
        cells = []
        for b in budgets:
            xs = [x["score"]["macro_exact_match"] for x in res
                  if x["arm"] == arm and x["budget"] == b and x["score"]]
            cells.append(f"{100*statistics.mean(xs):.1f} (n={len(xs)})" if xs else "=full")
        lines.append(f"| {arm} | {ARMS[arm][1]} | " + " | ".join(cells) + " |")
    table = "\n".join(lines)
    open(os.path.join(a.out, "table.md"), "w").write(table + "\n")
    print(table)


if __name__ == "__main__":
    main()
