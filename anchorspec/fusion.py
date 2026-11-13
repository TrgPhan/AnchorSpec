"""FUSION (PROTOCOL_FUSION.md): keep Flow in the pipeline next to the locked two-stage + physics-injection architecture.
    python fusion.py --workers 14            # Paderborn + HUST, 8 seeds
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import hashlib
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import numpy as np
from u_natural import training
from s_additive import additive_training
from event_experts import causal_average
from diagnostic_experts import fault_labels
from s3_spectral import SpectralResidual, ResidualGenerator
from cheap_sensor import simulate, windows
import funnel as Fu
import pb_common as P
import m_hier as MH
from m_dev import Model, mix

OUT = P.ROOT / 'results' / 'fusion'
SEEDS = (11, 29, 47, 101, 202, 303, 404, 505)
ARMS = ('real', 'hier', 'f_neo', 'f_t1', 'f_t1_copy', 'f_par')
STRENGTH = .5


def two_stage(base1, base2, inj, seed, x):
    """Same as m_hier.two_stage, but stage 1 and stage 2 may get different real(+extra) training sets."""
    xb, yb, wb = base1
    ring = np.isin(yb, (1, 2))
    m1 = Model('et500', seed).fit(xb, np.where(ring, 1, yb), np.where(ring, wb * .5, wb))
    x2, y2, w2 = mix(base2, inj, .25)
    keep = np.isin(y2, (1, 2))
    m2 = Model('et500', seed).fit(x2[keep], y2[keep], w2[keep])
    p1, p2 = m1.predict_proba(x), m2.predict_proba(x)
    p = p1.copy(); p[:, 1], p[:, 2] = p1[:, 1] * p2[:, 1], p1[:, 1] * p2[:, 2]
    return p


def run_arms(H_base, events, ev_waves, ev_fr, rms_log, inj_w, inj_feats, inj_cond, feat, seed, test):
    """events: [(name, label, feats)], ev_waves: {name: (10, 4000)}, inj_w: {c: (150, 4000)} on target healthy."""
    names = [n for n, _, _ in events]; lab = {n: c for n, c, _ in events}
    counts = Counter(lab.values()); onehot = {c: i for i, c in enumerate(sorted({1, 2} | set(counts)))}
    k = len(ev_waves[names[0]])
    waves = np.concatenate([ev_waves[n] for n in names]); groups = np.repeat(np.arange(len(names)), k)
    cond = np.concatenate([[np.r_[np.eye(3)[onehot[lab[n]]], ev_fr[n], rms_log]] * k for n in names])
    wts = np.repeat([1 / counts[lab[n]] for n in names], k)
    codec = SpectralResidual().fit(waves, groups, cond)
    gen = ResidualGenerator('flow', seed).fit(codec.z, codec.conditions[codec.pairs[:, 0]], wts[codec.pairs[:, 0]])
    peak = np.repeat([np.abs(ev_waves[n]).max() for n in names], k)
    g, _ = codec.apply(waves, gen.sample(codec.conditions, seed + 20261106) * codec.scale, STRENGTH, peak)
    flow_rows = {n: feat(g[j * k:(j + 1) * k], n) for j, n in enumerate(names)}
    base = training(H_base, events, {}, 'real')
    b_flow = additive_training(H_base, events, {n: {'flow': flow_rows[n]} for n in names}, 'flow', 1., .25)[:3]
    b_copy = additive_training(H_base, events, {n: {'duplicate': f} for n, _, f in events}, 'duplicate', 1., .25)[:3]
    # Flow variants around the physics anchors on the target machine
    neo = {}
    for c, aw in inj_w.items():
        cc = np.column_stack((codec.describe(aw), np.repeat([inj_cond(c, onehot)], len(aw), 0)))
        q = codec.condition_scaler.transform(cc).astype(np.float32)
        gw, _ = codec.apply(aw, gen.sample(q, seed + 7) * codec.scale, STRENGTH, np.abs(aw).max(1))
        neo[c] = np.concatenate([inj_feats[c], feat(gw, None)])
    p = {'real': Model('rf500', seed).fit(*base).predict_proba(test),
         'hier': two_stage(base, base, inj_feats, seed, test),
         'f_neo': two_stage(base, base, neo, seed, test),
         'f_t1': two_stage(b_flow, base, inj_feats, seed, test),
         'f_t1_copy': two_stage(b_copy, base, inj_feats, seed, test)}
    p['f_par'] = .5 * p['hier'] + .5 * Model('rf500', seed).fit(*b_flow).predict_proba(test)
    return {a: fault_labels(causal_average(v)).tolist() for a, v in p.items()}


# ---------------- Paderborn ----------------
def pb_job(task):
    target, seed, m = task; start = time.perf_counter()
    t = P.item(target); H = P.item(P.healthy_for(target, seed))
    donors = P.pick(P.INNER_REAL, target, seed, 1, m) + P.pick(P.OUTER_REAL, target, seed, 2, m)
    events = [(n, P.item(n)['label'], P.item(n)['donor']) for n in donors]
    rng = np.random.default_rng([seed, sum(map(ord, H['code'])), 31])
    inj_w, inj_f = {}, {}
    for c, kind in ((1, 'inner'), (2, 'outer')):
        w = Fu.injected(H['donor_w'][:, None, :], kind, 150, P.FR, P.ORDERS, P.SENSORS['1k'], 4000, rng)
        inj_w[c] = w[:, 0, :]; inj_f[c] = Fu.feats(w, 4000, P.FR, P.ORDERS)
    feat = lambda x, n: Fu.feats(x[:, None, :], 4000, P.FR, P.ORDERS)
    rl = float(np.log(P.rig_rms()))
    sc = run_arms(H['base'], events, {n: P.item(n)['donor_w'] for n in donors}, {n: P.FR for n in donors}, rl,
                  inj_w, inj_f, lambda c, oh: np.r_[np.eye(3)[oh[c]], P.FR, rl], feat, seed, t['test'])
    return dict(ds='pb', target=target, seed=seed, budget=m, label=t['label'], scores=sc, elapsed_seconds=time.perf_counter() - start)


# ---------------- HUST ----------------
@lru_cache(maxsize=None)
def hust_donor_w(cls, size):
    """Waveforms of the 10 donor windows of m_hier.hust_item (same simulation and seeds), with their speed."""
    wins, frs = [], []
    for load in (0, 2, 4):
        x, fr = MH.hust_file(f'{cls}{size}0{load}')
        w = windows(simulate(x - x.mean(), 51200, MH.SENSOR, np.random.default_rng([ord(cls), size, load, 7])), 4000)
        wins.append(w); frs += [fr] * len(w)
    allw = np.concatenate(wins); spread = np.linspace(0, len(allw) - 1, 10).round().astype(int)
    return allw[spread], np.asarray(frs)[spread]


def hust_job(task):
    cls, size, seed, m = task; start = time.perf_counter()
    t = MH.hust_item(cls, size); H = MH.hust_item('N', size)
    donors = []
    for c in 'IOB':
        pool = sorted(s for s in (4, 5, 6, 7, 8) if not (c == 'B' and s == 4) and (c, s) != (cls, size))
        donors += [(c, int(s)) for s in np.random.default_rng([seed, MH.CODE[c], 20261112]).permutation(pool)[:m]]
    events = [(f'{c}{s}', MH.CODE[c], MH.hust_item(c, s)['donor']) for c, s in donors]
    rng = np.random.default_rng([seed, size, 31])
    inj_w, inj_f = {}, {}
    for c, kind in ((1, 'inner'), (2, 'outer')):
        w = Fu.injected(H['base_w'], kind, 150, H['fr0'], H['orders'], MH.SENSOR, 4000, rng)
        inj_w[c] = w[:, 0, :]; inj_f[c] = Fu.feats(w, 4000, H['fr0'], H['orders'])
    dw = {f'{c}{s}': hust_donor_w(c, s) for c, s in donors}
    for c, s in donors:   # consistency: rebuilt donor windows reproduce hust_item donor features
        assert np.allclose(np.concatenate([Fu.feats(dw[f'{c}{s}'][0][i:i + 1, None, :], 4000, dw[f'{c}{s}'][1][i], MH.hust_item(c, s)['orders']) for i in range(10)]),
                           MH.hust_item(c, s)['donor'])
    orders = {f'{c}{s}': MH.hust_item(c, s)['orders'] for c, s in donors}

    def feat(x, n):
        if n is None:
            return Fu.feats(x[:, None, :], 4000, H['fr0'], H['orders'])
        return np.concatenate([Fu.feats(x[i:i + 1, None, :], 4000, dw[n][1][i], orders[n]) for i in range(len(x))])
    rl = float(np.log(np.sqrt(np.mean(H['base_w'] ** 2))))
    sc = run_arms(H['base'], events, {n: v[0] for n, v in dw.items()}, {n: float(np.mean(v[1])) for n, v in dw.items()}, rl,
                  inj_w, inj_f, lambda c, oh: np.r_[np.eye(3)[oh[c]], H['fr0'], rl], feat, seed, t['test'])
    return dict(ds='hust', target=f'{cls}{size}', seed=seed, budget=m, label=t['label'], scores=sc, elapsed_seconds=time.perf_counter() - start)


def job(task):
    return pb_job(task[1:]) if task[0] == 'pb' else hust_job(task[1:])


def per_bearing(rows, arm):
    d = {}
    for r in rows:
        d.setdefault(r['target'], []).append(float(np.mean(np.asarray(r['scores'][arm]) == r['label'])))
    return {k: float(np.mean(v)) for k, v in d.items()}


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]
    rng = np.random.default_rng(20261112)
    fmt = lambda c: f"{c['delta']*100:+.1f} [{c['ci95'][0]*100:+.1f}; {c['ci95'][1]*100:+.1f}]"
    L = ['# FUSION: Flow ghép với kiến trúc hai tầng + cấy lỗi (giao thức PROTOCOL_FUSION.md)', '',
         f'{len(rows)} lượt, 8 seed. Chỉ chọn loại lỗi; macro theo lớp; mỗi ổ trung bình trên các seed.', '']
    verdict = {a: dict(keep=True, contrib=False) for a in ('f_neo', 'f_t1', 'f_par')}
    for ds, budgets, classes, name in (('pb', (1, 2, 4), (1, 2), 'Paderborn'), ('hust', (1, 2, 3), (1, 2, 3), 'HUST')):
        L += [f'## {name}', '', '| Sự cố/loại | ' + ' | '.join(ARMS) + ' | f_neo − hier | f_t1 − hier | f_par − hier | f_t1 − f_t1_copy |',
              '|---:|' + '---:|' * len(ARMS) + '---|---|---|---|']
        for m in budgets:
            sub = [r for r in rows if r['ds'] == ds and r['budget'] == m]
            if not sub:
                continue
            lab = {r['target']: r['label'] for r in sub}
            per = {a: per_bearing(sub, a) for a in ARMS}
            cs = {a: P.bootstrap(per[a], per['hier'], lab, rng, classes=classes) for a in ('f_neo', 'f_t1', 'f_par')}
            own = P.bootstrap(per['f_t1'], per['f_t1_copy'], lab, rng, classes=classes)
            L.append(f'| {m} | ' + ' | '.join(f'{P.macro(per[a], lab, classes)*100:.1f}' for a in ARMS) + ' | '
                     + ' | '.join(fmt(cs[a]) for a in ('f_neo', 'f_t1', 'f_par')) + f' | {fmt(own)} |')
            for a, c in cs.items():
                verdict[a]['keep'] &= c['delta'] >= -.01 and c['ci95'][0] > -.03
                verdict[a]['contrib'] |= c['delta'] >= .02 and c['ci95'][0] > 0
        L.append('')
    for a, v in verdict.items():
        v['contrib'] = v['contrib'] and v['keep']
        L.append(f"**{a}:** giữ được: {'ĐẠT' if v['keep'] else 'KHÔNG ĐẠT'}; có đóng góp: {'ĐẠT' if v['contrib'] else 'KHÔNG ĐẠT'}.")
    (OUT / 'summary.json').write_text(json.dumps(verdict, indent=2))
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=14); ap.add_argument('--report', action='store_true')
    ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    h = {n: hashlib.sha256((P.ROOT / n).read_bytes()).hexdigest() for n in ('PROTOCOL_FUSION.md', 'fusion.py', 'm_hier.py', 'm_dev.py', 'pb_common.py')}
    pre = OUT / 'prerun.sha256'
    if a.smoke:
        r1 = pb_job(('KI04', 11, 1)); r2 = hust_job(('I', 5, 11, 1))
        old1 = json.loads((P.ROOT / 'results/pb_hier/tasks/KI04_11_m1.json').read_text())
        old2 = json.loads((P.ROOT / 'results/hier_hust/tasks/I_5_11_1.json').read_text())
        print('PB hier matches PB-HIER:', r1['scores']['hier'] == old1['scores']['hier'], '| real:', r1['scores']['real'] == old1['scores']['real'], round(r1['elapsed_seconds'], 1), 's')
        print('HUST hier matches HIER:', r2['scores']['hier'] == old2['scores']['hier'], '| real:', r2['scores']['real'] == old2['scores']['real'], round(r2['elapsed_seconds'], 1), 's')
        return
    if pre.exists() and json.loads(pre.read_text()) != h: raise ValueError('Frozen sources changed')
    pre.write_text(json.dumps(h, indent=2))
    if not a.report:
        todo = [('pb', t, s, m) for m in (1, 2, 4) for t in P.REAL for s in SEEDS] + \
               [('hust', c, z, s, m) for m in (1, 2, 3) for c, z in MH.hust_targets() for s in SEEDS]
        name = lambda t: f'{t[0]}_{"_".join(map(str, t[1:]))}.json'
        todo = [t for t in todo if not (OUT / 'tasks' / name(t)).exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, (t, row) in enumerate(zip(todo, pool.map(job, todo)), 1):
                (OUT / 'tasks' / name(t)).write_text(json.dumps(row))
                if i % 50 == 0: print('fusion', i, '/', len(todo), flush=True)
    report()


if __name__ == '__main__':
    main()
