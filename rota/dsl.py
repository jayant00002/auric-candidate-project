"""The constraint language the model translates each statement into, and its
compilation to a set of satisfying worlds.

One statement -> one line of the form

    OP arg arg ...        or     NOT OP arg arg ...     or     NONE

An *entity* argument is a person or a station; a station stands for whoever
holds it.  A *time* argument is a block, a *station* argument a station.

    AT x t             x works block t
    ON p s             person p holds station s
    BEFORE x y         x's block is earlier than y's (any gap)
    RIGHT_BEFORE x y   y's block is the one immediately after x's
    ADJACENT x y       x and y are on neighbouring blocks, either order
    BETWEEN x y z      x's block is strictly between y's and z's, either order
    SAME x y           x and y are the same person (e.g. "the 09:00 person
                       is the packing person")
    NONE               the statement constrains nothing

AFTER x y is accepted as BEFORE y x, and RIGHT_AFTER x y as RIGHT_BEFORE y x,
because the model reaches for them and refusing them only loses statements.

A constraint compiles to an int bitmask over the enumerated worlds; a set of
constraints is satisfiable iff the AND of their masks is non-zero.
"""
import itertools
import re
from dataclasses import dataclass

ARITY = {"AT": ("e", "t"), "ON": ("p", "s"), "BEFORE": ("e", "e"),
         "AFTER": ("e", "e"), "RIGHT_BEFORE": ("e", "e"),
         "RIGHT_AFTER": ("e", "e"), "ADJACENT": ("e", "e"),
         "BETWEEN": ("e", "e", "e"), "SAME": ("e", "e")}
ALIASES = {"NOT_AT": ("NOT", "AT"), "NOT_ON": ("NOT", "ON"),
           "IMMEDIATELY_BEFORE": (None, "RIGHT_BEFORE"),
           "DIRECTLY_BEFORE": (None, "RIGHT_BEFORE"),
           "IMMEDIATELY_AFTER": (None, "RIGHT_AFTER"),
           "DIRECTLY_AFTER": (None, "RIGHT_AFTER"),
           "NEXT_TO": (None, "ADJACENT"), "EARLIER": (None, "BEFORE"),
           "LATER": (None, "AFTER"), "IS": (None, "SAME")}


@dataclass(frozen=True)
class Constraint:
    op: str            # canonical op
    args: tuple        # canonical strings
    neg: bool = False

    def key(self):
        return (self.neg, self.op, self.args)

    def __str__(self):
        if self.op in ("OR", "AND"):
            return ("NOT " if self.neg else "") + "(" + f" {self.op} ".join(map(str, self.args)) + ")"
        return ("NOT " if self.neg else "") + " ".join((self.op,) + self.args)


