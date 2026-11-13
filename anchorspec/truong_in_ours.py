"""Post-hoc (12/11): does Truong's flow recipe (1:1, +0.25 weight) add anything on top of our architecture
(ExtraTrees 500 + A0 physics injection mixed at 25%) on Paderborn real damages? Controls: exact copies.
    python truong_in_ours.py --workers 14
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from u_natural import training
from s_additive import additive_training
from s3_spectral import SpectralResidual, ResidualGenerator
import funnel as Fu
import pb_common as P
from m_dev import Model, mix, predict

OUT = P.ROOT / 'results' / 'truong_in_ours'
SEEDS = (11, 29, 47); OFFSETS = (20261106, 1, 2)
ARMS = ('et500', 'et500+flow', 'et500+dup', 'ours', 'ours+flow', 'ours+dup')


def job(task):
    target, seed = task
    t = P.item(target); H = P.item(P.healthy_for(target, seed)); rows = []
    rng = np.random.default_rng([seed, sum(map(ord, H['code'])), 31])
    inj = {c: Fu.feats(Fu.injected(H['donor_w'][:, None, :], k, 150, P.FR, P.ORDERS, P.SENSORS['1k'], 4000, rng), 4000, P.FR, P.ORDERS)
           for c, k in ((1, 'inner'), (2, 'outer'))}
    for m in (1, 2, 4):
        donors = P.pick(P.INNER_REAL, target, seed, 1, m) + P.pick(P.OUTER_REAL, target, seed, 2, m)
        its = [P.item(n) for n in donors]; counts = Counter(i['label'] for i in its); k = len(its[0]['donor_w'])
        events = [(n, i['label'], i['donor']) for n, i in zip(donors, its)]
        waves = np.concatenate([i['donor_w'] for i in its]); groups = np.repeat(np.arange(len(its)), k)
        peak = np.repeat([np.abs(i['donor_w']).max() for i in its], k)
        cond = np.concatenate([[np.r_[np.eye(3)[{1: 0, 2: 1}[i['label']]], i['fr'], np.log(P.rig_rms())]] * k for i in its])
        wts = np.repeat([1 / counts[i['label']] for i in its], k)
        codec = SpectralResidual().fit(waves, groups, cond)
        gen = ResidualGenerator('flow', seed).fit(codec.z, codec.conditions[codec.pairs[:, 0]], wts[codec.pairs[:, 0]])
        fit = lambda xyw: predict(Model('et500', seed).fit(*xyw[:3]), t['test'])
        base = training(H['base'], events, {}, 'real')
        dupb = additive_training(H['base'], events, {n: {'duplicate': i['donor']} for n, i in zip(donors, its)}, 'duplicate', 1., .25)
        sc = {'et500': fit(base), 'et500+dup': fit(dupb), 'ours': fit(mix(base, inj, .25)), 'ours+dup': fit(mix(dupb[:3], inj, .25))}
        for o in OFFSETS:
            res = gen.sample(codec.conditions, seed + o) * codec.scale
            g, _ = codec.apply(waves, res, P.STRENGTH, peak)
            f = Fu.feats(g[:, None, :], its[0]['fs'], P.FR, P.ORDERS, P.SENSORS['1k'].bw_hz)
            fb = additive_training(H['base'], events, {n: {'flow': f[j * k:(j + 1) * k]} for j, n in enumerate(donors)}, 'flow', 1., .25)
            sc[f'et500+flow@{o}'] = fit(fb); sc[f'ours+flow@{o}'] = fit(mix(fb[:3], inj, .25))
        rows.append(dict(target=target, seed=seed, budget=m, label=t['label'], scores=sc))
    return rows


def acc(r, a):
    ks = [x for x in r['scores'] if x == a or x.startswith(a + '@')]
    return float(np.mean([np.mean(np.asarray(r['scores'][x]) == r['label']) for x in ks]))


def report():
    rows = [r for p in sorted((OUT / 'tasks').glob('*.json')) for r in json.loads(p.read_text())]
    lab = {r['target']: r['label'] for r in rows}; rng = np.random.default_rng(20261112)
    comps = (('et500+flow', 'et500'), ('et500+flow', 'et500+dup'), ('ours', 'et500'), ('ours+flow', 'ours'), ('ours+flow', 'ours+dup'))
    L = ['# Flow (công thức Trường) gắn vào kiến trúc của mình, Paderborn hỏng thật (hậu nghiệm, 12/11)', '',
         'ExtraTrees 500 cây, chỉ chọn loại lỗi, macro vòng trong/ngoài. `ours` = cấy lỗi A0 trộn 25%. Flow trung bình 3 hạt giống lấy mẫu.', '',
         '| Sự cố/loại | ' + ' | '.join(ARMS) + ' | ' + ' | '.join(f'{a} − {b}' for a, b in comps) + ' |', '|---:|' + '---:|' * len(ARMS) + '---|' * len(comps)]
    for m in (1, 2, 4):
        per = {a: {} for a in ARMS}
        for r in rows:
            if r['budget'] == m:
                for a in ARMS: per[a].setdefault(r['target'], []).append(acc(r, a))
        per = {a: {n: float(np.mean(v)) for n, v in d.items()} for a, d in per.items()}
        cs = [P.bootstrap(per[a], per[b], lab, rng) for a, b in comps]
        L.append(f'| {m} | ' + ' | '.join(f'{P.macro(per[a], lab) * 100:.1f}' for a in ARMS) + ' | '
                 + ' | '.join(f"{c['delta'] * 100:+.1f} [{c['ci95'][0] * 100:+.1f}; {c['ci95'][1] * 100:+.1f}]" for c in cs) + ' |')
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=14); ap.add_argument('--report', action='store_true'); a = ap.parse_args()
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    if not a.report:
        todo = [(t, s) for t in P.REAL for s in SEEDS if not (OUT / 'tasks' / f'{t}_{s}.json').exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for t, rows in zip(todo, pool.map(job, todo)):
                (OUT / 'tasks' / f'{t[0]}_{t[1]}.json').write_text(json.dumps(rows))
    report()
