"""TN2c: A0 trên IMS. Giao thức PROTOCOL_TN2C.md. check -> test (một lần)."""
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import re
import sys

os.environ.setdefault('OMP_NUM_THREADS', '1')

import numpy as np  # noqa: E402
from scipy import signal  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from cheap_sensor import CheapSensor, simulate  # noqa: E402
from features import extract  # noqa: E402
from injection import Prior, inject, quality_gate  # noqa: E402

BASE = ROOT.parent/'data'/'ims'/'extracted'/'4. Bearings'
FOLDERS = {'t1': BASE/'1st_test'/'1st_test', 't2': BASE/'2nd_test'/'2nd_test', 't3': BASE/'3rd_test'/'4th_test'/'txt'}
CH = {'t1_b1': 0, 't1_b2': 2, 't1_b3': 4, 't1_b4': 6, 't2_b1': 0, 't2_b2': 1, 't2_b3': 2, 't2_b4': 3, 't3_b1': 0, 't3_b2': 1, 't3_b3': 2, 't3_b4': 3}
LABEL = {'t1_b3': 'inner', 't2_b1': 'outer', 't3_b3': 'outer'}
CONTROL = ['t1_b1', 't1_b2', 't2_b2', 't2_b3', 't2_b4', 't3_b1', 't3_b2', 't3_b4']
CLASSES = ('healthy', 'inner', 'outer')
ORDERS = {'ftf': 14.8/(2000/60), 'bpfo': 236.4/(2000/60), 'bpfi': 296.9/(2000/60)}
FR = 2000/60
S = CheapSensor()
FS, N = 4000, 4000
OUT = ROOT/'results'/'tn2c'
CACHE = ROOT.parent/'data'/'ims'/'cache'
SEEDS = (11, 29, 47)
RF = dict(n_estimators=200, max_features='sqrt', bootstrap=False, class_weight='balanced', n_jobs=1)


def _file(args):
    path, ch, seed = args
    x = np.loadtxt(path, usecols=ch)
    return simulate(x, 20000, S, np.random.default_rng(seed))[:N].astype(np.float32)


def load(name, pool=None):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE/f'{name}.npy'
    if p.exists():
        return np.load(p)
    run = name[:2]
    files = sorted(f for f in FOLDERS[run].iterdir() if re.fullmatch(r'\d{4}(\.\d{2}){5}', f.name))
    jobs = [(f, CH[name], [int(name[1]), int(name[-1]), i]) for i, f in enumerate(files)]
    x = np.array(list(pool.map(_file, jobs, chunksize=32)))
    np.save(p, x)
    return x


