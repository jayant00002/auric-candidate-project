"""DEV ONLY: per-statement accuracy by SEMANTICS (bitmask equality), for the
visible set or the reworded set.  usage: stmt_acc.py <orig items> <items used> <trace>"""
import json, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rota import header, dsl, normalize, pipeline
from dev import oracle
orig = {i['id']: i for i in json.load(open(sys.argv[1]))}
used = {i['id']: i for i in json.load(open(sys.argv[2]))}
tr = json.load(open(sys.argv[3]))
k = collections.Counter()
for iid, info in tr.items():
    ol = orig[iid]['text'].split('\n')[2:]; nl = used[iid]['text'].split('\n')[2:]
    truth = {n: oracle.translate(o) for o, n in zip(ol, nl)}
    dom = dsl.Domain(header.parse(used[iid]['text']))
    lines = info['lines']; sent = [normalize.clean(l) for l in lines]
    samples = [pipeline.parse_output(dom, e.get('out'), sent) for e in info['log']]
    choice, _ = pipeline.vote(samples, len(lines), 'asym')
    for l, got in zip(lines, choice):
        w = dom.parse(truth[l])
        if w == 'NONE' and got == 'NONE': k['ok'] += 1
        elif w == 'NONE': k['invented'] += 1
        elif got == 'NONE': k['missed'] += 1
        elif dom.mask(w) == dom.mask(got): k['ok'] += 1
        else: k['wrong'] += 1
n = sum(k.values())
print(f"statements {n}: correct {k['ok']/n:.3f}  missed {k['missed']}  invented {k['invented']}  wrong {k['wrong']}")
