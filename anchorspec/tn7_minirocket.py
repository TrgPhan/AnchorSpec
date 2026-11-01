"""MiniRocket (khám phá, env anchorspec-rocket): cùng cấy lỗi A0 trên 13 ổ XJTU-SY đã mở."""
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import pickle
import sys
import time

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('NUMBA_NUM_THREADS', '1')

import numpy as np  # noqa: E402
from aeon.transformations.collection.convolution_based import MiniRocket  # noqa: E402
from sklearn.linear_model import RidgeClassifierCV  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import tn2b_xjtu as X  # noqa: E402

OUT = ROOT/'results'/'tn7'
KERNELS = 2000


def job(args):
    name, seed = args
    k = X.CLASSES.index(X.LABEL[name])
    full = X.load(name).astype(float)
    base, hold, late = X.split(full)
    rng = np.random.default_rng([seed, int.from_bytes(name.encode(), 'big') % 2**31])
    sets, _ = X.injected_set(base, X.fr_of(name), X.UER204.orders(), X.Prior(), X.FAULTS, X.N_INJECT, rng)
    scale = np.sqrt((base**2).mean(axis=(0, 2), keepdims=True))+1e-9
    train = np.concatenate([base]+[sets[c] for c in X.FAULTS])/scale
    y = np.concatenate([np.zeros(len(base), int)]+[np.full(X.N_INJECT, i+1) for i in range(3)])
    tf = MiniRocket(n_kernels=KERNELS, random_state=seed)
    F = tf.fit_transform(train)
    w = np.where(y == 0, X.N_INJECT/len(base), 1.)
    clf = RidgeClassifierCV(alphas=np.logspace(-3, 3, 7)).fit(F, y, sample_weight=w)
    pred = clf.predict(tf.transform(late/scale))
    hold_pred = clf.predict(tf.transform(hold/scale))
    one = late[:1]/scale
    ts = []
    for _ in range(20):
        t = time.perf_counter()
        clf.predict(tf.transform(one))
        ts.append(1e3*(time.perf_counter()-t))
    return {'name': name, 'seed': seed, 'late_acc': float((pred == k).mean()), 'hold_acc': float((hold_pred == 0).mean()),
            'latency_ms_median': float(np.median(ts[5:])), 'pickle_mb': len(pickle.dumps((tf, clf)))/1e6}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(14) as pool:
        rows = list(pool.map(job, [(n, s) for n in X.LABEL for s in X.SEEDS]))
    per = {c: float(np.mean([np.mean([r['late_acc'] for r in rows if r['name'] == n]) for n in X.LABEL if X.LABEL[n] == c])) for c in X.FAULTS}
    out = {'kernels': KERNELS, 'per_class': per, 'macro3': float(np.mean(list(per.values()))), 'macro2': .5*(per['inner']+per['outer']),
           'healthy': float(np.mean([r['hold_acc'] for r in rows])), 'latency_ms_median': float(np.median([r['latency_ms_median'] for r in rows])),
           'pickle_mb': float(np.median([r['pickle_mb'] for r in rows])), 'per_bearing': {n: float(np.mean([r['late_acc'] for r in rows if r['name'] == n])) for n in X.LABEL}, 'rows': rows}
    (OUT/'minirocket.json').write_text(json.dumps(out, indent=1))
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items() if k != 'rows'})


if __name__ == '__main__':
    main()
