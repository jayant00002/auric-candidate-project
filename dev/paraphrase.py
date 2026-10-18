"""DEV ONLY: build a pseudo-held-out set by rewording the visible one.

The held-out set keeps the item kinds but draws its constraint wording from a
pool disjoint from items.json.  To estimate what that costs, every constraint
statement (and every borderline distractor) is rewritten from templates I
wrote that occur nowhere in items.json or in the extraction prompt, with new
hedges and new restatement lead-ins.  The semantics are taken from the
oracle, so the key carries over unchanged except that cited statements are
renamed to their new wording.

    python3 dev/paraphrase.py ../items.json ../visible_key.json out/para_items.json out/para_key.json [seed]
"""
import json
import random
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev import oracle  # noqa: E402

HEDGES = ["I think ", "If I'm not mistaken, ", "To the best of my knowledge, ",
          "Off the top of my head, ", "Pretty sure ", "As I understand it, ", ""]
LEADS = ["To repeat: ", "Flagging again: ", "Said this already, but: "]


# A second, independent pool (B): used only as the acceptance test for
# changes made after pool A had been looked at.
HEDGES_B = ["Honestly, I'd say ", "From where I sit, ", "Correct me if I'm wrong, but ",
            "Seems to me ", "I'd put money on it: ", "In my view, ", ""]
LEADS_B = ["Once more for the record: ", "Repeating myself: ", "Again: "]
T_B = {
    "AT": ["{a} has drawn {b}.", "The rota shows {a} at {b}.", "{a} covers the {b} slot."],
    "NOT AT": ["{a} is off at {b}.", "{b} is out for {a}.", "{a} asked off {b} and got it.",
               "No {b} for {a}."],
    "ON": ["{a} mans {b}.", "{b} is in {a}'s hands.", "{a} is staffing {b}."],
    "NOT ON": ["{a} isn't staffing {b}.", "{b} has been given to someone besides {a}.",
               "Keep {a} away from {b}."],
    "BEFORE": ["{A} gets going ahead of {B}.", "{B} comes in after {A} has started.",
               "{A}'s slot is ahead of {B}'s."],
    "RIGHT_BEFORE": ["{B} takes the very next slot after {A}.", "{A} hands off straight to {B}.",
                     "Right after {A} comes {B}, nothing in between."],
    "BETWEEN": ["{A} lands somewhere between {B} and {C}.",
                "{B} and {C} are on either side of {A}, not necessarily next to it.",
                "{A}'s slot is flanked, at some distance, by {B} and {C}."],
}
DISTRACT_B = {
    "past": ["Three weeks back, {p} was on {s}.", "{p} was the {s} person before the change."],
    "unsettled": ["Someone suggested {p} for {t}; no decision yet.",
                  "{p} at {t} is pencilled in as a maybe."],
    "hypothetical": ["{p} at {t} might have been the better call.",
                     "In an ideal world {p} would take {t}."],
}


# Pool C: written last, after every prompt change, and used only to accept or
# reject those changes.
HEDGES_C = ["Unless the sheet is wrong, ", "For what it's worth, ", "Last I checked, ",
            "If the board is right, ", "Hand on heart, ", ""]
LEADS_C = ["Underlining this: ", "Noting it twice: ", "Restating: "]
T_C = {
    "AT": ["{a} is booked in at {b}.", "{b} belongs to {a} today.", "{a} starts at {b}."],
    "NOT AT": ["{a} is exempt from {b}.", "{b} is a no-go for {a}.", "{a} was spared {b}.",
               "{a}'s name is nowhere near {b}."],
    "ON": ["{a} has charge of {b}.", "{b} goes to {a}.", "{a} sits on {b}."],
    "NOT ON": ["{a} is not doing {b}.", "{b} is out of {a}'s remit.", "{a} was taken off {b}."],
    "BEFORE": ["{A} is in earlier than {B}.", "{B} turns up later in the day than {A}.",
               "{A}'s block comes first, {B}'s some time later."],
    "RIGHT_BEFORE": ["{B} starts the instant {A}'s block ends.", "{A}'s block leads straight into {B}'s.",
                     "{B} is on the block right after {A}'s."],
    "BETWEEN": ["Of {B}, {A} and {C}, {A} is the middle one in time.",
                "{A} comes after one of {B} and {C} and ahead of the other.",
                "In time order, {A} sits somewhere inside the span from {B} to {C} (either way round)."],
}
DISTRACT_C = {
    "past": ["Until recently {p} ran {s}.", "On the last rota {p} had {s}."],
    "unsettled": ["{p} for {t} is under discussion.", "Whether {p} gets {t} is anyone's guess."],
    "hypothetical": ["{p} at {t} would have been handy.", "Ideally {p} would have had {t}."],
}


