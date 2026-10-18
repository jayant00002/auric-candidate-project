VISIBLE
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

REWORDED
| arm | what changes | 1x | 3x | 10x |
|---|---|---|---|---|
| full | full system | 76.7 (n=2) | 88.3 (n=1) | 90.0 (n=1) |
| no_normalize | hedges / restatement lead-ins sent to the model | 63.3 (n=2) | – | – |
| no_lenient | read only the listed output forms (no or/and, no 'one of') | 67.5 (n=2) | – | – |

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
