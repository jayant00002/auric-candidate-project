"""One item end to end: header -> model translation of each statement ->
symbolic solve -> answer.  Extra budget buys more translations, combined per
statement by vote."""
import collections
import re

from . import direct, dsl, header, normalize, prompt, solver

DEFAULTS = dict(
    dedupe=True,        # send each restated statement once
    vote="asym",        # combine samples per statement: "asym" (a constraint
                        # beats "nothing" on a minority of votes), "plural"
                        # (plain plurality), or "none" (last sample only)
    min_core=3,         # prefer conflicts of the size the set guarantees
    lenient=True,       # also read or/and and "after one of X and Y" outputs
    mode="solve",       # "direct": ablation arm, the model answers by itself
    repair=True,        # if the voted outcome is impossible, re-vote
    adaptive=False,     # stop sampling early once the vote is settled
    repr="ce",          # model output: controlled English with the statement
                        # echoed ("ce"), without the echo ("ce_terse"), or the
                        # positional DSL ("dsl")
    prefilter=True,     # drop statements naming no person, block or station
    normalize=True,     # strip hedges / restatement lead-ins before sending
    realign=True,       # use the echoed statement to fix the model's numbering
    ground=True,        # reject translations naming things the statement doesn't
)


def _toks(s):
    return set(re.findall(r"[a-z0-9:']+", s.casefold()))


def _sim(a, b):
    a, b = _toks(a), _toks(b)
    return len(a & b) / max(1, len(a | b))


def grounded(dom, c, text):
    """Every person and station a translation names must be named by the
    statement; a block time must be too, unless the statement names none."""
    if c in (None, "NONE"):
        return True
    if c.op in ("OR", "AND"):
        return all(grounded(dom, x, text) for x in c.args)
    low = text.casefold()
    words = set(re.findall(r"[a-z]+", low))
    has_time = bool(re.search(r"\d{1,2}:\d{2}", text))
    for a in c.args:
        if a in dom.people and a.casefold() not in words:
            return False
        if a in dom.stations and a.casefold() not in low:
            return False
        if a in dom.blocks and has_time and a not in text:
            return False
    return True


def parse_output(dom, text, lines, rep="ce", realign=True, ground=True,
                 lenient=True):
    """'<k>: [<copy> =>] <translation>' lines -> list (one per statement) of
    Constraint | 'NONE' | None (no usable translation).

    When the model revises itself and repeats a number, the LAST readable
    translation wins.  With an echoed copy, the copy -- not the number --
    decides which statement a translation belongs to when they disagree."""
    n = len(lines)
    out = [None] * n
    if not text:
        return out
    if rep.startswith("ce"):
        read = lambda d, b: dsl.parse_ce(d, b, lenient)
    else:
        read = lambda d, b: d.parse(b)
    for line in text.split("\n"):
        m = re.match(r"\s*[\(\[]?(\d+)[\)\].:]*\s*[:.\-)]?\s*(.*)$", line)
        if not m:
            continue
        k = int(m.group(1)) - 1
        rest = m.group(2)
        if realign and "=>" in rest:
            copy = rest.split("=>")[0]
            sims = [_sim(copy, l) for l in lines]
            j = max(range(n), key=lambda i: sims[i])
            if not (0 <= k < n) or (sims[j] > 0.6 and sims[j] > sims[k] + 0.2):
                k = j
        if 0 <= k < n:
            body = re.sub(r"^\W+|[`*]+", "", rest)
            body = body.split("->")[-1].split("=>")[-1].strip()
            c = read(dom, body)
            if c is None:
                continue
            if ground and not grounded(dom, c, lines[k]):
                continue
            out[k] = c
    return out


