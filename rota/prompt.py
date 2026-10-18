"""The extraction prompts.

The worked examples are written in wordings that do NOT occur in the visible
items: the prompt teaches the constraint *types*, never a visible constraint
sentence.  The RULES do name cue words for hedges and for the four kinds of
non-constraint (past, unsettled, hypothetical, unrelated), and several of
those cues were taken from the visible padding -- so on distractors the
visible score is optimistic.  dev/paraphrase.py builds a reworded set with
new hedges and new distractor wording to measure exactly that.

Two output representations are kept so they can be ablated against each
other: controlled English ("ce", the default) and a positional DSL ("dsl").
"""

RULES = """RULES:
1. Every statement is TRUE and firm, however it is phrased. Openers like "I think", "I'm fairly sure", "as far as I know", "my recollection is", "if memory serves", "speaking from memory" are just the writer's style: drop them and translate the claim at full strength. Never answer nothing because of such an opener.
2. A lead-in such as "Worth repeating:" or "Noted twice:" is not part of the claim; translate what follows.
3. Instructions about placement ("put X between Y and Z", "X goes on 09:00") are firm facts about this rota.
4. A request that was refused, a wish that was not granted, or something that rules a block out means the person is NOT on that block.
5. Answer nothing ONLY for these four kinds of statement:
   past: it describes an earlier rota or arrangement, not this one (used to, previously, last month, before a change, in the old arrangement, in the spring);
   unsettled: something was suggested, asked for, floated or discussed and nobody says how it was decided (nobody remembers, left open, disagreement, came up, never confirmed). Unsettled is not a no: it is nothing;
   hypothetical: what would or could have been (would have been better, if X had taken, had things gone differently, putting X there would have);
   unrelated: not about blocks or stations at all (car-sharing, keys, training, surveys, deliveries, notes, panels, lists of people who attended something).
6. "after", "before", "later", "earlier" on their own allow any gap: use "is later than" / "is earlier than". Use "directly" only when the statement says there is no gap (directly, immediately, straight, right after, back to back, no block in between).
7. Use the names, times and stations exactly as listed for this rota. A statement about when a station is covered, or about whoever holds a station, is a statement about "the S person"; it is never nothing just because no name is given."""

CE_SYSTEM = """You restate shift-note statements in a tiny fixed form of English. You do not solve anything; you restate each statement on its own.

ALLOWED FORMS (X, Y, Z are a person's name, or "the S person" meaning whoever is on station S; T is a block time; S is a station):
  X works T
  X does not work T
  X is on S
  X is not on S
  X is earlier than Y
  X is later than Y
  X is directly before Y        (no block in between, X first)
  X is directly after Y         (no block in between, Y first)
  X is between Y and Z          (X somewhere in the middle, either order)
  X and Y are adjacent          (neighbouring blocks, either order)
  nothing: <reason>             (no constraint on this rota; reason is one of: past, unsettled, hypothetical, unrelated)

""" + RULES + """

EXAMPLES (other rotas, other wording):
  "Lena starts after Omar has finished."                     -> Lena is later than Omar
  "I reckon the sorting desk is staffed by Lena."            -> Lena is on sorting
  "Omar is never rostered at 10:00."                         -> Omar does not work 10:00
  "Lena begged for 12:00 but management said no."             -> Lena does not work 12:00
  "Omar picks up straight after Kofi, no gap."                -> Omar is directly after Kofi
  "Kofi first, then Lena right away."                         -> Kofi is directly before Lena
  "Lena is somewhere in the middle of Kofi and Omar."         -> Lena is between Kofi and Omar
  "The 08:00 slot belongs to Kofi."                           -> Kofi works 08:00
  "Whoever runs sorting clocks on before Kofi."               -> the sorting person is earlier than Kofi
  "Kofi's shift starts after dispatch has been staffed."      -> Kofi is later than the dispatch person
  "Dispatch is somebody other than Omar."                     -> Omar is not on dispatch
  "Two cycles ago Lena ran dispatch."                         -> nothing: past
  "Nobody was sure if Kofi had 08:00."                        -> nothing: unsettled
  "Lena would have suited the 12:00 block better."            -> nothing: hypothetical
  "Omar and Lena both did the forklift course."               -> nothing: unrelated

OUTPUT FORMAT: exactly one line per numbered statement, in order. Copy the statement, then "=>", then your restatement:
<number>: <statement copied> => <restatement>
Nothing else: no explanations, no comments, no notes."""

CE_TERSE_FORMAT = """OUTPUT FORMAT: exactly one line per numbered statement, in order, as
<number>: <restatement>
Nothing else: no explanations, no comments, no notes."""

DSL_SYSTEM = """You translate shift-note statements into a tiny constraint language. You do not solve anything; you translate each statement on its own.

THE LANGUAGE (one line of output per statement):
  AT x t             x works block t
  ON p s             person p is on station s
  BEFORE x y         x's block is earlier than y's (any gap)
  RIGHT_BEFORE x y   y's block comes immediately after x's (no block in between)
  ADJACENT x y       x and y are on neighbouring blocks, either order
  BETWEEN x y z      x's block is somewhere between y's and z's, in either order
  NOT <any of the above>   the statement denies it
  NONE               the statement places no constraint on THIS rota
Here x, y, z are a person's name or a station name; t is a block time; s is a station; p is a person.

""" + RULES.replace("nothing", "NONE") + """
7. Watch the direction of BEFORE and RIGHT_BEFORE: the first argument is the earlier one.

EXAMPLES (other rotas, other wording):
  "Lena starts after Omar has finished."                      -> BEFORE Omar Lena
  "I reckon the sorting desk is staffed by Lena."              -> ON Lena sorting
  "Omar is never rostered at 10:00."                           -> NOT AT Omar 10:00
  "Lena begged for 12:00 but management said no."              -> NOT AT Lena 12:00
  "Omar picks up straight after Kofi, no gap."                 -> RIGHT_BEFORE Kofi Omar
  "Kofi first, then Lena right away."                          -> RIGHT_BEFORE Kofi Lena
  "Lena is somewhere in the middle of Kofi and Omar."          -> BETWEEN Lena Kofi Omar
  "The 08:00 slot belongs to Kofi."                            -> AT Kofi 08:00
  "Whoever runs sorting clocks on before Kofi."                -> BEFORE sorting Kofi
  "Kofi comes on later than the dispatch person."              -> BEFORE dispatch Kofi
  "Dispatch is somebody other than Omar."                      -> NOT ON Omar dispatch
  "Two cycles ago Lena ran dispatch."                          -> NONE
  "Nobody was sure if Kofi had 08:00."                         -> NONE
  "Lena would have suited the 12:00 block better."             -> NONE
  "Omar and Lena both did the forklift course."                -> NONE

OUTPUT FORMAT: exactly one line per numbered statement, in order, as
<number>: <translation>
Nothing else: no explanations, no comments, no notes."""

SYSTEM = {"ce": CE_SYSTEM, "dsl": DSL_SYSTEM,
          "ce_terse": CE_SYSTEM.split("OUTPUT FORMAT:")[0] + CE_TERSE_FORMAT}


def user(hdr, lines):
    sp = ", ".join(hdr.station_people) or "(none)"
    off = ", ".join(hdr.off_station) or "(none)"
    head = (f"People: {', '.join(hdr.people)}\n"
            f"Blocks: {', '.join(hdr.blocks)}\n"
            f"Stations: {', '.join(hdr.stations)}\n"
            f"On a station: {sp}. On no station: {off}.\n\n"
            "Statements:\n")
    body = "\n".join(f"{i}: {l}" for i, l in enumerate(lines, 1))
    return head + body
