"""Post-hoc (12/11): two-stage ExtraTrees with NO generated data on UORED (4 classes, m=1,2, 8 seeds).
Writes results/v5_dev/hier_real_uored.json."""
import os, json
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
from concurrent.futures import ProcessPoolExecutor
import router_common as R
from event_experts import causal_average
from diagnostic_experts import fault_labels


def job(t):
    tg, s, m = t; lib = R.library('uored', tg, s, m, (1, 2, 3, 4)); base, _ = R.real_base('uored', tg, s, lib)
    return t, fault_labels(causal_average(R.two_stage(base, {}, {}, s, R.uored(tg)['test_f']))).tolist()


if __name__ == '__main__':
    T = [(tg, s, m) for m in (1, 2) for c in (1, 2, 3, 4) for tg in R.UORED_IDS[c] for s in R.SEEDS]
    with ProcessPoolExecutor(14) as ex: out = {f'{t[0]}_{t[1]}_{t[2]}': v for t, v in ex.map(job, T)}
    json.dump(out, open(R.P.ROOT / 'results/v5_dev/hier_real_uored.json', 'w'))
