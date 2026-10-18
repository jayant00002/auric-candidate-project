"""Ablation arm only: the model answers the item itself, no solver.

It gets the same header facts and the same cleaned statements as the full
system, plus the answer format, and its JSON is read as the answer.  With more
budget, the most common parseable answer wins.
"""
import collections
import json
import re

from . import prompt

SYSTEM = """You solve shift-rota puzzles. Every statement in the notes is true and firm, however hedged, except statements about the past, unsettled questions, hypotheticals, and things unrelated to blocks or stations.

Each person works exactly one block, one person per block. Each station is held by exactly one of the people listed as on a station.

Decide which case the notes are:
- unique: exactly one assignment satisfies every statement
- ambiguous: between two and four assignments do; give all of them
- inconsistent: none does; cite the smallest set of statements (copied word for word) that cannot all hold together

Answer with JSON only, one of:
{"case": "unique", "assignment": {"<name>": {"block": "<time>", "station": "<station>"}, "<name not on a station>": {"block": "<time>"}}}
{"case": "ambiguous", "assignments": [ {...}, {...} ]}
{"case": "inconsistent", "conflicts": ["<statement>", "..."]}"""


def ask(sess, hdr, sent, lines):
    user = prompt.user(hdr, sent)
    answers = []
    while sess.left > 0:
        out = sess.ask(SYSTEM, user)
        a = parse(out, sent, lines)
        if a is not None:
            answers.append(a)
    if not answers:
        return {"case": "inconsistent", "conflicts": []}
    keyed = collections.Counter(json.dumps(a, sort_keys=True) for a in answers)
    return json.loads(keyed.most_common(1)[0][0])


def parse(text, sent, lines):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        a = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(a, dict) or a.get("case") not in ("unique", "ambiguous", "inconsistent"):
        return None
    if a["case"] == "inconsistent":
        # map cited (cleaned) statements back to the original lines
        cs = []
        for c in a.get("conflicts") or []:
            c = str(c)
            hit = next((lines[i] for i, s in enumerate(sent) if c.strip() and
                        (c.strip(" .") in s or s.strip(" .") in c)), c)
            cs.append(hit)
        a["conflicts"] = cs
    return a
