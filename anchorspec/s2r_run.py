"""S2R dev/val runner.  python s2r_run.py dev|val"""
import os, sys, json
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from event_experts import causal_average
from diagnostic_experts import fault_labels
from m_dev import Model
import router_common as R
import cross_rf50 as X
import s2r as S
from v5_fg import mix_multi
import gen_report as GR

PHASE = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ('dev', 'val') else 'dev'; OUT = R.P.ROOT / 'results' / f's2r_{PHASE}'
X.CLS['pba'] = (1, 2); X.BUD['pba'] = (1, 2)
DS = ('pba', 'uored', 'xjtu') if PHASE == 'dev' else ('pb', 'hust')
ARMS = ('hier', 's2r_rep', 's2r_mix', 'ctrl_rep', 'ctrl_mix')


def targets(ds):
    return [k for v in R.PBA_IDS.values() for k in v] if ds == 'pba' else X.targets(ds)


def two_stage(base, t2rows, t2shares, seed, test):
    xb, yb, wb = base; ring = np.isin(yb, (1, 2))
    m1 = Model('et500', seed).fit(xb, np.where(ring, 1, yb), np.where(ring, wb * .5, wb))
    xs, ys, ws = [xb], [yb], [wb.copy()]; scale = len(xb) / (1 + len([c for c in np.unique(yb) if c > 0]))
    for c in (1, 2):
        tot = sum(sh for (cc, _), sh in zip(t2rows, t2shares) if cc == c); ws[0][yb == c] *= (1 - tot)
    for (c, a), sh in zip(t2rows, t2shares):
        xs.append(a); ys.append(np.full(len(a), c, int)); ws.append(np.full(len(a), sh * scale / len(a)))
    x2, y2, w2 = np.concatenate(xs), np.concatenate(ys), np.concatenate(ws); keep = np.isin(y2, (1, 2))
    m2 = Model('et500', seed).fit(x2[keep], y2[keep], w2[keep])
    p1, p2 = m1.predict_proba(test), m2.predict_proba(test)
    p = p1.copy(); p[:, 1], p[:, 2] = p1[:, 1] * p2[:, 1], p1[:, 1] * p2[:, 2]
    return fault_labels(causal_average(p)).tolist()


def job(task):
    ds, tg, s, m = task
    lib = R.library(ds, tg, s, m, X.CLS[ds]); test = R.record(ds, tg)['test_f']
    base, _ = R.real_base(ds, tg, s, lib); inj_f = R.injected(ds, tg, s)[0]
    rows, ctrl = S.s2r_rows(ds, tg, s, lib, inj_f)
    P = [(1, inj_f[1]), (2, inj_f[2])]
    cfg = {'hier': (P, (.25, .25)),
           's2r_rep': ([(1, rows[1]), (2, rows[2])], (.25, .25)),
           's2r_mix': (P + [(1, rows[1]), (2, rows[2])], (.125, .125, .125, .125)),
           'ctrl_rep': ([(1, ctrl[1]), (2, ctrl[2])], (.25, .25)),
           'ctrl_mix': (P + [(1, ctrl[1]), (2, ctrl[2])], (.125, .125, .125, .125))}
    sc = {a: two_stage(base, r, sh, s, test) for a, (r, sh) in cfg.items()}
    return task, dict(ds=ds, target=X.name(task)[len(ds) + 1:].rsplit('_', 2)[0], seed=s, budget=m, label=R.record(ds, tg)['label'], scores=sc)


if __name__ == '__main__':
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    todo = [(ds, t, s, m) for ds in DS for m in X.BUD[ds] for t in targets(ds) for s in R.SEEDS]
    todo = [t for t in todo if not (OUT / 'tasks' / X.name(t)).exists()]
    with ProcessPoolExecutor(14) as ex:
        for f in as_completed([ex.submit(job, t) for t in todo]):
            t, row = f.result(); (OUT / 'tasks' / X.name(t)).write_text(json.dumps(row))
    GR.report(OUT, DS, f"S2R-{PHASE.upper()}")