# Pool D: written after the normalizer fix and the temporal guard were built,
# and used once, to accept or reject them.
HEDGES_D = ["Going by my notes, ", "I'd swear ", "To my mind, ", "As best I can tell, ",
            "Don't quote me, but ", "If the printout is current, ", ""]
LEADS_D = ["Flagged again: ", "Duplicate note: ", "Same point as earlier: "]
T_D = {
    "AT": ["{a} is down for {b}.", "{b} is {a}'s block.", "{a} clocks in at {b}."],
    "NOT AT": ["{a} won't be in at {b}.", "{b} is off the table for {a}.", "{a} turned down {b} and that stands.",
               "There's no {b} shift for {a}."],
    "ON": ["{a} is working {b}.", "{b} is being handled by {a}.", "{a} takes {b}."],
    "NOT ON": ["{a} has nothing to do with {b}.", "{b} isn't {a}'s.", "{a} is not on the {b} desk."],
    "BEFORE": ["{A} is on before {B}.", "{B} gets in after {A} does.", "{A} goes ahead of {B} in the day."],
    "RIGHT_BEFORE": ["{B} is on immediately after {A}.", "{A} is followed directly by {B}.",
                     "{A}, then {B} with no gap."],
    "BETWEEN": ["{A} is in the middle of {B} and {C}, time-wise.",
                "Time-wise {A} falls between {B} and {C}.",
                "{B} and {C} come on either before or after {A}, one each."],
}
DISTRACT_D = {
    "past": ["{p} did {s} in the previous rota.", "Formerly {p} handled {s}."],
    "unsettled": ["{p} on {t} has been mooted.", "{p} at {t}? Still being argued over."],
    "hypothetical": ["{p} on {t} could have worked.", "Had it been up to me, {p} would get {t}."],
}


def ent(x, stations, r, pool="A"):
    if x in stations:
        if pool == "B":
            return r.choice([f"the {x} lead", f"whoever's on {x}", f"the {x} cover"])
        if pool == "D":
            return r.choice([f"the {x} staffer", f"the person on the {x} desk", f"whoever is doing {x}"])
        if pool == "C":
            return r.choice([f"the {x} worker", f"whoever handles {x}", f"the person doing {x}"])
        return r.choice([f"the {x} person", f"whoever runs {x}", f"the one on {x}"])
    return x


T = {
    "AT": ["{a} is rostered for {b}.", "{b} goes to {a}.", "{a} has been given the {b} slot."],
    "NOT AT": ["{a} can't do {b}.", "{a} isn't working {b}.", "{a}'s request for {b} was refused.",
               "Don't expect {a} at {b}."],
    "ON": ["{a} is running {b}.", "{b} falls to {a}.", "{a} is the {b} person this time."],
    "NOT ON": ["{a} won't be anywhere near {b}.", "{b} is someone else's job, not {a}'s.",
               "{a} is kept off {b}."],
    "BEFORE": ["{A} clocks off before {B} clocks on.", "{B} starts at some point after {A}.",
               "{A} is earlier in the day than {B}."],
    "RIGHT_BEFORE": ["{B} picks up the moment {A} finishes.", "{A} and then immediately {B}.",
                     "{B} follows {A} with no gap."],
    "BETWEEN": ["{A} falls somewhere in the middle of {B} and {C}.",
                "Going by start times, {A} is sandwiched between {B} and {C}, not necessarily touching either.",
                "One of {B} and {C} is on before {A} and the other after."],
}
NOISE = [  # new wordings of the borderline distractor families
    (r"^(?:In the spring|Last month|On the previous cycle|Back in the old arrangement),? ", None),
]
DISTRACT = {
    "past": ["Before the reshuffle, {p} covered {s}.", "{p} used to run {s} in the winter."],
    "unsettled": ["Whether {p} ends up on {t} is still being discussed.",
                  "{p} on {t} was floated but never confirmed."],
    "hypothetical": ["{p} on {t} would have suited everyone better.",
                     "It would have been neater if {p} had the {t} block."],
}


