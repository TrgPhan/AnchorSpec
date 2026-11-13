"""Extension of cross_rf50.py: same Flow model and same residual draws per task, applied at strengths 0.25/0.3/0.75/1.0
(+0.5 re-computed as a check). Real + Flow within, 1 per real window, +0.25 additive, RF 50."""
import os, json
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import invariant_classifier as IC
from event_experts import causal_average
from diagnostic_experts import fault_labels
import router_common as R
import branch_c as BC
import v4_flow as V
import cross_rf50 as X

STR = (.25, .3, .5, .75, 1.)


def job(task):
    ds, tg, s, m = task
    lib = R.library(ds, tg, s, m, X.CLS[ds]); test = R.record(ds, tg)['test_f']; base, _ = R.real_base(ds, tg, s, lib)
    codec, gen = R.fit_flow(ds, tg, s, lib); rows = {st: {} for st in STR}
    for c, keys in lib.items():
        for k in keys:
            rec = R.record(ds, k); a = np.asarray(rec['donor_w'], float); idx = np.arange(len(a))
            q = codec.condition_scaler.transform(np.column_stack((codec.describe(a), np.repeat([R.codec_cond(c, float(np.mean(rec['donor_fr'])), codec)], len(a), 0))))
            res = gen.sample(q.astype(np.float32), s + 20261106) * codec.scale            # same draw as flow_variants in cross_rf50
            for st in STR:
                w, _ = codec.apply(a, res, st, np.abs(a).max(1))
                rows[st].setdefault(c, []).append(BC._src_feats(rec, w, idx))
    out = {}
    for st in STR:
        xyw = V.add_rows(base, {c: np.concatenate(v) for c, v in rows[st].items()})
        out[f'flow_within_{st}_rf50'] = fault_labels(causal_average(IC.InvariantClassifier('rf', s).fit(*xyw).predict_proba(test))).tolist()
    return task, out


if __name__ == '__main__':
    todo = [(ds, t, s, m) for ds in ('pb', 'hust', 'uored', 'xjtu') for m in X.BUD[ds] for t in X.targets(ds) for s in R.SEEDS]
    same = 0
    with ProcessPoolExecutor(14) as ex:
        for i, f in enumerate(as_completed([ex.submit(job, t) for t in todo]), 1):
            t, out = f.result(); p = X.OUT / 'tasks' / X.name(t); row = json.loads(p.read_text())
            same += out['flow_within_0.5_rf50'] == row['scores']['flow_within_rf50']
            row['scores'].update(out); p.write_text(json.dumps(row))
            if i % 100 == 0: print('strength', i, '/', len(todo), flush=True)
    print('độ mạnh 0,5 tính lại trùng lượt chính:', same, '/', len(todo))
