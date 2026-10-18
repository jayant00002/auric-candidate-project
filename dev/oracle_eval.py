"""DEV ONLY: solve the visible set with the template oracle, to validate the
solver and the semantics of borderline families against the key."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rota import header, dsl, solver
from dev import oracle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import score as S

def run(items, cf):
    out = {}
    for it in items:
        h = header.parse(it["text"]); dom = dsl.Domain(h)
        parsed = []
        for _, l in h.body:
            t = oracle.translate(l, cf)
            c = dom.parse(t)
            if c is None: print("PARSEFAIL", t); continue
            if c != "NONE": parsed.append((l, c))
        st = solver.statements(dom, parsed)
        out[it["id"]], _ = solver.decide(dom, st)
    return out

if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    items = json.load(open(os.path.join(base, "items.json")))
    key = json.load(open(os.path.join(base, "visible_key.json")))
    for cf in sys.argv[1:] or ["NONE", "NOT AT", "AT"]:
        r = S.score(key, run(items, cf), items)
        print(cf, r["macro_exact_match"], r["per_case_rate"], r["confusion"])
