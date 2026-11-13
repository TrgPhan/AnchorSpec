"""Runner for PROTOCOL_FF.md:  python ff_run.py dev | val"""
import os, sys, json, hashlib
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import router_common as R
import flowfeat as F
import cross_rf50 as X

PHASE = sys.argv[1]; OUT = R.P.ROOT / 'results' / f'ff_{PHASE}'
DS = ('uored', 'xjtu') if PHASE == 'dev' else ('pb', 'hust')
ARMS = list(F.ARMS) if PHASE == 'dev' else None


def job(task):
    ds, tg, s, m = task; arms = ARMS or ['hier', LOCK['arm'], 'bs' + LOCK['arm'][2:]]
    lib = R.library(ds, tg, s, m, X.CLS[ds]); test = R.record(ds, tg)['test_f']
    base, _ = R.real_base(ds, tg, s, lib); inj = R.injected(ds, tg, s); dg = F.DeltaGen(ds, tg, s, lib)
    return task, dict(ds=ds, target=X.name(task)[len(ds) + 1:].rsplit('_', 2)[0], seed=s, budget=m, label=R.record(ds, tg)['label'],
                      scores={a: F.predict(a, ds, tg, s, lib, base, inj, test, dg) for a in arms})


def metrics(sub, a, C):
    m = np.zeros((5, 5))
    for r in sub:
        for p in r['scores'][a]: m[r['label'], p] += 1
    return float(np.mean([m[c, c] / m[:, c].sum() if m[:, c].sum() else 0. for c in C])), float(np.trace(m) / m.sum()), float(np.mean([m[c, c] / m[c].sum() for c in C])), [m[c, c] / m[c].sum() for c in C]


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]; arms = list(rows[0]['scores'])
    rng = np.random.default_rng(13); L = [f'# FF-{PHASE.upper()} (PROTOCOL_FF.md)', '']; summ = {}
    for ds in DS:
        C = X.CLS[ds]; L += [f'## {ds}', '', '| m | Nhánh | Avg Precision | Accuracy | Avg Recall | Recall từng lớp | ΔRecall so với hier (CI 95%) |', '|---:|---|---:|---:|---:|---|---|']
        levels = X.BUD[ds] + (('TB',) if len(X.BUD[ds]) > 1 else ())
        for m in levels:
            sub = [r for r in rows if r['ds'] == ds and (m == 'TB' or r['budget'] == m)]
            tg = sorted({r['target'] for r in sub}); lab = {r['target']: r['label'] for r in sub}
            G = {c: [t for t in tg if lab[t] == c] for c in C}; by = {t: [r for r in sub if r['target'] == t] for t in tg}
            bs = {a: [] for a in arms}
            for _ in range(500):
                s2 = [r for c in C for i in rng.integers(len(G[c]), size=len(G[c])) for r in by[G[c][i]]]; h = metrics(s2, 'hier', C)[2]
                for a in arms: bs[a].append(metrics(s2, a, C)[2] - h)
            h = metrics(sub, 'hier', C)
            for a in arms:
                p, acc, rc, cl = metrics(sub, a, C); d = rc - h[2]; lo, hi = np.percentile(bs[a], [2.5, 97.5])
                summ.setdefault(ds, {}).setdefault(str(m), {})[a] = dict(d=d, lo=float(lo), hi=float(hi), cls=[float(x) for x in cl], hcls=[float(x) for x in h[3]])
                L.append(f'| {m} | {a} | {p*100:.1f} | {acc*100:.1f} | {rc*100:.1f} | ' + ' / '.join(f'{x*100:.1f}' for x in cl) + ('' if a == 'hier' else f' | {d*100:+.1f} [{lo*100:+.1f}; {hi*100:+.1f}]') + ' |')
        L.append('')
    if PHASE == 'dev':
        cand = {}
        for a in arms:
            if not a.startswith('ff'): continue
            key = lambda ds: 'TB' if ds == 'uored' else '0'
            guard = all(min(np.array(summ[ds][key(ds)][a]['cls']) - np.array(summ[ds][key(ds)][a]['hcls'])) >= -.03 for ds in DS)
            md = float(np.mean([summ[ds][key(ds)][a]['d'] for ds in DS]))
            L.append(f'- {a}: trung bình Δ = {md*100:+.2f}, bảo vệ lớp: {"đạt" if guard else "không"}')
            if guard and md > 0: cand[a] = md
        lock = dict(arm=max(cand, key=cand.get) if cand else None)
        L.append(f'\n**Khóa:** {lock}'); (OUT / 'lock.json').write_text(json.dumps(lock))
    else:
        means = {ds: float(np.mean([summ[ds][str(m)][LOCK['arm']]['d'] for m in X.BUD[ds]])) for ds in DS}
        anyci = any(summ[ds][str(m)][LOCK['arm']]['lo'] > 0 for ds in DS for m in X.BUD[ds])
        worst = min(summ[ds][str(m)][LOCK['arm']]['d'] for ds in DS for m in X.BUD[ds])
        win = all(v > 0 for v in means.values()) and anyci and worst >= -.02
        L += [f'- Trung bình Δ theo bộ: ' + ', '.join(f'{k} {v*100:+.2f}' for k, v in means.items()), f'- Có mức CI > 0: {anyci}', f'- Mức tệ nhất: {worst*100:+.2f}', f'\n**{"THẮNG" if win else "CHƯA THẮNG"}**']
        (OUT / 'verdict.json').write_text(json.dumps(dict(win=bool(win), means=means, anyci=bool(anyci), worst=worst)))
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


LOCK = json.loads((R.P.ROOT / 'results/ff_dev/lock.json').read_text()) if PHASE == 'val' else None

if __name__ == '__main__':
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    h = {n: hashlib.sha256((R.P.ROOT / n).read_bytes()).hexdigest() for n in ('PROTOCOL_FF.md', 'flowfeat.py', 'ff_run.py', 'router_common.py')}
    if LOCK: h['lock'] = json.dumps(LOCK)
    pre = OUT / 'prerun.sha256'
    if pre.exists() and json.loads(pre.read_text()) != h: raise ValueError('Frozen sources changed')
    pre.write_text(json.dumps(h, indent=2))
    todo = [(ds, t, s, m) for ds in DS for m in X.BUD[ds] for t in X.targets(ds) for s in R.SEEDS]
    todo = [t for t in todo if not (OUT / 'tasks' / X.name(t)).exists()]
    with ProcessPoolExecutor(14) as ex:
        for i, f in enumerate(as_completed([ex.submit(job, t) for t in todo]), 1):
            t, row = f.result(); (OUT / 'tasks' / X.name(t)).write_text(json.dumps(row))
    report()
