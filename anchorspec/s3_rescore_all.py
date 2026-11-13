"""Post-hoc (12/11): every method scored exactly like S3 (XJTU LOBO, healthy[5:] + terminal windows, 4 classes incl. healthy,
selective policy, pooled confusion; Avg Precision = mean per-class precision with 0 for never-predicted classes)."""
import os, sys, json
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from sklearn.ensemble import RandomForestClassifier as _RFC
import invariant_classifier as IC
from event_experts import causal_average
from t_readiness import selective
from s_additive import additive_training
from u_natural import LABEL, bearing
from m_dev import Model
import s3_dose as D
import router_common as R
import v4_flow as V

ROOT = R.P.ROOT; DATA = ROOT.parent / 'data'
SEEDS = (11, 29, 47)
CL = (0, 1, 2, 4)


def rf_arms(target, seed, trees):
    IC.RandomForestClassifier = lambda **kw: _RFC(**{**kw, 'n_estimators': trees})
    t = bearing(target); src = [n for n in LABEL if n != target]
    ev = [(n, LABEL[n], bearing(n)['terminal_features']) for n in src]
    with np.load(DATA / 's_generation' / f'{target}_{seed}' / 'waveforms.npz') as z: di = z['duplicate_indices']
    dup = {n: {'duplicate': bearing(n)['terminal_features'][di[i*20:(i+1)*20] - i*10]} for i, n in enumerate(src)}
    with np.load(DATA / 's3_generation' / f'{target}_{seed}' / 'features.npz') as f: fl = {n: {'flow': f[n + ':spectral_flow_half']} for n in src}
    h = t['healthy_features'][:5]; out = {}
    for a, (d, m) in {'real': ({}, 'real'), 'photocopy': (dup, 'duplicate'), 'flow_s3': (fl, 'flow')}.items():
        mdl = IC.InvariantClassifier('rf', seed).fit(*additive_training(h, ev, d, m, 1., .25)[:3])
        out[f'{a}_rf{trees}'] = {st: selective(causal_average(mdl.predict_proba(x)), 0).tolist()
                                 for st, x in (('healthy', t['healthy_features'][5:]), ('terminal', t['terminal_features']))}
    return out


def et_probs(arm, target, seed, base, inj, lib, X, cache):
    """Two-stage family (v4 code path) returning 5-column probabilities."""
    ring, gen, weighting, per = V.ARMS[arm]; nolaw = {}
    for c in V.NOLAW:
        keys = lib.get(c, [])
        if gen is None or not keys:
            continue
        pairs, strength = gen
        if ('flow', c, pairs) not in cache:
            cache[('flow', c, pairs)] = V.ClassFlow('xjtu', keys, pairs, seed)
        nolaw[c] = cache[('flow', c, pairs)].rows(per, strength)
    b1 = R.mix_or_add(base, nolaw, .25) if weighting == 'share' and nolaw else base
    if weighting == 'add':
        b1 = V.add_rows(b1, nolaw)
    xb, yb, wb = b1[:3]; ring_m = np.isin(yb, (1, 2))
    m1 = Model('et500', seed).fit(xb, np.where(ring_m, 1, yb), np.where(ring_m, wb * .5, wb))
    x2, y2, w2 = R.mix_or_add(base, inj[0], .25) if arm != 'two_stage_real' else base; keep = np.isin(y2, (1, 2))
    m2 = Model('et500', seed).fit(x2[keep], y2[keep], w2[keep])
    p1, p2 = m1.predict_proba(X), m2.predict_proba(X)
    p = p1.copy(); p[:, 1], p[:, 2] = p1[:, 1] * p2[:, 1], p1[:, 1] * p2[:, 2]
    return p


V.ARMS['two_stage_real'] = (None, None, None, 0)
V.ARMS['flow_within_03'] = (None, ('within', .3), 'share', 20)
ET_ARMS = ('two_stage_real', 'hier', 'flow_within_03', 'flow_truong')


def job(task):
    target, seed = task
    out = rf_arms(target, seed, 50); out.update(rf_arms(target, seed, 500))
    lib = R.library('xjtu', target, seed, 0, (1, 2, 4)); base, _ = R.real_base('xjtu', target, seed, lib); inj = R.injected('xjtu', target, seed)
    hold = D.item('xjtu', target)['hold']; term = R.xjtu(target)['test_f']; cache = {}
    for a in ET_ARMS:
        out[a] = {st: selective(causal_average(et_probs(a, target, seed, base, inj, lib, x, cache)), 0).tolist()
                  for st, x in (('healthy', hold), ('terminal', term))}
    return dict(target=target, seed=seed, label=LABEL[target], scores=out)


def metrics(rows, a):
    m = np.zeros((6, 6)); L = [-1, 0, 1, 2, 3, 4]
    for r in rows:
        for st in ('healthy', 'terminal'):
            tr = 0 if st == 'healthy' else r['label']
            for p in r['scores'][a][st]: m[L.index(tr), L.index(p)] += 1
    pr = [m[L.index(c), L.index(c)] / m[:, L.index(c)].sum() if m[:, L.index(c)].sum() else 0. for c in CL]
    rc = [m[L.index(c), L.index(c)] / m[L.index(c)].sum() for c in CL]
    return float(np.mean(pr)), float(np.trace(m) / m.sum()), float(np.mean(rc)), pr, rc


if __name__ == '__main__':
    tasks = [(t, s) for t in LABEL for s in SEEDS]
    with ProcessPoolExecutor(14) as ex: rows = list(ex.map(job, tasks))
    out = ROOT / 'results' / 's3_rescore'; out.mkdir(exist_ok=True); json.dump(rows, open(out / 'rows.json', 'w'))
    names = [('real_rf50', 'Chỉ dữ liệu thật, RF 50 (mốc S3)'), ('photocopy_rf50', 'Thật + photocopy, RF 50'), ('flow_s3_rf50', 'Thật + Flow S3 (Trường), RF 50'),
             ('real_rf500', 'Chỉ dữ liệu thật, RF 500'), ('photocopy_rf500', 'Thật + photocopy, RF 500'), ('flow_s3_rf500', 'Thật + Flow S3, RF 500'),
             ('two_stage_real', 'Hai tầng ET, không sinh'), ('hier', 'hier (chốt): vật lý tầng 2'), ('flow_within_03', 'hier + Flow within 0,3 (bi/cách)'),
             ('flow_truong', 'hier + công thức Trường (bi/cách)')]
    L = ['# Mọi phương pháp chấm đúng như S3 (XJTU, 13 ổ, seed 11/29/47, khỏe + cuối đời, 4 lớp có "khỏe")', '',
         '| Phương pháp | Avg Precision | Accuracy | Avg Recall | Precision khỏe / trong / ngoài / cách | Recall khỏe / trong / ngoài / cách |', '|---|---:|---:|---:|---|---|']
    for a, n in names:
        p, acc, rc, pr, rcl = metrics(rows, a)
        L.append(f'| {n} | {p*100:.1f} | {acc*100:.1f} | {rc*100:.1f} | ' + ' / '.join(f'{x*100:.0f}' for x in pr) + ' | ' + ' / '.join(f'{x*100:.0f}' for x in rcl) + ' |')
    (out / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))
