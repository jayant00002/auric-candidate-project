| arm | what changes | 1x |
|---|---|---|
| full | full system | 87.8 (n=3) |
| no_ce | positional DSL instead of controlled English | 42.8 (n=3) |
| no_echo | controlled English without echoing the statement | 63.9 (n=3) |
| no_normalize | hedges / restatement lead-ins sent to the model | 84.4 (n=3) |
| no_realign | trust the model's line numbers, ignore the echo | 85.6 (n=3) |
| no_ground | accept translations naming things the statement does not | 86.7 (n=3) |
| no_lenient | read only the listed output forms (no or/and, no 'one of') | 78.9 (n=3) |
| no_prefilter | send statements that name no person/block/station | 86.7 (n=3) |
| no_dedupe | send restated statements twice | 86.7 (n=3) |
| no_min_core | cite the smallest conflict even if implausibly small | 85.0 (n=3) |
| no_solver | model answers the item directly; no symbolic solver | 0.0 (n=3) |
| plural_vote | plain plurality vote instead of asymmetric | =full |
| no_vote | use only the last sample | =full |
| no_repair | no re-vote when the outcome is impossible | =full |
