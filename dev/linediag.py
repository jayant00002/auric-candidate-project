"""DEV ONLY: per-statement accuracy of the model's translations against the
template oracle, grouped by statement family."""
import json, sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rota import header, dsl, solver, pipeline
from dev import oracle

def family(line, names):
    s = oracle.strip(line)
    for n in names: s = re.sub(r"\b%s\b" % n, "P", s)
    s = re.sub(r"\d\d:\d\d", "T", s)
    return re.sub(r"\b(intake|calibration|packing)\b", "S", s, flags=re.I)

def main(items_p, trace_p, show=0):
    items = {i["id"]: i for i in json.load(open(items_p))}
    tr = json.load(open(trace_p))
    fam = collections.defaultdict(lambda: [0, 0]); errs = collections.Counter()
    kinds = collections.Counter()
    for iid, info in tr.items():
        it = items[iid]; h = header.parse(it["text"]); dom = dsl.Domain(h)
        lines = info["lines"]
        for l, got in zip(lines, info["translations"]):
            want = dom.parse(oracle.translate(l))
            want = "NONE" if want == "NONE" else str(want)
            f = family(l, h.people); fam[f][1] += 1
            if got == want: fam[f][0] += 1
            else:
                errs[(f, want.split()[0] if want!="NONE" else "NONE", got)] += 0
                kinds["miss" if got == "NONE" else ("halluc" if want == "NONE" else "wrong")] += 1
                if show: print(f"{iid} | {oracle.strip(l)}\n    want {want}\n    got  {got}")
    tot = sum(v[1] for v in fam.values()); ok = sum(v[0] for v in fam.values())
    print(f"statement accuracy {ok}/{tot} = {ok/tot:.3f}", dict(kinds))
    for f, (a, b) in sorted(fam.items(), key=lambda x: x[1][0]/x[1][1]):
        if a < b: print(f"{a:3d}/{b:<3d} {f}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0)
