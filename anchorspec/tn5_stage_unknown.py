"""Khám phá trên XJTU-SY (đã mở ở TN2b): độ đúng theo giai đoạn đời + lớp chưa biết + khởi tạo máy."""
import json
from concurrent.futures import ProcessPoolExecutor
import os
from pathlib import Path
import pickle
import sys
import time

os.environ.setdefault('OMP_NUM_THREADS', '1')

import numpy as np  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import tn2b_xjtu as X  # noqa: E402

OUT = ROOT/'results'/'tn5'
BINS = ((0., .3), (.3, .5), (.5, .7), (.7, .9), (.9, 1.))
SMALL = dict(n_estimators=50, max_depth=8, min_samples_leaf=2, max_features='sqrt', bootstrap=False, class_weight='balanced')


def train(name, seed, kinds, small=False):
    """Mô hình A0 của một máy trên `kinds`. Trả (model, norm, X huấn luyện chuẩn hóa, y)."""
    d = X.bearing_data(name)
    fr, orders, n = d['fr'], X.UER204.orders(), d['norm']
    rng = np.random.default_rng([seed, int.from_bytes(name.encode(), 'big') % 2**31])
    sets, _ = X.injected_set(d['raw_base'], fr, orders, X.Prior(), kinds, X.N_INJECT, rng)
    Xa = np.concatenate([n(d['f']['base'])]+[n(X.axis_features(sets[k], fr, orders)) for k in kinds])
    ya = np.concatenate([np.zeros(len(d['f']['base']), int)]+[np.full(X.N_INJECT, X.CLASSES.index(k)) for k in kinds])
    cfg = dict(SMALL, n_jobs=1) if small else X.RF
    return RandomForestClassifier(random_state=seed, **cfg).fit(Xa, ya), n, Xa, ya, d


def stage_job(job):
    name, seed = job
    label = X.LABEL[name]
    m, n, *_ , d = train(name, seed, X.FAULTS)
    full = X.load(name)
    z = n(X.axis_features(full, d['fr'], X.UER204.orders()))
    p = X.expand(m.predict_proba(z), m.classes_)
    sma = X.stream(p)['sma5']
    k = X.CLASSES.index(label)
    start = len(d['f']['base'])+5
    rows = {}
    N = len(full)
    for lo, hi in BINS:
        idx = np.arange(max(int(lo*N), start), int(hi*N))
        if not len(idx):
            rows[f'{lo}-{hi}'] = None
            continue
        rows[f'{lo}-{hi}'] = {'n': len(idx), 'loai_dung': float((sma[idx].argmax(1) == k).mean()), 'goi_binh_thuong': float((sma[idx].argmax(1) == 0).mean()),
                              'loai_khi_biet_loi': float((sma[idx, 1:].argmax(1) == k-1).mean())}
    return name, seed, rows


def unknown_job(job):
    """Bỏ một lớp khỏi huấn luyện. Điểm lạ: 1-max xác suất; khoảng cách tới tâm lớp gần nhất."""
    name, seed, known = job
    m, n, Xa, ya, d = train(name, seed, known)
    z = n(d['f']['late'])
    p = m.predict_proba(z)
    centers = np.array([Xa[ya == c].mean(0) for c in m.classes_])
    dist = np.sqrt(((z[:, None]-centers[None])**2).mean(2)).min(1)
    # Chỉ xét lỗi: trừ xác suất lớp bình thường để lỗi lạ không bị tính là "bình thường".
    fault_p = p[:, 1:]/np.maximum(p[:, 1:].sum(1, keepdims=True), 1e-9)
    return name, seed, tuple(known), {'conf': float((1-p.max(1)).mean()), 'dist': float(dist.mean()),
                                      'fault_conf': float((1-fault_p.max(1)).mean()) if p.shape[1] > 2 else None}


def auc(rows, unknown_labels, known_labels, key):
    u = [r[key] for r in rows if X.LABEL[r['name']] in unknown_labels and r[key] is not None]
    k = [r[key] for r in rows if X.LABEL[r['name']] in known_labels and r[key] is not None]
    if not u or not k:
        return None
    y = [1]*len(u)+[0]*len(k)
    return {'auroc': float(roc_auc_score(y, u+k)), 'n_unknown': len(u), 'n_known': len(k)}


def init_time():
    """Khởi tạo một máy: đọc nền đã có -> cấy -> đặc trưng -> huấn luyện -> lưu. Một luồng."""
    times = {}
    for name in ('2_2', '3_4'):
        ts = []
        for s in range(3):
            t = time.perf_counter()
            m, *_ = train(name, s, ('inner', 'outer'), small=True)
            blob = pickle.dumps(m)
            ts.append(time.perf_counter()-t)
        times[name] = {'seconds_median': float(np.median(ts)), 'bytes': len(blob)}
    return times


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = list(X.LABEL)
    with ProcessPoolExecutor(14) as pool:
        out = list(pool.map(stage_job, [(n, s) for n in names for s in X.SEEDS]))
        ks = [('inner', 'outer'), ('outer', 'cage'), ('inner', 'cage')]
        unk = list(pool.map(unknown_job, [(n, s, k) for n in names for s in X.SEEDS for k in ks]))
    stage = {}
    for b in (f'{lo}-{hi}' for lo, hi in BINS):
        by = {c: [] for c in X.FAULTS}
        for n in names:
            vals = [r[b] for nn, s, r in out if nn == n and r[b]]
            if vals:
                by[X.LABEL[n]].append({k: float(np.mean([v[k] for v in vals])) for k in ('loai_dung', 'goi_binh_thuong', 'loai_khi_biet_loi')})
        stage[b] = {c: {k: float(np.mean([v[k] for v in rows])) for k in rows[0]} | {'n_bearing': len(rows)} for c, rows in by.items() if rows}
        print(b, {c: {k: round(v, 2) for k, v in s.items()} for c, s in stage[b].items()}, flush=True)
    results = {}
    for known, unknown_set in ((('inner', 'outer'), ('cage',)), (('outer', 'cage'), ('inner',)), (('inner', 'cage'), ('outer',))):
        rows = []
        for n in names:
            vals = [v for nn, s, kk, v in unk if nn == n and kk == known]
            rows.append({'name': n, **{k: float(np.mean([v[k] for v in vals])) for k in ('conf', 'dist', 'fault_conf')}})
        results['+'.join(known)] = {k: auc(rows, unknown_set, known, k) for k in ('conf', 'dist', 'fault_conf')}
        print('biet', known, {k: v and round(v['auroc'], 3) for k, v in results['+'.join(known)].items()}, results['+'.join(known)]['conf'], flush=True)
    t = init_time()
    print('init', t)
    (OUT/'stage_unknown_init.json').write_text(json.dumps({'stage': stage, 'per_bearing': [list(o) for o in out], 'unknown': results, 'init_time': t}, indent=1))


if __name__ == '__main__':
    main()
