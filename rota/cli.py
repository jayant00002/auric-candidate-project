"""./run <items.json> --budget <1x|3x|10x> --out <answers.json>"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor

from . import pipeline
from .model import Model, ItemSession

BUDGETS = {"1x": 1, "3x": 3, "10x": 10}


def fallback(item):
    """Used only if the solver itself raises: still a parseable answer."""
    return {"case": "inconsistent", "conflicts": []}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("items")
    ap.add_argument("--budget", required=True, choices=sorted(BUDGETS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--trace", help="write per-item diagnostics here")
    ap.add_argument("--set", action="append", default=[],
                    help="component override, e.g. --set vote=false (ablations)")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args(argv)

    cfg = {}
    for kv in a.set:
        k, v = kv.split("=", 1)
        cfg[k] = json.loads(v.lower()) if v.lower() in ("true", "false") or v.isdigit() else v
    items = json.load(open(a.items))
    model = Model()
    cap = BUDGETS[a.budget]

    def one(item):
        sess = ItemSession(model, item["id"], cap)
        try:
            ans, info = pipeline.answer(item, sess, cfg)
        except Exception as ex:
            if sess.used == 0:          # never leave an item with no call
                try:
                    sess.ask("Reply OK.", "OK", max_tokens=2)
                except Exception:
                    pass
            ans, info = fallback(item), {"error": repr(ex)}
        info["calls"] = sess.used
        info["log"] = sess.log
        return item["id"], ans, info

    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(one, items))
    json.dump({i: ans for i, ans, _ in res}, open(a.out, "w"), indent=1)
    if a.trace:
        json.dump({i: info for i, _, info in res}, open(a.trace, "w"), indent=1)
    calls = [info["calls"] for _, _, info in res]
    errs = sum(1 for _, _, info in res for e in info["log"] if "error" in e)
    print(f"{len(res)} items, calls/item min {min(calls)} max {max(calls)} "
          f"mean {sum(calls)/len(calls):.2f}, request errors {errs}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