class Domain:
    """All worlds for one item: a block per person, and a station per
    station-holder (one holder per station)."""

    def __init__(self, hdr):
        self.hdr = hdr
        self.people, self.blocks = hdr.people, hdr.blocks
        self.stations, self.sp = hdr.stations, hdr.station_people
        self.worlds = []
        n = len(self.blocks)
        for perm in itertools.permutations(range(n), len(self.people)):
            blk = dict(zip(self.people, perm))
            if self.stations and len(self.sp) == len(self.stations):
                for sperm in itertools.permutations(self.stations):
                    self.worlds.append((blk, dict(zip(self.sp, sperm))))
            else:
                self.worlds.append((blk, {}))
        self.full = (1 << len(self.worlds)) - 1
        self._canon = {}
        for kind, vals in (("p", self.people), ("s", self.stations),
                           ("t", self.blocks)):
            for v in vals:
                self._canon[(kind, _fold(v))] = v

    # ---- argument resolution -------------------------------------------
    def canon(self, kind, raw):
        f = _fold(raw)
        if kind == "e":
            return self.canon("p", raw) or self.canon("s", raw)
        if kind == "t":
            m = re.search(r"(\d{1,2}):?(\d{2})", raw)
            if m:
                f = _fold(f"{int(m.group(1)):02d}:{m.group(2)}")
        if (kind, f) in self._canon:
            return self._canon[(kind, f)]
        if kind == "s":   # "the calibration station", "calibrations"
            for s in self.stations:
                if _fold(s) in f or f in _fold(s):
                    return s
        if kind == "p":   # "Meera's"
            f2 = re.sub(r"'s$", "", f)
            if ("p", f2) in self._canon:
                return self._canon[("p", f2)]
        return None

    def parse(self, line):
        """One DSL line -> Constraint, 'NONE', or None if it does not parse."""
        line = line.split("#")[0].split("(")[0]
        toks = re.findall(r"[A-Za-z_]+(?:'s)?|\d{1,2}:\d{2}", line.replace("-", "_"))
        if not toks:
            return None
        toks = [t for t in toks]
        neg = False
        head = toks[0].upper()
        if head in ("NONE", "NOTHING", "NULL", "IRRELEVANT", "NOISE"):
            return "NONE"
        if head == "NOT" and len(toks) > 1:
            neg, toks = True, toks[1:]
            head = toks[0].upper()
        if head in ALIASES:
            n2, head = ALIASES[head]
            if n2 == "NOT":
                neg = not neg
        if head not in ARITY:
            return None
        raw_args = toks[1:1 + len(ARITY[head])]
        if head == "AT" and len(raw_args) == 2 and self.canon("s", raw_args[1]) \
                and not self.canon("t", raw_args[1]):
            head = "ON"           # "AT Ayesha calibration" means ON
        args = []
        for kind, raw in zip(ARITY[head], raw_args):
            c = self.canon(kind, raw)
            if c is None:
                return None
            args.append(c)
        if len(args) != len(ARITY[head]):
            return None
        if head == "AFTER":
            head, args = "BEFORE", args[::-1]
        elif head == "RIGHT_AFTER":
            head, args = "RIGHT_BEFORE", args[::-1]
        return _norm(Constraint(head, tuple(args), neg))

    # ---- semantics -----------------------------------------------------
    def _pos(self, w, x):
        blk, st = w
        if x in blk:
            return blk[x]
        for p, s in st.items():
            if s == x:
                return blk[p]
        return None

    def _who(self, w, x):
        if x in self.people:
            return x
        for p, s in w[1].items():
            if s == x:
                return p
        return None

    def holds(self, c, w):
        a = c.args
        if c.op == "OR":
            v = any(self.holds(x, w) for x in a)
        elif c.op == "AND":
            v = all(self.holds(x, w) for x in a)
        elif c.op == "AT":
            v = self._pos(w, a[0]) == self.blocks.index(a[1])
        elif c.op == "ON":
            v = w[1].get(a[0]) == a[1]
        elif c.op == "SAME":
            v = self._who(w, a[0]) == self._who(w, a[1])
        else:
            ps = [self._pos(w, x) for x in a]
            if None in ps:
                v = False
            elif c.op == "BEFORE":
                v = ps[0] < ps[1]
            elif c.op == "RIGHT_BEFORE":
                v = ps[1] == ps[0] + 1
            elif c.op == "ADJACENT":
                v = abs(ps[0] - ps[1]) == 1
            elif c.op == "BETWEEN":
                v = min(ps[1], ps[2]) < ps[0] < max(ps[1], ps[2])
            else:
                v = False
        return v != c.neg

    def mask(self, c):
        m = 0
        for i, w in enumerate(self.worlds):
            if self.holds(c, w):
                m |= 1 << i
        return m

    def render(self, i):
        """World i as the answers.json assignment object."""
        blk, st = self.worlds[i]
        out = {}
        for p in self.people:
            out[p] = {"block": self.blocks[blk[p]]}
            if p in st:
                out[p]["station"] = st[p]
        return out


def _fold(s):
    return " ".join(str(s).split()).casefold().strip(" .,;'\"")


# ---------------------------------------------------------------------------
# Controlled English.  The model restates each claim in one of a handful of
# fixed English shapes; this grammar reads them.  Roles are carried by word
# order the way English carries them ("X is between Y and Z"), so the model
# never has to remember which positional slot is the middle one.
# ---------------------------------------------------------------------------
_E = r"(.+?)"
CE_RULES = [
    (rf"^{_E} (?:works|is at|is on|has) (?:the )?(\d{{1,2}}:\d{{2}})(?: block)?$", "AT", (0, 1)),
    (rf"^{_E} is earlier than {_E}$", "BEFORE", (0, 1)),
    (rf"^{_E} is later than {_E}$", "BEFORE", (1, 0)),
    (rf"^{_E} is directly before {_E}$", "RIGHT_BEFORE", (0, 1)),
    (rf"^{_E} is directly after {_E}$", "RIGHT_BEFORE", (1, 0)),
    (rf"^{_E} is between {_E} and {_E}$", "BETWEEN", (0, 1, 2)),
    (rf"^{_E} and {_E} are adjacent$", "ADJACENT", (0, 1)),
    (rf"^{_E} is on (?:the )?{_E}(?: station)?$", "ON", (0, 1)),
    (rf"^{_E} (?:works|has|is at|covers) (?:the )?{_E}(?: station)?$", "ON", (0, 1)),
    (rf"^{_E} is the same person as {_E}$", "SAME", (0, 1)),
]
_NEG = [(r"\bdoes not work\b", "works"), (r"\bdoesn't work\b", "works"),
        (r"\bis not\b", "is"), (r"\bisn't\b", "is"), (r"\bare not\b", "are"),
        (r"\baren't\b", "are"), (r"\bdoes not have\b", "has"),
        (r"\bnot\s+", "")]


