"""Strip what is texture, not content, before the model sees a statement.

Two things are removed, both defined by the task rather than by any item's
wording: a restatement lead-in ("Worth restating: ...", the same rule the
scorer applies), and a speaker hedge ("I'm fairly sure", "as far as I know").
The brief says hedges carry full force; the model nevertheless reads them as
doubt and answers "nothing", so they are taken off rather than argued with.

A hedge is recognised by a first-person / memory marker, not by a list of
exact phrases, so new hedge wordings are caught too.  A leading clause with no
such marker ("Back in the old arrangement, ...") is kept: it changes the
meaning.  The citation always quotes the original line, never this form.
"""
import re

_MARK = r"\b(?:I|I'm|I've|I'd|me|my|memory|recollection|recall|roster)\b"
_LEAD_CLAUSE = re.compile(r"^([^,.;:]{0,60}),\s+(.*)$")
_LEAD_VERB = re.compile(
    r"^(?:I(?:'m| am)?|I'd)\s+(?:\w+\s+){0,2}?"
    r"(?:sure|confident|certain|believe|think|reckon|gather|understand|recall|remember)"
    r"(?:\s+that)?\s+(.*)$", re.I)
_BARE_ADJ = re.compile(
    r"^(?:(?:pretty|fairly|quite|reasonably|almost|very|100%)\s+)?(?:sure|confident|certain)(?! enough)"
    r"(?:\s+that)?,?\s+(.*)$", re.I)
_MY_X_IS = re.compile(r"^my\s+\w+(?:\s+\w+)?\s+is\s+that\s+(.*)$", re.I)


def strip_restatement(s):
    head, sep, tail = s.partition(": ")
    if sep and tail and len(head) < 60:
        return tail
    return s


def strip_hedge(s):
    for _ in range(2):              # "Speaking from memory, I believe ..."
        m = _LEAD_CLAUSE.match(s)
        if m and re.search(_MARK, m.group(1), re.I):
            s = m.group(2)
            continue
        m = _LEAD_VERB.match(s) or _MY_X_IS.match(s) or _BARE_ADJ.match(s)
        if m:
            s = m.group(1)
            continue
        break
    return s[:1].upper() + s[1:] if s else s


def clean(line):
    return strip_hedge(strip_restatement(line.strip()))
