#!/usr/bin/env python3
"""Per-item call counts from a count_proxy log, checked against a budget.
usage: budget_report.py <calls.jsonl> <items.json> <1x|3x|10x>"""
import collections, json, sys
log, items, b = sys.argv[1], sys.argv[2], sys.argv[3]
lo, hi = {"1x": (1, 1), "3x": (1, 3), "10x": (1, 10)}[b]
rows = [json.loads(l) for l in open(log)]
cnt = collections.Counter(r["item"] for r in rows)
ids = [i["id"] for i in json.load(open(items))]
bad = [i for i in ids if not lo <= cnt.get(i, 0) <= hi]
print(f"{b}: {len(rows)} requests, {sum(1 for r in rows if not r['item'])} without X-Item-Id, "
      f"per-item min {min(cnt.get(i,0) for i in ids)} max {max(cnt.get(i,0) for i in ids)}, "
      f"settings {sorted(set(json.dumps({k:v for k,v in r.items() if k not in ('item','path')}) for r in rows))}")
print("BUDGET OK" if not bad and all(r["item"] for r in rows) else f"BUDGET VIOLATION: {bad[:10]}")
sys.exit(1 if bad else 0)
