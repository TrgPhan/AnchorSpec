"""TN3: chỉ số sức khỏe bằng tham chiếu đóng băng + khớp xu hướng -> thời gian còn lại.

HI = khoảng cách Mahalanobis tới nền ban đầu CỐ ĐỊNH của từng ổ, không dùng mô hình
tự học. Ổ DEV chọn hệ số ngưỡng và HI hỏng; ổ TEST chỉ đọc sau khi đã chốt, báo một lần.
"""
import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
import re
import sys

import numpy as np
from scipy import signal, stats
from sklearn.covariance import LedoitWolf

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from cheap_sensor import CheapSensor, simulate  # noqa: E402

DATA = ROOT.parent/'data'
OUT = ROOT/'results'/'tn3'
CACHE = DATA/'tn3_cache'
CHEAP = CheapSensor()
SENSORS = {'cheap': CHEAP, 'goc': None}
BASELINE_SNAPSHOTS = 30
PERSIST = 5
K_GRID = (3., 4., 5., 6., 8., 10., 15.)
ALPHA = .2

DEV = {'femto': ['Bearing1_1', 'Bearing2_1', 'Bearing3_1'],
       'xjtu': ['Bearing1_1', 'Bearing2_1', 'Bearing3_1'],
       'ims': ['test2_b1']}
IMS_RUNS = {'test1_b3': ('1st_test', [4, 5]), 'test1_b4': ('1st_test', [6, 7]),
            'test2_b1': ('2nd_test', [0]), 'test3_b3': ('3rd_test', [2])}


def snapshot_features(x, fs, sensor, seed):
    """x: (trục, mẫu). Đặc trưng độc lập nhãn, tính cho từng trục rồi nối."""
    out = []
    for i, axis in enumerate(np.atleast_2d(x)):
        if sensor is not None:
            axis, f_s, top = simulate(axis, fs, sensor, np.random.default_rng([seed, i])), sensor.fs_out, 1000.
        else:
            f_s, top = fs, fs/2*.9
        axis = axis-axis.mean()
        rms = np.sqrt(np.mean(axis**2))+1e-15
        f, p = signal.welch(axis, f_s, nperseg=min(256, len(axis)))
        edges = np.linspace(0, top, 6)
        bands = [np.log(p[(f >= a) & (f < b)].sum()+1e-18) for a, b in zip(edges[:-1], edges[1:])]
        out += [np.log(rms), float(stats.kurtosis(axis)), np.max(np.abs(axis))/rms]+bands
    return np.array(out)


def list_runs():
    """Liệt kê theo cấu trúc thật của từng bộ dữ liệu."""
    runs = {}
    fem = DATA/'pronostia'/'extracted'
    for d in sorted(list(fem.glob('**/Learning_set/Bearing*'))+list(fem.glob('**/Full_Test_Set/Bearing*'))):
        files = sorted(d.glob('acc_*.csv'))
        if files:
            runs[('femto', d.name)] = {'files': files, 'fs': 25600, 'dt_h': 10/3600, 'reader': 'femto'}
    for d in sorted((DATA/'xjtu'/'extracted').glob('**/Bearing*')):
        files = sorted(d.glob('*.csv'), key=lambda p: int(p.stem))
        if files:
            runs[('xjtu', d.name)] = {'files': files, 'fs': 25600, 'dt_h': 1/60, 'reader': 'xjtu'}
    for name, (folder, cols) in IMS_RUNS.items():
        hits = list((DATA/'ims'/'extracted').glob(f'**/{folder}'))
        if hits:
            root = hits[0]
            files = sorted(p for p in root.rglob('*') if p.is_file() and re.fullmatch(r'\d{4}\.\d{2}\.\d{2}\.\d{2}\.\d{2}\.\d{2}', p.name))
            runs[('ims', name)] = {'files': files, 'fs': 20000, 'dt_h': None, 'reader': 'ims', 'cols': cols}
    return runs


def read(path, reader, cols=None):
    if reader == 'femto':
        with open(path) as f:
            first = f.readline()
        a = np.loadtxt(path, delimiter=';' if ';' in first else ',')
        return a[:, 4:6].T
    if reader == 'xjtu':
        return np.loadtxt(path, delimiter=',', skiprows=1).T
    a = np.loadtxt(path)
    return a[:, cols].T


def _job(args):
    path, reader, cols, fs, sensor, seed = args
    return snapshot_features(read(path, reader, cols), fs, sensor, seed)


def run_features(key, run, sensor_name, pool):
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE/f'{key[0]}_{key[1]}_{sensor_name}.npz'
    if out.exists():
        a = np.load(out)
        return a['x'], a['t']
    sensor = SENSORS[sensor_name]
    jobs = [(p, run['reader'], run.get('cols'), run['fs'], sensor, i) for i, p in enumerate(run['files'])]
    x = np.array(list(pool.map(_job, jobs, chunksize=16)))
    if run['reader'] == 'ims':
        stamps = [datetime.strptime(p.name, '%Y.%m.%d.%H.%M.%S') for p in run['files']]
        t = np.array([(s-stamps[0]).total_seconds()/3600 for s in stamps])
    else:
        t = np.arange(len(x))*run['dt_h']
    np.savez(out, x=x, t=t)
    return x, t


def health_index(x):
    """Tham chiếu cố định: BASELINE_SNAPSHOTS bản đầu, không cập nhật."""
    base = x[:BASELINE_SNAPSHOTS]
    mu, cov = base.mean(0), LedoitWolf().fit(base).covariance_
    inv = np.linalg.pinv(cov)
    d = x-mu
    return np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', d, inv, d), 0)/x.shape[1])