def _ce_clean(s):
    s = s.split("#")[0].strip().strip("`*\"'").strip()
    if s.startswith("("):            # "(A is earlier than B) and (...)"
        s = s.replace("(", "").replace(")", "")
    else:                            # "A is earlier than B (because ...)"
        s = s.split(" (")[0]
    s = re.sub(r"[.;]+$", "", s).strip()
    return " ".join(s.split())


_BETWEEN_ONE_OF = re.compile(
    r"^(.+?) is (?:directly |immediately |somewhere )?(?:after|later than) one of \{?(.+?)(?:,| and| or) (.+?)\}?,?"
    r"(?: and)?(?: \1)?(?: is)? (?:directly |immediately )?(?:before|earlier than) the other\b.*$")


_ONE_OF_SUBJ = re.compile(
    r"^\(?one of (.+?) (?:and|or) (.+?)\)? is (?:earlier|before|later|after)(?: than)? (.+?),? and "
    r"(?:\(?(?:the other|.+? or .+?)\)?) is (?:later|after|earlier|before)(?: than)? (?:\3|them|him|her)\b.*$")
_EITHER_SIDE = re.compile(
    r"^(.+?) is earlier than (.+?) and (.+?) is later than \2 or \3 is earlier than \2 and \1 is later than \2$")


def parse_ce(dom, raw, lenient=True):
    """One controlled-English restatement -> Constraint | 'NONE' | None.

    Beyond the listed forms it also reads the shapes the model reaches for
    when a statement does not fit one form: "X is after one of Y and Z and
    before the other", and simple "A or B" / "A and B" combinations of
    forms.  This normalises the model's OUTPUT language, which is the same
    whatever the wording of the notes."""
    s = _ce_clean(raw)
    if not lenient:
        return _parse_ce_atom(dom, s)
    low = s.lower()
    for pat, order in ((_BETWEEN_ONE_OF, (0, 1, 2)), (_ONE_OF_SUBJ, (2, 0, 1)),
                       (_EITHER_SIDE, (1, 0, 2))):
        m = pat.match(low)
        if m:
            g = m.groups()
            args = [dom.canon("e", _ent(g[i])) for i in order]
            return _norm(Constraint("BETWEEN", tuple(args))) if None not in args else None
    return _parse_ce_bool(dom, s)


def _parse_ce_bool(dom, s, seps=((" or ", "OR"), (" and ", "AND"))):
    c = _parse_ce_atom(dom, s)
    if c is not None or not seps:
        return c
    (sep, op), rest = seps[0], seps[1:]
    if sep not in s.lower():
        return _parse_ce_bool(dom, s, rest)
    pieces = re.split(sep, s, flags=re.I)
    # "X is directly after A or directly before B": carry the subject over
    subj = re.match(r"^(.+?) (?:is|are|does|works) ", pieces[0])
    if subj:
        pieces = [pieces[0]] + [p if not re.match(r"^(?:is|are|does|works|directly|not) ", p.strip(), re.I)
                                else (subj.group(1) + " " + ("is " if re.match(r"^directly", p.strip(), re.I) else "") + p.strip())
                                for p in pieces[1:]]
    parts = [_parse_ce_bool(dom, p, rest) for p in pieces]
    parts = [p for p in parts if p != "NONE"]
    if not parts or None in parts:
        return None
    return parts[0] if len(parts) == 1 else Constraint(op, tuple(parts))


def _parse_ce_atom(dom, raw):
    s = _ce_clean(raw)
    low = s.lower()
    if not s or low in ("nothing", "none", "no constraint", "n/a"):
        return "NONE"
    if low.startswith("nothing") or low.startswith("none"):
        return "NONE"
    neg = False
    for pat, rep in _NEG:
        if re.search(pat, low):
            low2 = re.sub(pat, rep, low, count=1)
            neg, low = True, low2
            break
    for pat, op, order in CE_RULES:
        m = re.match(pat, low)
        if not m:
            continue
        groups = [m.group(i + 1) for i in order]
        kinds = ARITY[op]
        args = []
        for kind, g in zip(kinds, groups):
            c = dom.canon(kind, _ent(g))
            if c is None and kind == "s":
                c = dom.canon("s", g)
            args.append(c)
        if None in args:
            # "X is on intake" vs "X is on 09:00" is decided by the argument
            if op == "ON":
                continue
            return None
        return _norm(Constraint(op, tuple(args), neg))
    return None


def _ent(g):
    g = g.strip()
    g = re.sub(r"^(?:the |whoever (?:is on|has|holds|covers) )", "", g)
    g = re.sub(r"(?:'s)? (?:person|station|holder|block|slot)$", "", g)
    g = re.sub(r"'s$", "", g)
    return g.strip(" {}[]")


def _norm(c):
    """Canonical form, so equivalent translations vote together."""
    if c.op == "BETWEEN":
        return Constraint(c.op, (c.args[0],) + tuple(sorted(c.args[1:])), c.neg)
    if c.op in ("ADJACENT", "SAME"):
        return Constraint(c.op, tuple(sorted(c.args)), c.neg)
    return c