def reword(line, hdr_people, stations, r, pool="A"):
    TT, DD = {"A": (T, DISTRACT), "B": (T_B, DISTRACT_B), "C": (T_C, DISTRACT_C), "D": (T_D, DISTRACT_D)}[pool]
    s = oracle.strip(line)
    t = oracle.translate(line)
    if t == "NONE":
        # reword the borderline distractor families; leave plain padding alone
        times = re.findall(r"\d\d:\d\d", s)
        names = [p for p in hdr_people if re.search(rf"\b{p}\b", s)]
        sts = [x for x in stations if x in s.lower()]
        if len(names) == 1 and sts and re.search(r"spring|month|previous|old arrangement|was .*'s|took", s, re.I):
            return r.choice(DD["past"]).format(p=names[0], s=sts[0])
        if len(names) == 1 and times and re.search(r"remember|open|disagreement|minuted", s, re.I):
            return r.choice(DD["unsettled"]).format(p=names[0], t=times[0])
        if len(names) == 1 and times and re.search(r"would|had taken|better fit|Putting", s, re.I):
            return r.choice(DD["hypothetical"]).format(p=names[0], t=times[0])
        return None
    neg = t.startswith("NOT ")
    parts = t.split()
    op = " ".join(parts[:2]) if neg else parts[0]
    args = parts[2:] if neg else parts[1:]
    tpl = r.choice(TT[op])
    args = [a.lower() if a.lower() in stations else a for a in args]
    if op in ("AT", "NOT AT", "ON", "NOT ON"):
        out = tpl.format(a=args[0], b=args[1])
        return out[0].upper() + out[1:]
    A = [ent(x, stations, r, pool) for x in args]
    out = tpl.format(A=A[0], B=A[1], C=A[2] if len(A) > 2 else "")
    return out[0].upper() + out[1:]


def main(items_p, key_p, out_items, out_key, seed=0, pool="A"):
    r = random.Random(seed)
    hedges, leads = {"A": (HEDGES, LEADS), "B": (HEDGES_B, LEADS_B), "C": (HEDGES_C, LEADS_C), "D": (HEDGES_D, LEADS_D)}[pool]
    items = json.load(open(items_p))
    key = json.load(open(key_p))
    new_items, new_key = [], {}
    for it in items:
        lines = it["text"].split("\n")
        people = re.search(r"rota: ([^.]*)\.", lines[0]).group(1).split(", ")
        stations = re.search(r"one person on each: ([^.]*)\.", lines[0]).group(1).split(", ")
        mapping, out = {}, [lines[0]]
        for l in lines[1:]:
            if not l.strip():
                out.append(l)
                continue
            nw = reword(l, people, stations, r, pool)
            if nw is None:
                nl = l
            else:
                h = r.choice(hedges)
                first = re.sub(r"'s$", "", nw.split(" ")[0])
                if h and first not in people:
                    nw = nw[0].lower() + nw[1:]
                nl = h + nw
                if re.match(r"^[^:]{0,59}: ", l):
                    nl = r.choice(leads) + nl
            mapping[l] = nl
            out.append(nl)
        new_items.append(dict(it, text="\n".join(out)))
        k = json.loads(json.dumps(key[it["id"]]))
        if k.get("conflict_line_sets"):
            k["conflict_line_sets"] = [[mapping.get(c, c) for c in core]
                                       for core in k["conflict_line_sets"]]
        new_key[it["id"]] = k
    json.dump(new_items, open(out_items, "w"), indent=1)
    json.dump(new_key, open(out_key, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:5], *(int(x) for x in sys.argv[5:6]), *sys.argv[6:7])
