# Architecture under a fixed weak model

**Result (macro exact match, mean of n runs).** Visible: 1x **87.8 (n=3)**, 3x **93.3 (n=1)**, 10x **91.7 (n=1)**. Unseen wording (reworded copies of the visible items, whose constraint wording, hedges and distractors appear nowhere in the package or the prompt): pool A 1x 76.7 / 3x 88.3 / 10x 90.0. Three harder pools, written after the design was frozen, show how far that drops on unfamiliar hedges: pool B about 54, pool C 28 and pool D 37 at 1x. Their runs are listed in the appendix. Read the visible number as a ceiling, and pools A to D as the range to expect on held-out text. The same model answering directly scores 0.0 at every budget. Every number, run count and ablation is in the appendix.

**Constraint extraction is model-based.** Each constraint comes from Granite's restatement of one statement. The surrounding code is symbolic: it reads the header, strips hedges, reads the model's *output* language and solves. It never matches the notes' constraint wording.

## 1. Characterising the model first

I built the solver first and checked it with a dev-only template translator of the visible wording ([dev/oracle.py](dev/oracle.py)). Given perfect translations it scores **100%**, so the question is how well Granite translates one statement. I scored every run end to end and per statement. Five findings:

- **It cannot do positional slots.** In a `BETWEEN x y z` DSL it misplaced the middle person and flipped `BEFORE`. That gave 43% macro at 1x. Restating the claim in fixed English ("Meera is between Tomas and Rohan") carries the roles in word order: 88%.
- **Its errors are lopsided.** It drops a real constraint ("nothing") 20 to 40 times more often than it invents one. So most failures are items declared `ambiguous` (12 of 180 at 1x).
- **It reads any hedge as doubt.** "My recollection is that …" and "Unless the sheet is wrong, …" both get "nothing: unsettled". Instructions don't stop this; removing the hedge does.
- **It revises itself mid-list** (the later version is usually right) and drifts in numbering on long lists.
- **Noise at T=1.0 is about ±4 points per run.** Most per-statement errors are independent across samples, so 1x → 3x gains 5 to 12 points. The remainder are consistent misreadings that no vote fixes, so 3x ≈ 10x.

## 2. What each component is for (1x ablation in brackets: drop when removed)

1. **Exhaustive solver over 720 worlds** (to 0.0). Each constraint becomes a bitmask. `inconsistent` cites the smallest minimal conflicting set, verbatim from the notes.
2. **Controlled English, not a DSL** (−45).
3. **Echo then restate** (−24). Copying each statement first keeps the model aligned.
4. **Lenient output reader** (−9; −9 on pool A). It accepts the model's own shapes, such as "A or B" and "after one of Y and Z and before the other".
5. **Hedge normalizer** (−3; −13 on pool A). It removes a restatement lead-in ("Worth repeating: …"), a verb-form hedge ("I believe …", "My recollection is that …", "pretty sure …"), and a leading comma clause that contains a first-person or memory word ("As far as I know, …"). A leading clause with no such word ("Back in the old arrangement, …") is kept. It has a known content-deleting bug, described in sections 3 and 4.
6. **Realign by echo, grounding, prefilter, dedupe, prefer cores of 3 or more statements.** Each is worth 1 to 3 points, within noise at n=3, so they are kept as cheap insurance, not as proven gains.
7. **3x/10x: asymmetric vote, then plausibility repair** (no vote: −10 at 10x). Because drops dominate, a constraint beats "nothing" with ⌈k/5⌉ votes. If the outcome is impossible (more than 4 solutions, or a core under 3 statements), the vote threshold moves.

## 3. Built, then removed