def rms_index(x):
    """Baseline đơn giản: z-score của log RMS trục đầu với cùng nền."""
    base = x[:BASELINE_SNAPSHOTS, 0]
    return np.abs(x[:, 0]-base.mean())/(base.std()+1e-9)


def first_warning(hi, k):
    """Ngưỡng từ NỀN (trung vị + k*MAD); cảnh báo khi vượt PERSIST bản liên tiếp."""
    base = hi[:BASELINE_SNAPSHOTS]
    med = np.median(base)
    thr = med+k*1.4826*np.median(np.abs(base-med))
    over = hi > thr
    run = 0
    for i in range(BASELINE_SNAPSHOTS, len(hi)):
        run = run+1 if over[i] else 0
        if run >= PERSIST:
            return i, float(thr)
    return None, float(thr)


def fit_rul(hi, t, i, hi_fail, window):
    """Khớp log HI tuyến tính trên cửa sổ gần nhất; ngoại suy tới HI hỏng."""
    lo = max(0, i-window+1)
    y = np.log(np.maximum(hi[lo:i+1], 1e-6))
    if len(y) < 5:
        return None
    a, b = np.polyfit(t[lo:i+1], y, 1)
    if a <= 0:
        return None
    return float(max((np.log(hi_fail)-b)/a-t[i], 0))


def phm_score(true, pred):
    e = 100*(true-pred)/max(true, 1e-9)
    return float(np.exp(-np.log(.5)*e/5) if e <= 0 else np.exp(np.log(.5)*e/20))


def evaluate(hi, t, k, hi_fail):
    i, thr = first_warning(hi, k)
    life = float(t[-1])
    res = {'life_h': life, 'threshold': thr, 'warning_h': None if i is None else float(t[i]),
           'lead_h': None if i is None else life-float(t[i]),
           'lead_pct_life': None if i is None else 100*(life-float(t[i]))/life,
           'hi_end': float(hi[-1]), 'n': len(hi)}
    if i is None:
        return res
    window = max(20, min(120, len(hi)//20))
    steps = np.arange(i, len(hi)-1, max(1, (len(hi)-i)//50))
    inside, count, scores = 0, 0, {}
    for s in steps:
        pred = fit_rul(hi, t, int(s), hi_fail, window)
        true = life-t[s]
        if pred is None or true <= 0:
            continue
        count += 1
        inside += abs(pred-true) <= ALPHA*true
    res['alpha_lambda_frac'] = inside/count if count else None
    res['rul_points'] = count
    for frac in (.5, .9):
        s = int(i+frac*(len(hi)-1-i))
        pred, true = fit_rul(hi, t, s, hi_fail, window), life-t[s]
        res[f'phm_score_{int(frac*100)}'] = phm_score(true, pred) if pred is not None and true > 0 else None
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--datasets', default='femto,xjtu,ims')
    ap.add_argument('--workers', type=int, default=12)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    runs = {k: v for k, v in list_runs().items() if k[0] in args.datasets.split(',')}
    results = {}
    with ProcessPoolExecutor(args.workers) as pool:
        for dataset in sorted({k[0] for k in runs}):
            for sensor_name in SENSORS:
                dev_keys = [k for k in runs if k[0] == dataset and k[1] in DEV[dataset]]
                dev = {k: run_features(k, runs[k], sensor_name, pool) for k in dev_keys}
                hi = {k: (health_index(x), t, rms_index(x)) for k, (x, t) in dev.items()}
                hi_fail = float(np.median([np.median(h[0][-5:]) for h in hi.values()]))
                # Chọn k trên DEV: bản cảnh báo sớm nhất trong các k không cảnh báo trong nửa đầu đời.
                best = None
                table = {}
                for k_value in K_GRID:
                    warns = [first_warning(h[0], k_value)[0] for h in hi.values()]
                    leads = [None if w is None else float(h[1][w]/h[1][-1]) for w, h in zip(warns, hi.values())]
                    table[k_value] = leads
                    if all(v is not None and v >= .5 for v in leads) and best is None:
                        best = k_value
                best = best or K_GRID[-1]
                test = [k for k in runs if k[0] == dataset and k not in dev_keys]
                rows = {}
                for key in dev_keys+test:
                    x, t = run_features(key, runs[key], sensor_name, pool)
                    h = health_index(x)
                    rows[key[1]] = {'role': 'dev' if key in dev_keys else 'test', **evaluate(h, t, best, hi_fail),
                                    'baseline_rms': evaluate(rms_index(x), t, best, max(hi_fail, 2.))}
                    np.savez(OUT/f'{dataset}_{key[1]}_{sensor_name}.npz', hi=h, t=t, rms=rms_index(x))
                    print(dataset, sensor_name, key[1], rows[key[1]]['role'], rows[key[1]]['lead_h'], rows[key[1]].get('alpha_lambda_frac'), flush=True)
                results[f'{dataset}/{sensor_name}'] = {'k': best, 'k_table_warning_frac_of_life': {str(a): b for a, b in table.items()},
                                                       'hi_fail': hi_fail, 'bearings': rows}
    (OUT/'summary.json').write_text(json.dumps({'config': {'baseline_snapshots': BASELINE_SNAPSHOTS, 'persist': PERSIST, 'alpha': ALPHA,
        'k_grid': K_GRID, 'dev': DEV, 'sensor': CHEAP.as_dict()}, 'results': results}, indent=1))


if __name__ == '__main__':
    main()
