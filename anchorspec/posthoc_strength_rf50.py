"""Post-hoc (12/11): S3-style scoring (XJTU LOBO, healthy + terminal, 4 classes, RF 50), real + Flow-within re-applied from
the SAVED S3 residuals at several strengths, additive +0.25 (Truong) and 25% share. Needs results/s3_rescore/rows.json
(from s3_rescore_all.py).   python posthoc_strength_rf50.py 0.5 0.3 0.25 0.2 0.55 0.6 0.52"""
import os, sys, json
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import invariant_classifier as IC
from event_experts import causal_average
from t_readiness import selective
from s_additive import additive_training, training
from u_natural import LABEL, bearing
import m_dev, s3_rescore_all as S
from s3_rescore_within03 import flow_feats

STR = tuple(map(float, sys.argv[1:])) or (.5,)


def job(t):
    tg, s = t; tb = bearing(tg); src = [n for n in LABEL if n != tg]; ev = [(n, LABEL[n], bearing(n)['terminal_features']) for n in src]; h = tb['healthy_features'][:5]
    base = training(h, ev, {}, 'real'); out = {}
    for st in STR:
        f = flow_feats(tg, s, st); rows = {}
        for n, c, _ in ev: rows.setdefault(c, []).append(f[n])
        sets = {f'add_{st}': additive_training(h, ev, {n: {'flow': f[n]} for n in src}, 'flow', 1., .25)[:3],
                f'share_{st}': m_dev.mix(base, {c: np.concatenate(v) for c, v in rows.items()}, .25)}
        for a, xyw in sets.items():
            mdl = IC.InvariantClassifier('rf', s).fit(*xyw)
            out[a] = {k: selective(causal_average(mdl.predict_proba(x)), 0).tolist() for k, x in (('healthy', tb['healthy_features'][5:]), ('terminal', tb['terminal_features']))}
    return dict(target=tg, seed=s, scores=out)


if __name__ == '__main__':
    with ProcessPoolExecutor(14) as ex: new = {(r['target'], r['seed']): r for r in ex.map(job, [(t, s) for t in LABEL for s in S.SEEDS])}
    p = S.ROOT / 'results/s3_rescore/rows.json'; rows = json.load(open(p))
    for r in rows: r['scores'].update(new[(r['target'], r['seed'])]['scores'])
    json.dump(rows, open(p, 'w'))
    for a in ['real_rf50', 'photocopy_rf50', 'flow_s3_rf50'] + [f'{k}_{st}' for st in STR for k in ('add', 'share')]:
        prc, acc, rc, _, rcl = S.metrics(rows, a); print(f'{a:16s} AvgP {prc*100:5.1f} Acc {acc*100:5.1f} AvgR {rc*100:5.1f} cage {rcl[3]*100:4.0f}')
