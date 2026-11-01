"""TN3b + chuỗi thời gian thực. KHÁM PHÁ: các ổ đã xem ở TN3/TN2b, không phải xác nhận.

So cách cảnh báo và cách báo RUL trên đặc trưng cảm biến rẻ đã cache. Mọi tính toán
chỉ dùng quá khứ; tham số chọn trên ổ dev như TN3.
"""
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import sys

import numpy as np
from scipy import stats
from sklearn.covariance import LedoitWolf
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import tn2b_xjtu as X  # noqa: E402
from tn3_trend import ALPHA, DEV, phm_score  # noqa: E402

CACHE = ROOT.parent/'data'/'tn3_cache'
OUT = ROOT/'results'/'tn3b'
SKIP, BASE = 10, 30
GRID = {'nguong': (5., 10., 15., 25., 40.), 'ewma': (3., 5., 8., 12., 20.), 'cusum': (5., 10., 20., 40., 80.)}


def hi_series(x, skip):
    """HI tham chiếu đóng băng, nền bỏ qua `skip` bản đầu (chạy rà)."""
    base = x[skip:skip+BASE]
    mu, inv = base.mean(0), np.linalg.pinv(LedoitWolf().fit(base).covariance_)
    d = x-mu
    return np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', d, inv, d), 0)/x.shape[1]), skip+BASE


def alarm(hi, start, kind, h):
    """Trả chỉ số cảnh báo đầu tiên, hoặc None. Chỉ dùng quá khứ."""
    y = np.log(np.maximum(hi, 1e-6))
    ref = y[start-BASE:start]
    mu, sd = np.median(ref), 1.4826*np.median(np.abs(ref-np.median(ref)))+1e-6
    z = (y-mu)/sd
    if kind == 'nguong':
        run = 0
        for i in range(start, len(z)):
            run = run+1 if z[i] > h else 0
            if run >= 5:
                return i
    elif kind == 'ewma':
        e = 0.
        for i in range(start, len(z)):
            e = .2*z[i]+.8*e
            if e > h:
                return i
    else:
        s = 0.
        for i in range(start, len(z)):
            s = max(0., s+min(z[i], 10.)-.5)
            if s > h:
                return i
    return None


def smooth(y, a=.2):
    out = np.zeros_like(y)
    out[0] = y[0]
    for i in range(1, len(y)):
        out[i] = a*y[i]+(1-a)*out[i-1]
    return out


def rul_loglinear(y, t, i, a0, fail, window):
    lo = max(a0, i-window+1)
    if i-lo < 4:
        return None, None
    s, c = np.polyfit(t[lo:i+1], y[lo:i+1], 1)
    return (float(max((fail-c)/s-t[i], 0)), None) if s > 0 else (None, None)


def rul_wiener(y, t, i, a0, fail):
    """Thời gian chạm ngưỡng của quá trình Wiener trên log HI đã làm mượt; có khoảng 80%."""
    if i-a0 < 4:
        return None, None
    dt = np.diff(t[a0:i+1])
    dy = np.diff(y[a0:i+1])
    drift = dy.sum()/max(dt.sum(), 1e-9)
    if drift <= 0:
        return None, None
    gap = fail-y[i]
    if gap <= 0:
        return 0., (0., 0.)
    var = max(np.mean((dy-drift*dt)**2/np.maximum(dt, 1e-9)), 1e-9)
    mean, lam = gap/drift, gap**2/var
    q = stats.invgauss(mean/lam, scale=lam)
    return float(mean), (float(q.ppf(.1)), float(q.ppf(.9)))