- **A positional DSL.** Replaced by controlled English.
- **Prompt rules arguing with hedges.** Stripping the hedges worked; the rules didn't.
- **First-occurrence parsing and a 1,200-token cap.** The model's corrections come late, so the last readable translation now wins, and the cap was raised.
- **Targeted re-asks at 3x/10x.** Re-asking only the disputed statements scored 61.3 vs 61.3 on pool B over 4 runs. What remains wrong is wrong in every sample.
- **Generic prompt rules,** replacing cue phrases copied from the visible padding with definitions by meaning. Pool C: 24.4 vs 27.8. Dropped.
- **A content-safe normalizer and a past/undecided guard (tried, not shipped).** The fix for the normalizer bug (section 4) brings content loss to 0 lines. The guard, replayed on saved outputs, gained 0 to 7 points and never lost. The API key's limit ran out after one fresh-call check (visible 93.3 vs 93.3; pool D 33.3 vs 36.7), too few runs to show a gain, and the ablation could not be re-run on changed code. So the submitted code is exactly what the ablation tables measure.

## 4. Where it breaks

- **The hedge normalizer deletes content on 31 of 5,685 lines across the five sets (13 visible).** A leading clause with a memory word is removed even when the claim sits inside it: "I'd swear Meera is in the middle of Tomas and Rohan, time-wise." becomes "Time-wise." This is a deterministic preprocessing bug, not a model limit. It does not explain pool C, which loses no content and still scores 28%.
- **Unfamiliar hedges and idioms: the main risk on held-out text.** The prompt rules name hedge and distractor cues taken from the visible padding; new ones are missed. "Unless the sheet is wrong, …" is read as a condition (pool C: 28% at 1x), polarity idioms flip ("asked off 13:00 and got it" became `AT`), and "on either side of" gains a spurious adjacency.
- **Systematic misreads survive any budget.** For example, "no block between X's and Y's, in that order" is read as unordered.
- **Assumptions:** one claim per line, the header template, and a closed language with no counting.

## 5. With a month

- **Ask a different question, not the same one again.** For example, check a restatement by asking "according to this sentence, is Daniel on 13:00?", then keep only restatements that survive.
- **Constrained decoding on the local weights.** A grammar would remove the need for the lenient reader.
- **Tune only on held-out pools** written by different people: the vote threshold and the normalizer vocabulary.

## 6. If people, not a template, wrote the notes

The extraction carries over only partly. Granite gets 97% of statements right on the visible wording and 94% on pool A, but 80% on pool C, where impersonal hedges are read as conditions. What breaks first:

- **The scaffolding.** Real notes put two claims in one sentence, use pronouns, write corrections ("scratch that"), and use hedges no list anticipates.
- **The asymmetric vote.** It assumes padding is obviously irrelevant. Near-miss distractors ("Meera *asked* for intake") would make inventions common.

The fix is structural: have the model split sentences into claims, resolve references against the rota, and let the solver's conflicting sets drive re-reading of exactly the statements an answer depends on.

---

# How to run
```
./run <items.json> --budget <1x|3x|10x> --out <answers.json>
```

- **Python 3.13** (3.13.9 tested; uses only the standard library plus `openai` and `httpx`).
- `pip install -r requirements.txt` (pins `openai==3.7.0`, `httpx==0.28.1`). `./run` uses `$PYTHON` if it is set. Otherwise it uses the first `python3` it finds that can import `openai`, and if there is none it prints the install command.
- Credentials come from a `.env` holding `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` and `MODEL`. It is looked up in the current directory, this directory and its parent. Environment variables of the same names override it. **`.env` is not part of the submission.**
- Every call goes to `ibm-granite/granite-4.2-8b` with `temperature=1.0`, `top_p=0.95`, `extra_body={"reasoning": {"enabled": False}}` and an `X-Item-Id` header ([rota/model.py](rota/model.py)).
- Budget: `1x` makes exactly one call per item. `3x` and `10x` make exactly 3 and 10. A call is counted *before* it is sent and the client's own retries are off, so a failed request still uses up budget, just as it does at a counting proxy. No item is ever answered without a call. The one exception to no-retry is a connection that never opened (connection refused, DNS failure). That carried no request, so it is retried, with backoff, without spending budget.
- Optional flags: `--trace <file>` writes per-item diagnostics (translations, vote agreement, solution count, chosen core). `--workers N` sets concurrency (default 12). `--set key=value` switches a component off for ablations.

