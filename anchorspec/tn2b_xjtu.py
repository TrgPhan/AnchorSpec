"""TN2b: mỗi máy một mô hình trên XJTU-SY. Giao thức: PROTOCOL_TN2B.md.

smoke -> freeze -> test. `test` kiểm tra hash và từ chối chạy lại. Không sửa
injection.py/features.py vì chúng thuộc bản freeze của TN2.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import time

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')

import numpy as np  # noqa: E402
from scipy import signal  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from bearing import Bearing  # noqa: E402
from cheap_sensor import CheapSensor, fault_path, output_stage, simulate  # noqa: E402
from features import extract  # noqa: E402
from injection import FS_SIM, Prior, _draw, component, quality_gate  # noqa: E402

DATA = ROOT.parent/'data'/'xjtu'
OUT = ROOT/'results'/'tn2b'
RAW = DATA/'extracted'/'XJTU-SY_Bearing_Datasets'
SENSOR = CheapSensor()
FS, N = 4000, 4000
UER204 = Bearing(8, 7.92, 34.55, 0.)
FOLDER = {'1': ('35Hz12kN', 2100.), '2': ('37.5Hz11kN', 2250.), '3': ('40Hz10kN', 2400.)}
LABEL = {'1_1': 'outer', '1_2': 'outer', '1_3': 'outer', '2_2': 'outer', '2_4': 'outer', '2_5': 'outer',
         '3_1': 'outer', '3_5': 'outer', '2_1': 'inner', '3_3': 'inner', '3_4': 'inner', '1_4': 'cage', '2_3': 'cage'}
SMOKE = {'1_5': 'inner', '3_2': 'outer'}  # hỏng nhiều bộ phận; nhãn tạm chỉ để chạy đường ống
CLASSES = ('healthy', 'inner', 'outer', 'cage')
FAULTS = CLASSES[1:]
SEEDS = (11, 29, 47)
N_INJECT = 150
AMP_GRID = (.2, .35, .6, 1., 1.7, 3.)
# Cột của features.extract: 4 biên độ + 10 băng + 2 phổ + 12 bậc thô + 12 bậc bao hình
ENV = {'cage': (31, 34), 'outer': (34, 37), 'inner': (37, 40)}
RF = dict(n_estimators=200, max_features='sqrt', bootstrap=False, class_weight='balanced', n_jobs=1)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_hashes():
    return {p: sha(ROOT/p) for p in ('tn2b_xjtu.py', 'features.py', 'injection.py', 'cheap_sensor.py', 'bearing.py', 'PROTOCOL_TN2B.md')}


def fr_of(name):
    return FOLDER[name[0]][1]/60


def load(name):
    """Cửa sổ 2 trục qua cảm biến rẻ, theo thứ tự thời gian, có cache: (bản ghi, 2, N)."""
    cache = DATA/'cache'/f'{name}.npy'
    if cache.exists():
        return np.load(cache)
    cache.parent.mkdir(exist_ok=True)
    folder = RAW/FOLDER[name[0]][0]/f'Bearing{name}'
    files = sorted(folder.glob('*.csv'), key=lambda p: int(p.stem))
    seed = int.from_bytes(name.encode(), 'big') % 2**31
    out = []
    for i, f in enumerate(files):
        a = np.loadtxt(f, delimiter=',', skiprows=1).T
        rng = np.random.default_rng([seed, i])
        out.append([simulate(axis, 25600, SENSOR, rng)[:N] for axis in a])
    out = np.array(out, dtype=np.float32)
    np.save(cache, out)
    return out


def split(x):
    n = len(x)
    base = min(30, int(.4*n))
    late = max(5, int(.1*n))
    return x[:base], x[base:base+5], x[n-late:]


def axis_features(x, fr, orders):
    """x: (n, 2, N) -> (n, 2 x đặc trưng)."""
    return np.column_stack([extract(x[:, a], FS, fr, orders) for a in range(2)])


def cross_features(x):
    """⑦ Quan hệ giữa hai trục, không dùng nhãn."""
    a, b = x[:, 0]-x[:, 0].mean(1, keepdims=True), x[:, 1]-x[:, 1].mean(1, keepdims=True)
    ra, rb = np.sqrt((a**2).mean(1))+1e-15, np.sqrt((b**2).mean(1))+1e-15
    corr = (a*b).mean(1)/(ra*rb)
    rows = [np.log(ra/rb), corr]
    f, c = signal.coherence(a, b, FS, nperseg=512, axis=1)
    for lo, hi in ((0, 300), (300, 600), (600, 1000)):
        rows.append(c[:, (f >= lo) & (f < hi)].mean(1))
    both = []
    for u, v in zip(a, b):
        pu, _ = signal.find_peaks(np.abs(u), height=4*np.median(np.abs(u))+1e-15, distance=8)
        pv, _ = signal.find_peaks(np.abs(v), height=4*np.median(np.abs(v))+1e-15, distance=8)
        both.append(np.mean(np.min(np.abs(pu[:, None]-pv[None]), axis=1) <= 4) if len(pu) and len(pv) else 0.)
    rows.append(np.array(both))
    return np.column_stack(rows)


def inject_axes(bg, kind, fr, orders, prior, rng, axis_ratio_sigma=.5):
    """Cùng dạng sóng lỗi cho 2 trục, biên độ theo nền từng trục và tỉ lệ ngẫu nhiên."""
    n_sim = int(np.ceil(N*FS_SIM/FS))+int(.05*FS_SIM)
    raw, meta = component(kind, n_sim, FS_SIM, fr, orders, prior, rng)
    x = fault_path(raw, FS_SIM, SENSOR)[-N:]
    x = x-x.mean()
    x = x/np.sqrt(np.mean(x**2))
    amp = _draw(rng, prior.amp_rel, log=True)
    gain = np.exp(rng.normal(0, axis_ratio_sigma))
    out = np.stack([output_stage(bg[0]+x*amp*np.sqrt(np.mean(bg[0]**2)), SENSOR),
                    output_stage(bg[1]+x*amp*gain*np.sqrt(np.mean(bg[1]**2)), SENSOR)])
    return out, meta | {'amp_rel': amp, 'axis_gain': float(gain)}


def injected_set(base, fr, orders, prior, kinds, n, rng):
    """Mẫu qua cổng cho từng lớp, dừng khi vượt 4n lần thử; số bị loại được ghi lại."""
    sets, audit = {}, {}
    for kind in kinds:
        rows, rejected, tries = [], {}, 0
        while len(rows) < n:
            tries += 1
            if tries > 4*n:
                raise RuntimeError(f'Quota failed {kind}: {rejected}')
            i = int(rng.integers(len(base)))
            y, _ = inject_axes(base[i], kind, fr, orders, prior, rng)
            why = next((r for r in (quality_gate(y[a], base[i][a], SENSOR) for a in range(2)) if r), None)
            if why:
                rejected[why] = rejected.get(why, 0)+1
            else:
                rows.append(y)
        sets[kind] = np.array(rows)
        audit[kind] = {'accepted': len(rows), 'rejected': rejected}
    return sets, audit


class Norm:
    def __init__(self, x):
        self.mu, self.sd = x.mean(0), x.std(0)+1e-9

    def __call__(self, x):
        return (x-self.mu)/self.sd


def bearing_data(name):
    fr, orders = fr_of(name), UER204.orders()
    x = load(name)
    base, hold, late = split(x)
    f = {k: axis_features(v, fr, orders) for k, v in (('base', base), ('hold', hold), ('late', late))}
    c = {k: cross_features(v) for k, v in (('base', base), ('hold', hold), ('late', late))}
    return {'raw_base': base, 'f': f, 'c': c, 'norm': Norm(f['base']), 'cnorm': Norm(c['base']), 'fr': fr}


def stream(p):
    """Lọc theo thời gian trên xác suất, chỉ dùng quá khứ."""
    sma = np.array([p[max(0, i-4):i+1].mean(0) for i in range(len(p))])
    ema = np.zeros_like(p)
    ema[0] = p[0]
    for i in range(1, len(p)):
        ema[i] = .3*p[i]+.7*ema[i-1]
    return {'raw': p, 'sma5': sma, 'ema': ema}


def report(p_late, p_hold, label):
    k = CLASSES.index(label)
    pred = p_late.argmax(1)
    out = {'late_acc': float((pred == k).mean()), 'hold_acc': float((p_hold.argmax(1) == 0).mean()),
           'pred_counts': np.bincount(pred, minlength=4).tolist(), 'majority': CLASSES[int(np.bincount(pred, minlength=4).argmax())],
           'type_given_fault': float((p_late[:, 1:].argmax(1) == k-1).mean()), 'flips': int((np.diff(pred) != 0).sum())}
    return out


def physics_rule(z_axes):
    """z: đặc trưng đã chuẩn hóa theo nền của ổ. Không huấn luyện. Trả xác suất giả 4 lớp."""
    n_each = z_axes.shape[1]//2
    scores = []
    for kind in FAULTS:
        lo, hi = ENV[kind]
        scores.append(np.maximum(z_axes[:, lo:hi].mean(1), z_axes[:, n_each+lo:n_each+hi].mean(1)))
    scores = np.column_stack(scores)
    p = np.zeros((len(z_axes), 4))
    best = scores.argmax(1)
    alarm = scores.max(1) >= 3
    p[np.arange(len(z_axes)), np.where(alarm, best+1, 0)] = 1
    return p


def expand(p, model_classes):
    out = np.zeros((len(p), 4))
    out[:, model_classes] = p
    return out


def fit_predict(X, y, seed, zs, cfg=None):
    model = RandomForestClassifier(random_state=seed, **(cfg or RF)).fit(X, y)
    return [expand(model.predict_proba(z), model.classes_) for z in zs]


def per_seed(job):
    """Một ổ, một seed: toàn bộ nhánh."""
    name, label, seed, common, amp_center = job
    d = bearing_data(name)
    fr, orders, n = d['fr'], UER204.orders(), d['norm']
    h, zh, zl = n(d['f']['base']), n(d['f']['hold']), n(d['f']['late'])
    rng = np.random.default_rng([seed, int.from_bytes(name.encode(), 'big') % 2**31])
    res, stream_res, audit = {}, {}, {}
    y0 = np.zeros(len(h), int)

    def add(arm, late, hold):
        res[arm] = report(late, hold, label)
        stream_res[arm] = {k: float((v.argmax(1) == CLASSES.index(label)).mean()) for k, v in stream(late).items()}

    # A0
    sets, audit['A0'] = injected_set(d['raw_base'], fr, orders, Prior(), FAULTS, N_INJECT, rng)
    fa = {k: axis_features(v, fr, orders) for k, v in sets.items()}
    ca = {k: cross_features(v) for k, v in sets.items()}
    Xa = np.concatenate([h]+[n(fa[k]) for k in FAULTS])
    ya = np.concatenate([y0]+[np.full(N_INJECT, i+1) for i in range(3)])
    late, hold = fit_predict(Xa, ya, seed, [zl, zh])
    add('A0', late, hold)
    # A1: biên độ chung cho mọi lớp, tâm từ W1 trên ổ khác
    prior = Prior(amp_rel=(amp_center/1.5, amp_center*1.5))
    sets1, audit['A1'] = injected_set(d['raw_base'], fr, orders, prior, FAULTS, N_INJECT, rng)
    Xb = np.concatenate([h]+[n(axis_features(sets1[k], fr, orders)) for k in FAULTS])
    late, hold = fit_predict(Xb, ya, seed, [zl, zh])
    add('A1', late, hold)
    # P: quy tắc vật lý, không huấn luyện
    add('P', physics_rule(zl), physics_rule(zh))
    # C: CWRU một trục, trung bình xác suất 2 trục
    half = h.shape[1]//2
    cw = common['cwru']
    cm = RandomForestClassifier(random_state=seed, **RF).fit(cw[0], cw[1])
    both = lambda z: expand(.5*(cm.predict_proba(z[:, :half])+cm.predict_proba(z[:, half:])), cm.classes_)
    add('C', both(zl), both(zh))
    # D: lỗi thật từ ổ khác
    others = [v for k, v in common['lobo'].items() if k != name]
    Xd = np.concatenate([h]+[v[0] for v in others])
    yd = np.concatenate([y0]+[v[1] for v in others])
    late, hold = fit_predict(Xd, yd, seed, [zl, zh])
    add('D', late, hold)
    # Phụ: đặc trưng giữa hai trục, mô hình gọn
    cn = d['cnorm']
    ch = cn(d['c']['base'])
    Xc = np.concatenate([Xa, np.concatenate([ch]+[cn(ca[k]) for k in FAULTS])], axis=1)
    late, hold = fit_predict(Xc, ya, seed, [np.column_stack([zl, cn(d['c']['late'])]), np.column_stack([zh, cn(d['c']['hold'])])])
    add('A0_cross', late, hold)
    small = dict(n_estimators=50, max_depth=8, min_samples_leaf=2, max_features='sqrt', bootstrap=False, class_weight='balanced', n_jobs=1)
    late, hold = fit_predict(Xa, ya, seed, [zl, zh], small)
    add('A0_rf50d8', late, hold)
    lr = LogisticRegression(max_iter=2000, class_weight='balanced', C=.1).fit(Xa, ya)
    add('A0_logreg', expand(lr.predict_proba(zl), lr.classes_), expand(lr.predict_proba(zh), lr.classes_))
    return name, seed, res, stream_res, audit


def common_inputs(names, seed=0):
    """CWRU một trục và kho lỗi thật theo ổ cho nhánh D, đều chuẩn hóa theo nền của nguồn."""
    from tn2_paderborn import cwru_features
    c = cwru_features(SENSOR, seed)
    mu, sd = c['healthy'].mean(0), c['healthy'].std(0)+1e-9
    X = np.concatenate([(c[k]-mu)/sd for k in ('healthy', 'inner', 'outer')])
    y = np.concatenate([np.full(len(c[k]), i) for i, k in enumerate(('healthy', 'inner', 'outer'))])
    lobo = {}
    for name in names:
        d = bearing_data(name)
        n = d['norm']
        k = CLASSES.index(LABEL.get(name, SMOKE.get(name)))
        lobo[name] = (np.concatenate([n(d['f']['base']), n(d['f']['late'])]),
                      np.concatenate([np.zeros(len(d['f']['base']), int), np.full(len(d['f']['late']), k)]))
    return {'cwru': (X, y), 'lobo': lobo}


def amp_scores(name):
    """W1 giữa lỗi cấy và lỗi thật của chính ổ đó theo lưới biên độ chung."""
    d = bearing_data(name)
    label = LABEL[name]
    rng = np.random.default_rng([5, int.from_bytes(name.encode(), 'big') % 2**31])
    real = np.sort(d['norm'](d['f']['late']), axis=0)
    out = {}
    for amp in AMP_GRID:
        prior = Prior(amp_rel=(amp, amp))
        ys = np.array([inject_axes(d['raw_base'][int(rng.integers(len(d['raw_base'])))], label, d['fr'], UER204.orders(), prior, rng)[0] for _ in range(16)])
        f = np.sort(d['norm'](axis_features(ys, d['fr'], UER204.orders())), axis=0)
        q = (np.arange(16)+.5)/16
        out[amp] = float(np.mean(np.abs(f-np.quantile(real, q, axis=0))))
    return name, out


def score(rows, names, key='late_acc'):
    by = {k: [] for k in FAULTS}
    for n in names:
        by[LABEL[n]].append(np.mean([r[n][key] for r in rows]))
    per = {k: float(np.mean(v)) for k, v in by.items() if v}
    return {'macro3': float(np.mean(list(per.values()))), 'macro2': float(np.mean([per['inner'], per['outer']])), **per}


def bootstrap(rows_a, rows_b, names, classes, n=10000):
    rng = np.random.default_rng(0)
    diffs = {c: np.array([np.mean([r[m]['late_acc'] for r in rows_a])-np.mean([r[m]['late_acc'] for r in rows_b]) for m in names if LABEL[m] == c]) for c in classes}
    point = float(np.mean([v.mean() for v in diffs.values()]))
    draws = [np.mean([v[rng.integers(len(v), size=len(v))].mean() for v in diffs.values()]) for _ in range(n)]
    return {'diff': point, 'ci95': [float(np.quantile(draws, .025)), float(np.quantile(draws, .975))]}


def latency():
    """Độ trễ một luồng cho cửa sổ 2 trục trên máy này, KHÔNG phải Pi 5."""
    name = '2_2'
    d = bearing_data(name)
    fr, orders = d['fr'], UER204.orders()
    rng = np.random.default_rng(0)
    sets, _ = injected_set(d['raw_base'], fr, orders, Prior(), FAULTS, N_INJECT, rng)
    n = d['norm']
    X = np.concatenate([n(d['f']['base'])]+[n(axis_features(sets[k], fr, orders)) for k in FAULTS])
    y = np.concatenate([np.zeros(len(d['f']['base']), int)]+[np.full(N_INJECT, i+1) for i in range(3)])
    models = {'rf200': RandomForestClassifier(random_state=0, **RF),
              'rf50d8': RandomForestClassifier(n_estimators=50, max_depth=8, min_samples_leaf=2, max_features='sqrt', bootstrap=False, class_weight='balanced', random_state=0, n_jobs=1),
              'logreg': LogisticRegression(max_iter=2000, class_weight='balanced', C=.1)}
    window = d['raw_base'][:1]
    out = {}
    feats = []
    for _ in range(50):
        t = time.perf_counter()
        z = n(axis_features(window, fr, orders))
        feats.append(1e3*(time.perf_counter()-t))
    out['features_ms_median'] = float(np.median(feats))
    out['features_ms_p95'] = float(np.quantile(feats, .95))
    for k, m in models.items():
        m.fit(X, y)
        ts = []
        for _ in range(50):
            t = time.perf_counter()
            m.predict_proba(z)
            ts.append(1e3*(time.perf_counter()-t))
        out[k] = {'predict_ms_median': float(np.median(ts)), 'predict_ms_p95': float(np.quantile(ts, .95)), 'pickle_mb': len(pickle.dumps(m))/1e6}
    return out


def run(names, labels, workers):
    all_names = list(LABEL)
    print('caching', flush=True)
    with ProcessPoolExecutor(workers) as pool:
        list(pool.map(load, list(LABEL)+list(SMOKE)))
    common = common_inputs(all_names)
    with ProcessPoolExecutor(workers) as pool:
        amp = dict(pool.map(amp_scores, all_names))
    centers = {}
    for n in names:
        rows = [v for k, v in amp.items() if k != n]
        means = {a: np.mean([r[a] for r in rows]) for a in AMP_GRID}
        centers[n] = float(min(means, key=means.get))
    jobs = [(n, labels[n], s, common, centers[n]) for n in names for s in SEEDS]
    with ProcessPoolExecutor(workers) as pool:
        out = list(pool.map(per_seed, jobs))
    results = {s: {} for s in SEEDS}
    streams = {s: {} for s in SEEDS}
    audits = {}
    for name, seed, res, st, aud in out:
        results[seed][name] = res
        streams[seed][name] = st
        audits[f'{name}:{seed}'] = aud
    return results, streams, audits, centers, amp


def arm_rows(results, arm):
    return [{n: results[s][n][arm] for n in results[s]} for s in SEEDS]


def smoke(workers):
    results, streams, audits, centers, amp = run(list(SMOKE), SMOKE, workers)
    OUT.mkdir(parents=True, exist_ok=True)
    print('centers', centers)
    print('amp sample', {k: min(v, key=v.get) for k, v in amp.items()})
    for n in SMOKE:
        print(n, {a: results[SEEDS[0]][n][a]['pred_counts'] for a in results[SEEDS[0]][n]})
    print('audit', json.dumps(audits[f'1_5:{SEEDS[0]}'])[:300])
    print('late windows', {n: len(split(load(n))[2]) for n in list(SMOKE)+['2_4']}, 'base', {n: len(split(load(n))[0]) for n in ['2_4', '3_1']})


def freeze():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'FROZEN.json').write_text(json.dumps({'code': code_hashes(), 'primary': 'A0', 'labels': LABEL}, indent=1))
    print('frozen', code_hashes()['tn2b_xjtu.py'][:12])


def test(workers):
    frozen = json.loads((OUT/'FROZEN.json').read_text())
    if frozen['code'] != code_hashes():
        raise ValueError('Code/protocol changed after freeze')
    dest = OUT/'test.json'
    if dest.exists():
        raise FileExistsError('Test already opened once')
    results, streams, audits, centers, amp = run(list(LABEL), LABEL, workers)
    names = list(LABEL)
    arms = list(results[SEEDS[0]][names[0]])
    summary = {}
    for arm in arms:
        rows = arm_rows(results, arm)
        summary[arm] = {**score(rows, names), 'type_given_fault': score(rows, names, 'type_given_fault'),
                        'healthy': float(np.mean([r[n]['hold_acc'] for r in rows for n in names])),
                        'bearing_votes': [sum(r[n]['majority'] == LABEL[n] for n in names) for r in rows],
                        'flips_mean': float(np.mean([r[n]['flips'] for r in rows for n in names])),
                        'macro3_seeds': [score([r], names)['macro3'] for r in rows],
                        'stream': {k: float(np.mean([streams[s][n][arm][k] for s in SEEDS for n in names])) for k in ('raw', 'sma5', 'ema')}}
    rows = {a: arm_rows(results, a) for a in arms}
    comparisons = {}
    for x, y in (('A0', 'C'), ('A0', 'D'), ('A0', 'P'), ('A1', 'A0'), ('A0', 'A0_cross'), ('A0', 'A0_rf50d8'), ('A0', 'A0_logreg')):
        comparisons[f'{x} - {y} (macro3)'] = bootstrap(rows[x], rows[y], names, FAULTS)
        comparisons[f'{x} - {y} (macro2)'] = bootstrap(rows[x], rows[y], names, ('inner', 'outer'))
    deploy = latency()
    dest.write_text(json.dumps({'summary': summary, 'comparisons': comparisons, 'deploy': deploy, 'centers': centers,
                                'amp_w1': {k: {str(a): b for a, b in v.items()} for k, v in amp.items()},
                                'per_seed': {str(s): results[s] for s in SEEDS}, 'audit': audits}, indent=1, default=int))
    for a, s in summary.items():
        print(a, {k: round(v, 3) for k, v in s.items() if isinstance(v, float)}, s['bearing_votes'], {k: round(v, 3) for k, v in s['stream'].items()}, flush=True)
    print(json.dumps(comparisons, indent=0))
    print(json.dumps(deploy, indent=0))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['smoke', 'freeze', 'test'])
    ap.add_argument('--workers', type=int, default=14)
    args = ap.parse_args()
    {'smoke': lambda: smoke(args.workers), 'freeze': freeze, 'test': lambda: test(args.workers)}[args.stage]()
