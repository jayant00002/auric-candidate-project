"""DEV ONLY -- never on the answering path.

A hand-written template translator for the phrasings in the VISIBLE set.  It
exists to (1) pin down the semantics of borderline statement types against
visible_key.json, and (2) give a per-statement reference translation to measure
the model's extraction against.  It cannot generalise to the held-out phrasing
pool by construction, which is exactly why the shipped system does not use it.
"""
import re

P = r"([A-Z][a-z]+)"
T = r"(\d\d:\d\d)"
S = r"([A-Za-z]+)"

HEDGES = ("i'm fairly sure ", "from what i recall, ", "as far as i know, ",
          "i believe ", "going off the roster, ", "if memory serves, ",
          "my recollection is that ", "unless i have this wrong, ",
          "speaking from memory, ", "i'm reasonably confident ")

# (pattern, template) -- template uses \1.. groups
RULES = [
    (rf"^{P} sits between {P} and {P} on the rota\.$", r"BETWEEN \1 \2 \3"),
    (rf"^{P} is on after one of {P} and {P} and before the other\.$", r"BETWEEN \1 \2 \3"),
    (rf"^{P}'s block falls between {P}'s and {P}'s, in one order or the other\.$", r"BETWEEN \1 \2 \3"),
    (rf"^{P} works at some point between {P} and {P}, not necessarily adjacent to either\.$", r"BETWEEN \1 \2 \3"),
    (rf"^[Ww]hichever way round {P} and {P} are, {P} is between them\.$", r"BETWEEN \3 \1 \2"),
    (rf"^[Pp]ut {P} between {P} and {P}, though not necessarily next to either\.$", r"BETWEEN \1 \2 \3"),
    (rf"^[Tt]he {S} station is covered earlier in the day than {P}'s block\.$", r"BEFORE \1 \2"),
    (rf"^{S} is covered by someone other than {P}\.$", r"NOT ON \2 \1"),
    (rf"^{P} (?:lobbied for|wanted) {T} (?:without success|and did not get it)\.$", r"NOT AT \1 \2"),
    (rf"^{P} is on later than whoever has {S}\.$", r"BEFORE \2 \1"),
    (rf"^{P} relieves {P} directly, with no block in between\.$", r"RIGHT_BEFORE \2 \1"),
    (rf"^{P} has a standing commitment that rules out the {T} block entirely\.$", r"NOT AT \1 \2"),
    (rf"^{P} put in for the {T} block and was turned down\.$", r"NOT AT \1 \2"),
    (rf"^{P} asked to move to the {T} block; the request was declined\.$", r"NOT AT \1 \2"),
    (rf"^{P} (?:has not been put on|is not on|is not assigned to) {S}\.$", r"NOT ON \1 \2"),
    (rf"^{S} is not {P}'s station\.$", r"NOT ON \2 \1"),
    (rf"^[Yy]ou can rule {P} out for {S}\.$", r"NOT ON \1 \2"),
    (rf"^{S} is covered before {P} comes on\.$", r"BEFORE \1 \2"),
    (rf"^[Tt]he person on {S} precedes {P}\.$", r"BEFORE \1 \2"),
    (rf"^[Ww]hoever (?:is on|has) {S} (?:works earlier in the day than|is done before) {P}(?: starts)?\.$", r"BEFORE \1 \2"),
    (rf"^{S} is {P}'s station\.$", r"ON \2 \1"),
    (rf"^{P} (?:is assigned to|is on|has) {S}(?: this week)?\.$", r"ON \1 \2"),
    (rf"^{S} is covered by {P}\.$", r"ON \2 \1"),
    (rf"^[Tt]he {S} station is down to {P}\.$", r"ON \2 \1"),
    (rf"^{T} is the one block {P} is definitely not on\.$", r"NOT AT \2 \1"),
    (rf"^{P} is unavailable at {T}\.$", r"NOT AT \1 \2"),
    (rf"^{P} is not on the {T} block\.$", r"NOT AT \1 \2"),
    (rf"^[Tt]he {T} block is not {P}'s\.$", r"NOT AT \2 \1"),
    (rf"^[Yy]ou will not find {P} on the {T} block\.$", r"NOT AT \1 \2"),
    (rf"^{P} is on the block (?:directly|immediately) after {P}\.$", r"RIGHT_BEFORE \2 \1"),
    (rf"^{P} is on the block immediately before {P}\.$", r"RIGHT_BEFORE \1 \2"),
    (rf"^{P} then {P}, back to back\.$", r"RIGHT_BEFORE \1 \2"),
    (rf"^{P} hands straight over to {P}\.$", r"RIGHT_BEFORE \1 \2"),
    (rf"^[Tt]here is no block between {P}'s and {P}'s, in that order\.$", r"RIGHT_BEFORE \1 \2"),
    (rf"^{P} comes later in the day than {P}\.$", r"BEFORE \2 \1"),
    (rf"^{P} takes over from {P} later in the day\.$", r"BEFORE \2 \1"),
    (rf"^{P}'s block falls somewhere earlier than {P}'s\.$", r"BEFORE \1 \2"),
    (rf"^{P} (?:works earlier in the day than|is done before) {P}(?: starts)?\.$", r"BEFORE \1 \2"),
    (rf"^[Bb]y the time {P} starts, {P} has already been on\.$", r"BEFORE \2 \1"),
    (rf"^{P} is the one who opens up at {T}\.$", r"AT \1 \2"),
    (rf"^[Ww]hoever drew the {T} block, it was {P}\.$", r"AT \2 \1"),
    (rf"^{P} takes {T}, as things stand\.$", r"AT \1 \2"),
    (rf"^[Tt]he {T} block is {P}'s\.$", r"AT \2 \1"),
    (rf"^{T} is when {P} is scheduled\.$", r"AT \2 \1"),
    (rf"^{P} is on the {T} block\.$", r"AT \1 \2"),
]

# borderline families whose meaning is decided against the key
COUNTERFACTUAL = [
    rf"^{P} would have been a better fit for the {T} block\.$",
    rf"^[Ii]f {P} had taken the {T} block the handover would have been smoother\.$",
    rf"^[Hh]ad the rota gone the other way, {P} would be on {T}\.$",
    rf"^[Pp]utting {P} on the {T} block would have solved the parking problem\.$",
]


def strip(line):
    s = line.strip()
    head, sep, tail = s.partition(": ")
    if sep and tail and len(head) < 60:
        s = tail
    for h in HEDGES:
        if s.lower().startswith(h):
            s = s[len(h):]
            break
    return s


def translate(line, counterfactual="NONE"):
    s = strip(line)
    for pat, tpl in RULES:
        m = re.match(pat, s)
        if m:
            return m.expand(tpl)
    for pat in COUNTERFACTUAL:
        m = re.match(pat, s)
        if m:
            if counterfactual == "NONE":
                return "NONE"
            return f"{counterfactual} {m.group(1)} {m.group(2)}"
    return "NONE"
