"""inj_only (0 real events) on Paderborn, same code path as pb_bw_lib.py (1k), over the 8 PB-HIER seeds. Descriptive, for the figure."""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import funnel as Fu
import pb_common as P
from m_dev import inj_only
from pb_bw_lib import predict
from pb_hier import SEEDS

def job(task):
    target, seed = task; sen = P.SENSORS['1k']
    t = P.item(target); H = P.item(P.healthy_for(target, seed))
    rng = np.random.default_rng([seed, sum(map(ord, target)), 31])
    inj = {c: Fu.feats(Fu.injected(H['donor_w'][:, None, :], k, 150, P.FR, P.ORDERS, sen, sen.fs_out, rng), sen.fs_out, P.FR, P.ORDERS, sen.bw_hz)
           for c, k in ((1, 'inner'), (2, 'outer'))}
    return dict(target=target, seed=seed, label=t['label'], acc=float(np.mean(np.asarray(predict(inj_only(H['base'], inj), seed, t['test'])) == t['label'])))

if __name__ == '__main__':
    todo = [(t, s) for t in P.REAL for s in SEEDS]
    with ProcessPoolExecutor(14) as pool: rows = list(pool.map(job, todo))
    lab = {r['target']: r['label'] for r in rows}
    per = {k: float(np.mean([r['acc'] for r in rows if r['target'] == k])) for k in lab}
    per3 = {k: float(np.mean([r['acc'] for r in rows if r['target'] == k and r['seed'] in SEEDS[:3]])) for k in lab}
    out = dict(macro8=P.macro(per, lab), macro_seeds_11_29_47=P.macro(per3, lab), rows=rows)
    (P.ROOT / 'results/pb_inj_only8/summary.json').write_text(json.dumps(out, indent=1))
    print('8 seed', round(out['macro8'] * 100, 1), '| seed 11/29/47 (phai = 76.9)', round(out['macro_seeds_11_29_47'] * 100, 1))