def vote(samples, n, mode="plural", min_real=None):
    """Per-statement vote over samples; unparsed samples abstain.  Ties go to
    the earliest-seen translation.  Returns (choice, agreement).

    "asym": the model drops real constraints (answers "nothing") far more
    often than it invents one for a padding line -- measured at roughly 40:1
    on the visible set -- so a constraint needs only ceil(k/5) of k votes to
    beat "nothing"; among constraints, plurality."""
    choice, agree = [], []
    for i in range(n):
        votes = [s[i] for s in samples if s[i] is not None]
        if mode == "asym":
            real = [v for v in votes if v != "NONE"]
            need = min_real if min_real is not None else -(-len(samples) // 5)
            if real and len(real) >= need:
                votes = real
        if not votes:
            choice.append("NONE")
            agree.append(0.0)
            continue
        keys = [v if v == "NONE" else v.key() for v in votes]
        cnt = collections.Counter(keys)
        best = max(cnt, key=lambda k: (cnt[k], -keys.index(k)))
        choice.append(votes[keys.index(best)])
        agree.append(cnt[best] / len(samples))
    return choice, agree


def solve(dom, lines, choice, cfg):
    parsed = [(l, c) for l, c in zip(lines, choice) if c not in (None, "NONE")]
    stmts = solver.statements(dom, parsed)
    return solver.decide(dom, stmts, min_core=cfg["min_core"])


def plausible(info, cfg):
    n = info["n_solutions"]
    if n == 0:
        return len(info.get("core", [])) >= cfg["min_core"]
    return n <= 4


def settled(samples, n):
    """Every statement's plurality is a strict majority of all samples taken."""
    _, agree = vote(samples, n, "plural")
    return all(a > 0.5 for a in agree)


def mentions_entity(hdr, line):
    """Can this statement constrain anything at all?  One that names no
    person, no block and no station cannot, whatever its wording."""
    low = line.casefold()
    words = set(re.findall(r"[a-z]+", low))
    return (any(p.casefold() in words for p in hdr.people)
            or any(s.casefold() in low for s in hdr.stations)
            or any(b in line for b in hdr.blocks))


def answer(item, sess, cfg=None):
    cfg = dict(DEFAULTS, **(cfg or {}))
    hdr = header.parse(item["text"])
    dom = dsl.Domain(hdr)
    lines, sent, seen = [], [], set()     # original wording / what is sent
    for _, l in hdr.body:
        c = normalize.clean(l) if cfg["normalize"] else l
        k = solver.stmt_key(c)
        if cfg["dedupe"] and k in seen:
            continue
        seen.add(k)
        if cfg["prefilter"] and not mentions_entity(hdr, l):
            continue
        lines.append(l)
        sent.append(c)
    n = len(lines)
    sys_p, user_p = prompt.SYSTEM[cfg["repr"]], prompt.user(hdr, sent)

    if cfg["mode"] == "direct":
        return direct.ask(sess, hdr, sent, lines), {"n_solutions": None, "lines": lines}

    samples = []
    while sess.left > 0:
        samples.append(parse_output(dom, sess.ask(sys_p, user_p), sent, cfg["repr"],
                                    cfg["realign"], cfg["ground"], cfg["lenient"]))
        if cfg["adaptive"] and len(samples) >= 3 and settled(samples, n):
            break
    if cfg["vote"] != "none":
        choice, agree = vote(samples, n, cfg["vote"])
    else:
        choice = [c if c is not None else "NONE" for c in samples[-1]]
        agree = [1.0] * n
    ans, info = solve(dom, lines, choice, cfg)
    if cfg["repair"] and cfg["vote"] == "asym" and len(samples) > 1 \
            and not plausible(info, cfg):
        # The vote's evidence threshold is the one free knob; move it toward
        # whichever side makes the outcome a possible one (1-4 solutions, or
        # a conflict of plausible size), nearest to the default first.
        k, default = len(samples), -(-len(samples) // 5)
        for t in sorted(range(1, k + 1), key=lambda t: (abs(t - default), t)):
            if t == default:
                continue
            c2, a2 = vote(samples, n, "asym", t)
            ans2, info2 = solve(dom, lines, c2, cfg)
            if plausible(info2, cfg):
                ans, info, choice, agree = ans2, info2, c2, a2
                info["repaired_threshold"] = t
                break
    info.update(calls=sess.used, lines=lines,
                translations=[str(c) for c in choice], agreement=agree)
    return ans, info