The ablation table is in the appendix below and is re-run by:

```
python3 ablate.py <items.json> <key.json> --runs 2 --budgets 1x,3x,10x
```

## How it works

```
item text ─┬─ header (symbolic): people, blocks, stations, who holds a station
           └─ statements ─ normalize (strip hedges / "Worth repeating:") ─ drop lines naming nothing
                │
                ▼  one call = all statements of the item
        Granite: restate each statement in controlled English
        "12: <statement copied> => Meera is between Tomas and Rohan"
                │
                ▼  symbolic, per statement
        read the restatement → constraint (or "nothing"); realign by the copied text;
        reject if it names a person/station/time the statement does not
                │
                ▼  3x / 10x: one restatement per sample, combined per statement by an
                │  asymmetric vote, re-voted if the outcome is impossible
        solver: enumerate all 720 worlds, AND the constraint bitmasks
                1 world → unique, 2+ → ambiguous (all of them),
                0 → inconsistent: smallest minimal conflicting set of statements,
                    cited verbatim from the original lines
```

| file | role |
|---|---|
| [rota/header.py](rota/header.py) | parse the header (the domain, not the constraints) |
| [rota/normalize.py](rota/normalize.py) | strip hedges and restatement lead-ins before the model sees a line |
| [rota/prompt.py](rota/prompt.py) | the extraction prompt (controlled English; positional DSL kept for the ablation) |
| [rota/dsl.py](rota/dsl.py) | constraint language, controlled-English reader, world enumeration and semantics |
| [rota/solver.py](rota/solver.py) | solution set, minimal conflicting sets, case decision |
| [rota/pipeline.py](rota/pipeline.py) | one item end to end: sampling, output parsing, grounding, vote, repair |
| [rota/model.py](rota/model.py) | client, per-item budget, `X-Item-Id` |
| [rota/direct.py](rota/direct.py) | ablation arm only: the model answers directly, no solver |
| [ablate.py](ablate.py) | the ablation table |
| [checks/](checks/) | pre-submission checks: counting proxy, per-item budget report, format, model dependence |
| [dev/](dev/) | **development only, never on the answering path**: a template oracle for the visible phrasings, per-statement diagnostics, the reworded test set generator |

## Checks before sending

```
checks/preflight.sh ../items.json 1x 3x 10x
```

This runs the entrypoint through a local counting proxy ([checks/count_proxy.py](checks/count_proxy.py)). It checks that every item got at least one call and no more than its cap, that every call carried `X-Item-Id` and the required sampling settings, and that the output parses. It then re-runs 1x with every model completion perturbed (`ROTA_CORRUPT_MODEL=1` rotates the translations between lines) and counts how many answers change.

---

# Appendix: ablations and runs

## Ablation tables

Each arm is the full system with one component switched off, run through `./run` with `--set` and scored with `score.py`. "=full" means the component does nothing at that budget. Values are macro exact match in %, the mean of n runs. Re-run with `python3 ablate.py <items> <key> --runs N`; `python3 ablation/build_tables.py` merges the per-budget results. Every run in these tables had zero failed requests, apart from one 1x run of `no_ground` with a single failed request. Runs with failed requests are repeated automatically. The tables were measured before one robustness change to `rota/model.py`: a connection that never opened is now retried, because it carried no request and costs no budget. That change cannot alter an answer that got a reply, and the final budget and model-dependence checks (`checks/preflight.log`) were run on the shipped code. `ablate.py` needs the package's `score.py` next to the key or one directory up. "–" means the arm was not run at that budget, a cut made to fit the time.

**How to read it.** At 1x (three runs per arm), the clear contributors are controlled English (−45 points without it), the echo (−24), the lenient output reader (−9) and hedge stripping (−3). On the reworded set, hedge stripping is worth −13 and the lenient reader −9, which is where they were meant to matter. Realignment, grounding, the prefilter, dedupe and the smallest-conflict preference are each worth 1 to 3 points at 1x. That is inside run-to-run noise (about ±4) at n=3, so they are kept as cheap insurance, not as proven gains. At 3x and 10x, with one run per arm, only differences above about 5 points mean anything. Those are the vote (−10 at 10x without it), controlled English and the echo.

