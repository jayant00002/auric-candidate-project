"""Parse the item header: who is on the rota, the blocks, the stations, and
who holds a station.

The header is the one part of an item that is a fixed, fully specified
sentence pattern (it states the puzzle's domain, not its constraints), so it is
read symbolically.  The patterns are deliberately loose -- any list after
"rota:", any HH:MM times, any list after "one person on each:" -- and there is
a fallback for each field so a reworded header degrades rather than crashes.
"""
import re
from dataclasses import dataclass, field

TIME = re.compile(r"\b\d{1,2}:\d{2}\b")


def _split_list(s):
    s = re.sub(r"\s+(?:and|&)\s+", ", ", s.strip())
    return [x.strip(" .;") for x in s.split(",") if x.strip(" .;")]


@dataclass
class Header:
    people: list
    blocks: list
    stations: list
    station_people: list
    body: list = field(default_factory=list)   # (index, original line) pairs

    @property
    def off_station(self):
        return [p for p in self.people if p not in self.station_people]


def parse(text):
    lines = text.split("\n")
    head = lines[0]
    body = [(i, l) for i, l in enumerate(lines[1:], 1) if l.strip()]

    m = re.search(r"rota:\s*([^.]*)\.", head)
    people = _split_list(m.group(1)) if m else []

    m = re.search(r"[Bb]locks run ([^a-z]*?)(?:,\s*one person|\.)", head)
    blocks = TIME.findall(m.group(1)) if m else []
    if not blocks:
        blocks = list(dict.fromkeys(TIME.findall(head)))

    m = re.search(r"one person on each:\s*([^.]*)\.", head)
    stations = _split_list(m.group(1)) if m else []

    m = re.search(r"people on a station are\s*([^;.]*)", head)
    station_people = _split_list(m.group(1)) if m else []
    if not station_people and stations and len(stations) == len(people):
        station_people = list(people)

    if not people:
        # fallback: capitalised words that recur in the body
        caps = re.findall(r"\b[A-Z][a-z]+\b", text)
        people = [w for w in dict.fromkeys(caps) if caps.count(w) >= 3][:len(blocks) or 5]

    return Header(people, blocks, stations, station_people, body)
