"""Generic report: Avg Precision / Accuracy / Avg Recall per dataset and level, Δ Avg Recall vs a baseline (bearing bootstrap)."""
import json
import numpy as np
import cross_rf50 as X


def metrics(sub, a, C):
    m = np.zeros((5, 5))
    for r in sub:
        for p in r['scores'][a]: m[r['label'], p] += 1
    return (float(np.mean([m[c, c] / m[:, c].sum() if m[:, c].sum() else 0. for c in C])), float(np.trace(m) / m.sum()),
            float(np.mean([m[c, c] / m[c].sum() for c in C])), [float(m[c, c] / m[c].sum()) for c in C])


def report(out, datasets, title, base='hier', B=500):
    rows = [json.loads(p.read_text()) for p in sorted((out / 'tasks').glob('*.json'))]; arms = list(rows[0]['scores'])
    rng = np.random.default_rng(13); L = [f'# {title}', '']; summ = {}
    for ds in datasets:
        C = X.CLS[ds]; L += [f'## {ds}', '', '| m | Nhánh | Avg Precision | Accuracy | Avg Recall | Recall từng lớp | ΔRecall so với ' + base + ' (CI 95%) |', '|---:|---|---:|---:|---:|---|---|']
        for m in X.BUD[ds] + (('TB',) if len(X.BUD[ds]) > 1 else ()):
            sub = [r for r in rows if r['ds'] == ds and (m == 'TB' or r['budget'] == m)]
            if not sub: continue
            tg = sorted({r['target'] for r in sub}); lab = {r['target']: r['label'] for r in sub}
            G = {c: [t for t in tg if lab[t] == c] for c in C}; by = {t: [r for r in sub if r['target'] == t] for t in tg}
            bs = {a: [] for a in arms}
            for _ in range(B):
                s2 = [r for c in C for i in rng.integers(len(G[c]), size=len(G[c])) for r in by[G[c][i]]]; h = metrics(s2, base, C)[2]
                for a in arms: bs[a].append(metrics(s2, a, C)[2] - h)
            h = metrics(sub, base, C)
            for a in arms:
                p, acc, rc, cl = metrics(sub, a, C); d = rc - h[2]; lo, hi = np.percentile(bs[a], [2.5, 97.5])
                summ.setdefault(ds, {}).setdefault(str(m), {})[a] = dict(d=d, lo=float(lo), hi=float(hi), cls=cl, hcls=h[3])
                L.append(f'| {m} | {a} | {p*100:.1f} | {acc*100:.1f} | {rc*100:.1f} | ' + ' / '.join(f'{x*100:.1f}' for x in cl) + ('' if a == base else f' | {d*100:+.1f} [{lo*100:+.1f}; {hi*100:+.1f}]') + ' |')
        L.append('')
    (out / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); (out / 'summary.json').write_text(json.dumps(summ)); print('\n'.join(L))
    return summ
