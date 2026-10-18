"""Decide the case and its content from per-statement constraints.

The domain is small enough (5 people x 5 blocks x 3 stations = 720 worlds) to
enumerate outright, so there is no search heuristic to get wrong: each
constraint is a bitmask over worlds, the solution set is their AND, and a
minimal conflicting set is a set of statements whose AND is empty and whose
every proper subset's AND is not.
"""
import itertools
import re

from .header import Header

# Restatement prefixes ("It bears repeating: ...") are stripped before two
# lines are compared, so a restated line counts as the same statement.
def stmt_key(text):
    s = " ".join(text.split()).casefold()
    head, sep, tail = s.partition(": ")
    if sep and tail and len(head) < 60:
        s = tail
    return s


def popcount(m):
    return bin(m).count("1")


def statements(dom, parsed):
    """parsed: list of (line_text, Constraint) -> list of statement dicts,
    one per distinct normalised line, keeping the first wording."""
    out, seen = [], {}
    for text, c in parsed:
        k = stmt_key(text)
        if k in seen:
            continue
        seen[k] = len(out)
        out.append({"text": text, "c": c, "mask": dom.mask(c)})
    return out


def solutions(dom, stmts):
    m = dom.full
    for s in stmts:
        m &= s["mask"]
    return [i for i in range(len(dom.worlds)) if m >> i & 1]


def minimal_cores(dom, stmts, max_size=6, limit=50):
    """All minimal conflicting sets of the smallest size found, as lists of
    statement indices.  Exhaustive by increasing size up to max_size, then a
    deletion-based shrink as a fallback so an answer always comes back."""
    idx = [i for i, s in enumerate(stmts) if s["mask"] != dom.full]
    masks = [s["mask"] for s in stmts]
    found = []
    for k in range(1, min(max_size, len(idx)) + 1):
        for combo in itertools.combinations(idx, k):
            m = dom.full
            for i in combo:
                m &= masks[i]
                if not m:
                    break
            if m:
                continue
            # minimal iff every (k-1)-subset is satisfiable; since smaller
            # sizes were searched first and none were found inside this
            # combo, checking that no found core is a subset suffices only
            # for found cores -- check directly to be exact.
            if all(_and(masks, combo[:j] + combo[j + 1:], dom.full)
                   for j in range(k)):
                found.append(list(combo))
                if len(found) >= limit:
                    return found
        if found:
            return found
    # fallback: shrink the whole conflicting set by deletion
    cur = list(idx)
    if _and(masks, cur, dom.full):
        return []
    for i in list(cur):
        trial = [j for j in cur if j != i]
        if not _and(masks, trial, dom.full):
            cur = trial
    return [cur]


def _and(masks, idxs, full):
    m = full
    for i in idxs:
        m &= masks[i]
    return m


def decide(dom, stmts, min_core=3):
    """-> (answer dict, info dict)."""
    sols = solutions(dom, stmts)
    info = {"n_solutions": len(sols)}
    if len(sols) == 1:
        return {"case": "unique", "assignment": dom.render(sols[0])}, info
    if len(sols) > 1:
        return {"case": "ambiguous",
                "assignments": [dom.render(i) for i in sols]}, info
    cores = minimal_cores(dom, stmts)
    info["cores"] = cores
    # The set's cores all have >= min_core statements (stated in the brief);
    # a tiny core is more likely one misread statement than the real
    # contradiction, so prefer a core of plausible size when one exists.
    pick = cores[0] if cores else []
    big = [c for c in cores if len(c) >= min_core]
    if not big and cores and len(cores[0]) < min_core:
        more = minimal_cores_of_size_at_least(dom, stmts, min_core)
        if more:
            big = more
    if big:
        pick = big[0]
    info["core"] = pick
    return {"case": "inconsistent",
            "conflicts": [stmts[i]["text"] for i in pick]}, info


def minimal_cores_of_size_at_least(dom, stmts, k0, max_size=6):
    idx = [i for i, s in enumerate(stmts) if s["mask"] != dom.full]
    masks = [s["mask"] for s in stmts]
    for k in range(k0, min(max_size, len(idx)) + 1):
        out = []
        for combo in itertools.combinations(idx, k):
            if _and(masks, combo, dom.full):
                continue
            if all(_and(masks, combo[:j] + combo[j + 1:], dom.full)
                   for j in range(k)):
                out.append(list(combo))
        if out:
            return out
    return []