def evaluate(hi, t, start, a, fail, constant):
    life = float(t[-1])
    out = {'alarm_frac': None if a is None else float(t[a]/life), 'lead_h': None if a is None else life-float(t[a]), 'life_h': life}
    if a is None:
        return out
    ref = np.log(np.maximum(hi[start-BASE:start], 1e-6))
    thr = np.median(ref)+5*1.4826*np.median(np.abs(ref-np.median(ref)))
    y = smooth(np.log(np.maximum(hi, 1e-6)))
    out['sustained'] = float((np.log(np.maximum(hi[a:], 1e-6)) > thr).mean())
    steps = np.arange(a, len(hi)-1, max(1, (len(hi)-a)//50))
    window = max(20, min(120, len(hi)//20))
    hits = {'log': [0, 0], 'wiener': [0, 0], 'hang_so': [0, 0]}
    cover = [0, 0]
    fracs = {}
    for s in steps:
        true = life-t[s]
        if true <= 0:
            continue
        preds = {'log': rul_loglinear(y, t, int(s), a, fail, window)[0], 'hang_so': max(constant-(t[s]-t[a]), 0.)}
        w, band = rul_wiener(y, t, int(s), a, fail)
        preds['wiener'] = w
        if band:
            cover[1] += 1
            cover[0] += band[0] <= true <= band[1]
        for k, v in preds.items():
            if v is not None:
                hits[k][1] += 1
                hits[k][0] += abs(v-true) <= ALPHA*true
    for k, (u, v) in hits.items():
        out[f'alpha_{k}'] = u/v if v else None
        out[f'answered_{k}'] = v/max(len(steps), 1)
    out['pi80_cover'] = cover[0]/cover[1] if cover[1] else None
    for frac in (.5, .9):
        s = int(a+frac*(len(hi)-1-a))
        true = life-t[s]
        fracs[frac] = {'log': rul_loglinear(y, t, s, a, fail, window)[0], 'wiener': rul_wiener(y, t, s, a, fail)[0], 'hang_so': max(constant-(t[s]-t[a]), 0.)}
        for k, v in fracs[frac].items():
            out[f'phm{int(frac*100)}_{k}'] = phm_score(true, v) if v is not None and true > 0 else None
    return out


def load_set(dataset):
    out = {}
    for p in sorted(CACHE.glob(f'{dataset}_*_cheap.npz')):
        name = p.stem[len(dataset)+1:-len('_cheap')]
        a = np.load(p)
        out[name] = (a['x'], a['t'])
    return out


def mean(values):
    v = [x for x in values if x is not None]
    return float(np.mean(v)) if v else None


def trend():
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for dataset in ('femto', 'xjtu', 'ims'):
        data = load_set(dataset)
        for skip in (0, SKIP):
            hi = {}
            for n, (x, t) in data.items():
                if len(x) >= skip+BASE+5:
                    hi[n] = (*hi_series(x, skip), t)
            dev = [n for n in hi if n in DEV[dataset]]
            fail = float(np.median([np.median(np.log(np.maximum(hi[n][0][-5:], 1e-6))) for n in dev]))
            for kind, grid in GRID.items():
                # Chọn h: ít cảnh báo sớm (<50% đời) nhất trên dev, hòa thì cảnh báo sớm hơn.
                rank = []
                for h in grid:
                    frac = []
                    for n in dev:
                        a = alarm(hi[n][0], hi[n][1], kind, h)
                        frac.append(1.1 if a is None else hi[n][2][a]/hi[n][2][-1])
                    rank.append((sum(f < .5 for f in frac), sum(f > 1 for f in frac), float(np.median(frac)), h))
                h = min(rank)[3]
                gaps = [hi[n][2][-1]-hi[n][2][a] for n in dev if (a := alarm(hi[n][0], hi[n][1], kind, h)) is not None]
                constant = float(np.median(gaps)) if gaps else 0.
                rows = {n: evaluate(hi[n][0], hi[n][2], hi[n][1], alarm(hi[n][0], hi[n][1], kind, h), fail, constant)
                        for n in hi if n not in dev}
                ok = [r for r in rows.values() if r['alarm_frac'] is not None]
                missing = [n for n in data if n not in hi and n not in dev]
                results[f'{dataset}/skip{skip}/{kind}'] = {'h': h, 'n': len(rows), 'no_alarm': len(rows)-len(ok), 'not_monitored': missing,
                    'alarm_frac_median': float(np.median([r['alarm_frac'] for r in ok])) if ok else None,
                    'early_lt50': sum(r['alarm_frac'] < .5 for r in ok), 'unstable': sum(r['sustained'] < .5 for r in ok),
                    'lead_median_h': float(np.median([r['lead_h'] for r in ok])) if ok else None,
                    **{f'alpha_{k}': mean([r.get(f'alpha_{k}') for r in ok]) for k in ('log', 'wiener', 'hang_so')},
                    **{f'phm50_{k}': mean([r.get(f'phm50_{k}') for r in ok]) for k in ('log', 'wiener', 'hang_so')},
                    **{f'phm90_{k}': mean([r.get(f'phm90_{k}') for r in ok]) for k in ('log', 'wiener', 'hang_so')},
                    'pi80_cover': mean([r.get('pi80_cover') for r in ok]), 'answered_wiener': mean([r.get('answered_wiener') for r in ok]),
                    'constant_h': constant, 'bearings': rows}
                v = results[f'{dataset}/skip{skip}/{kind}']
                print(f'{dataset:6s}skip{skip:<3d}{kind:7s}h={h:<5}n={v["n"]:<3d}none={v["no_alarm"]} frac={v["alarm_frac_median"] or 0:.2f} early={v["early_lt50"]} unstable={v["unstable"]} lead={v["lead_median_h"] or 0:7.2f}h',
                      'alpha log/wien/const', *[f'{(v[f"alpha_{k}"] or 0):.3f}' for k in ('log', 'wiener', 'hang_so')],
                      'phm50', *[f'{(v[f"phm50_{k}"] or 0):.3f}' for k in ('log', 'wiener', 'hang_so')], f'cover={v["pi80_cover"] or 0:.2f}', flush=True)
    (OUT/'trend.json').write_text(json.dumps(results, indent=1))


def pipeline_job(job):
    """Một ổ, một seed: chạy dòng toàn đời như tại máy, KHÔNG biết tương lai."""
    name, seed, kind, h = job
    label = X.LABEL[name]
    d = X.bearing_data(name)
    fr, orders, n = d['fr'], X.UER204.orders(), d['norm']
    rng = np.random.default_rng([seed, int.from_bytes(name.encode(), 'big') % 2**31])
    sets, _ = X.injected_set(d['raw_base'], fr, orders, X.Prior(), ('inner', 'outer'), X.N_INJECT, rng)
    Xa = np.concatenate([n(d['f']['base'])]+[n(X.axis_features(sets[k], fr, orders)) for k in ('inner', 'outer')])
    ya = np.concatenate([np.zeros(len(d['f']['base']), int)]+[np.full(X.N_INJECT, i+1) for i in range(2)])
    model = RandomForestClassifier(n_estimators=50, max_depth=8, min_samples_leaf=2, max_features='sqrt', bootstrap=False,
                                   class_weight='balanced', random_state=seed, n_jobs=1).fit(Xa, ya)
    full = X.load(name)
    p = X.expand(model.predict_proba(n(X.axis_features(full, fr, orders))), model.classes_)
    sma = X.stream(p)['sma5']
    a = np.load(CACHE/f'xjtu_Bearing{name}_cheap.npz')
    hi, start = hi_series(a['x'], 0)
    i = alarm(hi, start, kind, h)
    N = len(full)
    out = {'name': name, 'seed': seed, 'label': label, 'life_min': N, 'alarm_frac': None if i is None else i/N}
    if label == 'cage':
        out['note'] = 'khong co lop vong cach trong chuoi nay'
    pred = sma[:, 1:3].argmax(1)+1
    raw_fault = sma.argmax(1) != 0
    base_end = X.split(np.arange(N))[0].max()+1
    out['ungated_fault_rate_early_half'] = float(raw_fault[base_end:N//2].mean()) if N//2 > base_end else None
    if i is None:
        return out
    after = pred[i:]
    if label in ('inner', 'outer'):
        k = X.CLASSES.index(label)
        out['type_acc_after_alarm'] = float((after == k).mean())
        out['type_acc_last10pct'] = float((pred[N-max(5, N//10):] == k).mean())
        wrong = np.where(after != k)[0]
        stable = 0 if not len(wrong) else int(wrong[-1])+1
        out['stable_correct_from_frac'] = None if stable >= len(after) else (i+stable)/N
        out['stable_correct_lead_min'] = None if stable >= len(after) else N-(i+stable)
    return out


def pipeline(kind='cusum'):
    trend_res = json.loads((OUT/'trend.json').read_text())
    choice = trend_res[f'xjtu/skip0/{kind}']
    jobs = [(n, s, kind, choice['h']) for n in X.LABEL for s in X.SEEDS]
    with ProcessPoolExecutor(14) as pool:
        rows = list(pool.map(pipeline_job, jobs))
    (OUT/f'pipeline_{kind}.json').write_text(json.dumps({'alarm': kind, 'h': choice['h'], 'rows': rows}, indent=1))
    print('==', kind, 'h', choice['h'])
    for n in X.LABEL:
        r = [x for x in rows if x['name'] == n]
        print(n, r[0]['label'], 'life', r[0]['life_min'], 'alarm', r[0]['alarm_frac'] and round(r[0]['alarm_frac'], 2),
              'after', [round(x.get('type_acc_after_alarm', -1), 2) for x in r], 'last10', [round(x.get('type_acc_last10pct', -1), 2) for x in r],
              'stable_lead_min', [x.get('stable_correct_lead_min') for x in r], 'ungated_early', round(np.mean([x['ungated_fault_rate_early_half'] or 0 for x in r]), 2))


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] == 'trend':
        trend()
    pipeline('cusum')
    pipeline('nguong')