def check(pool):
    """Đỉnh phổ bao hình 100-500 Hz ở cuối đời t2_b1, so với BPFO nguồn thứ cấp."""
    x = load('t2_b1', pool)
    late = x[-max(5, len(x)//50):]
    y = signal.sosfiltfilt(signal.butter(4, (10, 1000), 'bandpass', fs=FS, output='sos'), late, axis=1)
    e = np.abs(signal.hilbert(y, axis=1))
    sp = (np.abs(np.fft.rfft(e-e.mean(1, keepdims=True), axis=1))**2).mean(0)
    f = np.fft.rfftfreq(N, 1/FS)
    b = (f >= 100) & (f <= 500)
    top = np.argsort(sp[b])[::-1][:6]
    print('dinh bao hinh t2_b1 (Hz):', np.round(f[b][top], 1), 'BPFO', 236.4, 'BPFI', 296.9)
    z = np.abs(f-236.4) <= 6
    print('SNR quanh BPFO so voi trung vi 100-500 Hz:', round(float(sp[z].max()/np.median(sp[b])), 1))
    z = np.abs(f-296.9) <= 6
    print('SNR quanh BPFI:', round(float(sp[z].max()/np.median(sp[b])), 1))


def job(args):
    name, seed, cwru = args
    x = np.load(CACHE/f'{name}.npy').astype(float)
    base, late10, late2 = x[:30], x[-max(5, len(x)//10):], x[-max(5, len(x)//50):]
    f0 = extract(base, FS, FR, ORDERS)
    mu, sd = f0.mean(0), f0.std(0)+1e-9
    z = lambda w: (extract(w, FS, FR, ORDERS)-mu)/sd
    rng = np.random.default_rng([seed, sum(map(ord, name))])
    Xs, ys, rejected = [(f0-mu)/sd], [np.zeros(30, int)], {}
    for k, kind in ((1, 'inner'), (2, 'outer')):
        rows = []
        while len(rows) < 150:
            b = base[int(rng.integers(30))]
            y, _ = inject(b, kind, FR, ORDERS, S, Prior(), rng, name)
            why = quality_gate(y, b, S)
            if why:
                rejected[why] = rejected.get(why, 0)+1
            else:
                rows.append(y)
        Xs.append(z(np.array(rows)))
        ys.append(np.full(150, k))
    m = RandomForestClassifier(random_state=seed, **RF).fit(np.concatenate(Xs), np.concatenate(ys))
    c = RandomForestClassifier(random_state=seed, **RF).fit(cwru[0], cwru[1])

    def phys(zw):
        o, i = zw[:, 34:37].mean(1), zw[:, 37:40].mean(1)
        return np.where(np.maximum(o, i) < 3, 0, np.where(i > o, 1, 2))

    out = {'name': name, 'seed': seed, 'rejected': rejected}
    for key, w in (('late10', late10), ('late2', late2)):
        zw = z(w)
        out[key] = {'A0': np.bincount(m.predict(zw), minlength=3).tolist(), 'C': np.bincount(c.predict(zw), minlength=3).tolist(),
                    'P': np.bincount(phys(zw), minlength=3).tolist(), 'n': len(w)}
    return out


def test(pool):
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT/'test.json'
    if dest.exists():
        raise FileExistsError('Test already opened once')
    names = list(LABEL)+['t1_b4']+CONTROL
    for n in names:
        load(n, pool)
    from tn2_paderborn import cwru_features
    c = cwru_features(S, 0)
    mu, sd = c['healthy'].mean(0), c['healthy'].std(0)+1e-9
    X = np.concatenate([(c[k]-mu)/sd for k in CLASSES])
    y = np.concatenate([np.full(len(c[k]), i) for i, k in enumerate(CLASSES)])
    rows = list(pool.map(job, [(n, s, (X, y)) for n in names for s in SEEDS]))
    acc = lambda name, key, arm, k: float(np.mean([r[key][arm][k]/r[key]['n'] for r in rows if r['name'] == name]))
    summary = {}
    for arm in ('A0', 'C', 'P'):
        for key in ('late10', 'late2'):
            inner = acc('t1_b3', key, arm, 1)
            outer = np.mean([acc(n, key, arm, 2) for n in ('t2_b1', 't3_b3')])
            summary[f'{arm}/{key}'] = {'t1_b3_inner': inner, 't2_b1_outer': acc('t2_b1', key, arm, 2), 't3_b3_outer': acc('t3_b3', key, arm, 2),
                                       'primary': float(.5*(inner+outer)), 'control_healthy': float(np.mean([acc(n, key, arm, 0) for n in CONTROL])),
                                       't1_b4_counts_seed11': next(r[key][arm] for r in rows if r['name'] == 't1_b4' and r['seed'] == 11)}
    dest.write_text(json.dumps({'summary': summary, 'rows': rows, 'orders': ORDERS}, indent=1))
    for k, v in summary.items():
        print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()})
    print('control detail A0 late10', {n: round(acc(n, 'late10', 'A0', 0), 2) for n in CONTROL})


if __name__ == '__main__':
    with ProcessPoolExecutor(14) as pool:
        {'check': check, 'test': test}[sys.argv[1]](pool)
