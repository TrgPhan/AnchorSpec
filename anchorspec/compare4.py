"""Post-hoc (12/11): four-way comparison on the same tasks as FUSION (8 seeds, Paderborn + HUST):
real only (RF 500) | real + Flow (Truong recipe 1:1, +0.25, RF 500) | injection only (0 real events) |
real + injection (two-stage, locked) | real + injection + Flow (f_neo). Reuses results/fusion for real, hier, f_neo."""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from s_additive import additive_training
from event_experts import causal_average
from diagnostic_experts import fault_labels
from s3_spectral import SpectralResidual, ResidualGenerator
import funnel as Fu
import pb_common as P
import m_hier as MH
import fusion as FU
from m_dev import Model, inj_only

OUT = P.ROOT / 'results' / 'compare4'


def real_flow(H_base, events, ev_waves, ev_fr, rms_log, feat, seed, test):
    names = [n for n, _, _ in events]; lab = {n: c for n, c, _ in events}
    counts = Counter(lab.values()); onehot = {c: i for i, c in enumerate(sorted({1, 2} | set(counts)))}
    k = len(ev_waves[names[0]])
    waves = np.concatenate([ev_waves[n] for n in names]); groups = np.repeat(np.arange(len(names)), k)
    cond = np.concatenate([[np.r_[np.eye(3)[onehot[lab[n]]], ev_fr[n], rms_log]] * k for n in names])
    wts = np.repeat([1 / counts[lab[n]] for n in names], k)
    codec = SpectralResidual().fit(waves, groups, cond)
    gen = ResidualGenerator('flow', seed).fit(codec.z, codec.conditions[codec.pairs[:, 0]], wts[codec.pairs[:, 0]])
    peak = np.repeat([np.abs(ev_waves[n]).max() for n in names], k)
    g, _ = codec.apply(waves, gen.sample(codec.conditions, seed + 20261106) * codec.scale, FU.STRENGTH, peak)
    rows = {n: feat(g[j * k:(j + 1) * k], n) for j, n in enumerate(names)}
    b = additive_training(H_base, events, {n: {'flow': rows[n]} for n in names}, 'flow', 1., .25)[:3]
    return fault_labels(causal_average(Model('rf500', seed).fit(*b).predict_proba(test))).tolist()


def job(task):
    ds = task[0]
    if ds == 'pb':
        target, seed, m = task[1:]
        t = P.item(target); H = P.item(P.healthy_for(target, seed))
        donors = P.pick(P.INNER_REAL, target, seed, 1, m) + P.pick(P.OUTER_REAL, target, seed, 2, m)
        events = [(n, P.item(n)['label'], P.item(n)['donor']) for n in donors]
        rng = np.random.default_rng([seed, sum(map(ord, H['code'])), 31])
        inj = {c: Fu.feats(Fu.injected(H['donor_w'][:, None, :], k, 150, P.FR, P.ORDERS, P.SENSORS['1k'], 4000, rng), 4000, P.FR, P.ORDERS) for c, k in ((1, 'inner'), (2, 'outer'))}
        rf = real_flow(H['base'], events, {n: P.item(n)['donor_w'] for n in donors}, {n: P.FR for n in donors}, float(np.log(P.rig_rms())),
                       lambda x, n: Fu.feats(x[:, None, :], 4000, P.FR, P.ORDERS), seed, t['test'])
        tid, label = target, t['label']
    else:
        cls, size, seed, m = task[1:]
        t = MH.hust_item(cls, size); H = MH.hust_item('N', size); donors = []
        for c in 'IOB':
            pool = sorted(s for s in (4, 5, 6, 7, 8) if not (c == 'B' and s == 4) and (c, s) != (cls, size))
            donors += [(c, int(s)) for s in np.random.default_rng([seed, MH.CODE[c], 20261112]).permutation(pool)[:m]]
        events = [(f'{c}{s}', MH.CODE[c], MH.hust_item(c, s)['donor']) for c, s in donors]
        rng = np.random.default_rng([seed, size, 31])
        inj = {c: Fu.feats(Fu.injected(H['base_w'], k, 150, H['fr0'], H['orders'], MH.SENSOR, 4000, rng), 4000, H['fr0'], H['orders']) for c, k in ((1, 'inner'), (2, 'outer'))}
        dw = {f'{c}{s}': FU.hust_donor_w(c, s) for c, s in donors}; orders = {f'{c}{s}': MH.hust_item(c, s)['orders'] for c, s in donors}
        feat = lambda x, n: np.concatenate([Fu.feats(x[i:i + 1, None, :], 4000, dw[n][1][i], orders[n]) for i in range(len(x))])
        rf = real_flow(H['base'], events, {n: v[0] for n, v in dw.items()}, {n: float(np.mean(v[1])) for n, v in dw.items()},
                       float(np.log(np.sqrt(np.mean(H['base_w'] ** 2)))), feat, seed, t['test'])
        tid, label = f'{cls}{size}', t['label']
    io = fault_labels(causal_average(Model('rf500', seed).fit(*inj_only(H['base'], inj)).predict_proba(t['test']))).tolist()
    return dict(ds=ds, target=tid, seed=task[-2], budget=task[-1], label=label, scores={'real_flow': rf, 'inj_only': io})


if __name__ == '__main__':
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    todo = [('pb', t, s, m) for m in (1, 2, 4) for t in P.REAL for s in FU.SEEDS] + \
           [('hust', c, z, s, m) for m in (1, 2, 3) for c, z in MH.hust_targets() for s in FU.SEEDS]
    name = lambda t: f'{t[0]}_{"_".join(map(str, t[1:]))}.json'
    todo = [t for t in todo if not (OUT / 'tasks' / name(t)).exists()]
    with ProcessPoolExecutor(14) as pool:
        for t, row in zip(todo, pool.map(job, todo)):
            (OUT / 'tasks' / name(t)).write_text(json.dumps(row))
    print('done')