**Visible set**

| arm | what changes | 1x | 3x | 10x |
|---|---|---|---|---|
| full | full system | 87.8 (n=3) | 93.3 (n=1) | 91.7 (n=1) |
| no_ce | positional DSL instead of controlled English | 42.8 (n=3) | 43.3 (n=1) | 50.0 (n=1) |
| no_echo | controlled English without echoing the statement | 63.9 (n=3) | 76.7 (n=1) | – |
| no_normalize | hedges / restatement lead-ins sent to the model | 84.4 (n=3) | 91.7 (n=1) | 93.3 (n=1) |
| no_realign | trust the model's line numbers, ignore the echo | 85.6 (n=3) | 88.3 (n=1) | – |
| no_ground | accept translations naming things the statement does not | 86.7 (n=3) | 86.7 (n=1) | 91.7 (n=1) |
| no_lenient | read only the listed output forms (no or/and, no 'one of') | 78.9 (n=3) | 88.3 (n=1) | 90.0 (n=1) |
| no_prefilter | send statements that name no person/block/station | 86.7 (n=3) | 93.3 (n=1) | – |
| no_dedupe | send restated statements twice | 86.7 (n=3) | 91.7 (n=1) | – |
| no_min_core | cite the smallest conflict even if implausibly small | 85.0 (n=3) | 85.0 (n=1) | – |
| no_solver | model answers the item directly; no symbolic solver | 0.0 (n=3) | 0.0 (n=1) | 0.0 (n=1) |
| plural_vote | plain plurality vote instead of asymmetric | =full | 93.3 (n=1) | 91.7 (n=1) |
| no_vote | use only the last sample | =full | 88.3 (n=1) | 78.3 (n=1) |
| no_repair | no re-vote when the outcome is impossible | =full | 86.7 (n=1) | 90.0 (n=1) |

**Reworded set** ([dev/paraphrase.py](dev/paraphrase.py), seed 7; [ablation/reworded_items.json](ablation/reworded_items.json))

| arm | what changes | 1x | 3x | 10x |
|---|---|---|---|---|
| full | full system | 76.7 (n=2) | 88.3 (n=1) | 90.0 (n=1) |
| no_normalize | hedges / restatement lead-ins sent to the model | 63.3 (n=2) | – | – |
| no_lenient | read only the listed output forms (no or/and, no 'one of') | 67.5 (n=2) | – | – |

**Case handling, full system** (rows: true kind; columns: declared kind; summed over runs)

| 1x (n=3 runs) true \ declared | unique | ambiguous | inconsistent |
|---|---|---|---|
| unique | 55 | 5 | 0 |
| ambiguous | 0 | 57 | 3 |
| inconsistent | 3 | 7 | 50 |

| 3x (n=1 runs) true \ declared | unique | ambiguous | inconsistent |
|---|---|---|---|
| unique | 20 | 0 | 0 |
| ambiguous | 0 | 18 | 2 |
| inconsistent | 1 | 1 | 18 |

| 10x (n=1 runs) true \ declared | unique | ambiguous | inconsistent |
|---|---|---|---|
| unique | 19 | 1 | 0 |
| ambiguous | 0 | 18 | 2 |
| inconsistent | 1 | 1 | 18 |



**Harder reworded pools (1x, full system, frozen version).** Pool B (written after A): 63.3, 55.0, 60.0, 46.7, 46.7, 53.3 over six runs, mean 54.2. Pool C (written after B): 30.0, 25.0, 28.3, mean 27.8. Pool D (written last): 36.7, one run. On pools C and D most misses come from hedges with no first-person word ("Unless the sheet is wrong, …", "Don't quote me, but …"): the model labels the claim hypothetical or unsettled.
