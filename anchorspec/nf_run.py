"""NF dev/val runner.  python nf_run.py dev|val"""
import os, sys, json
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
from concurrent.futures import ProcessPoolExecutor, as_completed
import router_common as R
import cross_rf50 as X
import flowfeat as F
import normflow as NF
import gen_report as GR

PHASE = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ('dev', 'val') else 'dev'; OUT = R.P.ROOT / 'results' / f'nf_{PHASE}'
X.CLS['pba'] = (1, 2); X.BUD['pba'] = (1, 2)
DS = ('pba', 'uored', 'xjtu') if PHASE == 'dev' else ('pb', 'hust')


def targets(ds):
    return [k for v in R.PBA_IDS.values() for k in v] if ds == 'pba' else X.targets(ds)


def job(task):
    ds, tg, s, m = task
    lib = R.library(ds, tg, s, m, X.CLS[ds]); test = R.record(ds, tg)['test_f']
    base, _ = R.real_base(ds, tg, s, lib); inj = R.injected(ds, tg, s)
    sc = {'hier': F.predict('hier', ds, tg, s, lib, base, inj, test, None)} if False else {}
    import v4_flow as V
    sc['hier'] = V.predict_arm('hier', ds, tg, s, lib, base, inj, test, {})
    sc.update(NF.arms(ds, tg, s, lib, inj[0], test))
    return task, dict(ds=ds, target=X.name(task)[len(ds) + 1:].rsplit('_', 2)[0], seed=s, budget=m, label=R.record(ds, tg)['label'], scores=sc)


if __name__ == '__main__':
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    todo = [(ds, t, s, m) for ds in DS for m in X.BUD[ds] for t in targets(ds) for s in R.SEEDS]
    todo = [t for t in todo if not (OUT / 'tasks' / X.name(t)).exists()]
    with ProcessPoolExecutor(14) as ex:
        for f in as_completed([ex.submit(job, t) for t in todo]):
            t, row = f.result(); (OUT / 'tasks' / X.name(t)).write_text(json.dumps(row))
    GR.report(OUT, DS, f'NF-{PHASE.upper()}')
