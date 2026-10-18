"""Merge the per-budget ablation results into the tables used in README.md."""
import json, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ablate import ARMS
D = os.path.dirname(os.path.abspath(__file__))

def load(dirs):
    rows = []
    for d in dirs:
        p = os.path.join(D, d, "results.json")
        if os.path.exists(p):
            rows += [r for r in json.load(open(p)) if r["score"]]
    return rows

def table(rows, budgets, arms):
    out = ["| arm | what changes | " + " | ".join(budgets) + " |", "|---|---|" + "---|" * len(budgets)]
    for a in arms:
        cells = []
        for b in budgets:
            xs = [r["score"]["macro_exact_match"] for r in rows if r["arm"] == a and r["budget"] == b]
            if xs:
                cells.append(f"{100*statistics.mean(xs):.1f} (n={len(xs)})")
            else:
                cells.append("=full" if b == "1x" and not ARMS[a][2] else "–")
        out.append(f"| {a} | {ARMS[a][1]} | " + " | ".join(cells) + " |")
    return "\n".join(out)

def confusion(rows, budget):
    cases = ("unique", "ambiguous", "inconsistent")
    tot = {t: {d: 0 for d in cases + ("unparsed",)} for t in cases}
    n = 0
    for r in rows:
        if r["arm"] == "full" and r["budget"] == budget:
            n += 1
            for t in cases:
                for d, v in r["score"]["confusion"][t].items():
                    tot[t][d] += v
    lines = [f"| {budget} (n={n} runs) true \\ declared | unique | ambiguous | inconsistent |", "|---|---|---|---|"]
    for t in cases:
        lines.append(f"| {t} | " + " | ".join(str(tot[t][d]) for d in cases) + " |")
    return "\n".join(lines)

vis = load(["visible_1x", "visible_3x", "visible_3x_b", "visible_10x"])
rw = load(["reworded_1x", "reworded_hi"])
print("VISIBLE\n" + table(vis, ["1x", "3x", "10x"], list(ARMS)))
print("\nREWORDED\n" + table(rw, ["1x", "3x", "10x"], ["full", "no_normalize", "no_lenient"]))
for b in ("1x", "3x", "10x"):
    print("\n" + confusion(vis, b))
