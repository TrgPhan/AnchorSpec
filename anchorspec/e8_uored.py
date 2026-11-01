"""E8: xác nhận một lần trên UORED-VAFCLS. Giao thức: PROTOCOL_E8.md. check -> smoke -> freeze -> test."""
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('OMP_NUM_THREADS', '1')

import numpy as np  # noqa: E402
from scipy import signal, stats  # noqa: E402
from scipy.io import loadmat  # noqa: E402
from sklearn.covariance import LedoitWolf  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import funnel as Fu  # noqa: E402
from bearing import Bearing  # noqa: E402
from cheap_sensor import CheapSensor, simulate  # noqa: E402

MAT = ROOT.parent/'data'/'uored'/'mat'
OUT = ROOT/'results'/'e8'
BEARING = Bearing(8, 6.77, 28.50, 0.)
ORDERS = BEARING.orders()
NOMINAL = 1750/60
SEEDS = (11, 29, 47)
LAB = {**{i: 'inner' for i in range(1, 6)}, **{i: 'outer' for i in range(6, 11)}, **{i: 'ball' for i in range(11, 16)}, **{i: 'cage' for i in range(16, 21)}}
LET = {'inner': 'I', 'outer': 'O', 'ball': 'B', 'cage': 'C'}
KINDS = ('inner', 'outer')
SENSORS = {'1k': CheapSensor(), '6k': CheapSensor(fs_out=16000, bw_hz=6000.)}
ALLOW_FAULT = {'on': False}
UNIT_DIV = 9.81  # coi kênh gia tốc là m/s²; xem nhật ký trong PROTOCOL_E8.md


def raw(i, state):
    """Chặn đọc file lỗi trước giai đoạn test."""
    if state and not ALLOW_FAULT['on']:
        raise PermissionError('Fault file before test stage')
    name = f"H_{i}_0" if state == 0 else f"{LET[LAB[i]]}_{i}_{state}"
    return loadmat(MAT/f'{name}.mat')[name]


def sensed(i, state, sen, col=0):
    x = raw(i, state)[:, col].astype(float)
    x = (x-x.mean())/UNIT_DIV
    return simulate(x, 42000, sen, np.random.default_rng([i, state, 5]))


def windows50(y, n):
    step = n//2
    w = np.stack([y[s:s+n] for s in range(0, len(y)-n+1, step)])
    return (w-w.mean(1, keepdims=True))[:, None, :]


def speed(y, fs):
    n = len(y)
    sp = np.abs(np.fft.rfft((y-y.mean())*signal.get_window('hann', n)))
    f = np.fft.rfftfreq(n, 1/fs)
    c = np.arange(NOMINAL*.97, NOMINAL*1.03, .02)
    sc = [sum(np.interp(v*h, f, sp)/np.median(sp[(f > v*h-5) & (f < v*h+5)]+1e-15) for h in (1, 2, 3)) for v in c]
    return float(c[int(np.argmax(sc))])


def machine(i, sen):
    fs = sen.fs_out
    y = sensed(i, 0, sen)
    w = windows50(y, fs)
    base, hold = w[:11], w[12:]
    fr = speed(y[:6*fs], fs)
    return base, hold, fr


def hi_stats(base, others, fs, bw):
    def fe(x):
        v = x[:, 0]
        r = np.sqrt((v**2).mean(1))+1e-15
        f, p = signal.welch(v, fs, nperseg=256, axis=1)
        e = np.linspace(0, bw, 6)
        return np.column_stack([np.log(r), stats.kurtosis(v, axis=1), np.abs(v).max(1)/r]+[np.log(p[:, (f >= u) & (f < t)].sum(1)+1e-18) for u, t in zip(e[:-1], e[1:])])
    b = fe(base)
    inv = np.linalg.pinv(LedoitWolf().fit(b).covariance_)
    h = lambda x: np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', fe(x)-b.mean(0), inv, fe(x)-b.mean(0)), 0)/b.shape[1])
    ref = np.log(np.maximum(h(base), 1e-6))
    med, mad = np.median(ref), 1.4826*np.median(np.abs(ref-np.median(ref)))+1e-6
    return {k: float(((np.log(np.maximum(h(x), 1e-6))-med)/mad >= 10).mean()) for k, x in others.items()}


def smooth(a, k=5):
    return np.array([a[max(0, i-k+1):i+1].mean(0) for i in range(len(a))])


def job(a):
    i, seed, cfg, smoke, cw, lib = a
    sen = SENSORS[cfg]
    fs, bw = sen.fs_out, float(sen.bw_hz)
    ALLOW_FAULT['on'] = not smoke
    base, hold, fr = machine(i, sen)
    m = Fu.fit_funnel(base, fr, ORDERS, sen, fs, seed, KINDS, max_hz=bw, rng=np.random.default_rng([seed, i, 9]))
    states = {'hold': hold}
    if smoke:  # dùng file khỏe của ổ khác thay file lỗi, chỉ để chạy đường ống
        other = windows50(sensed(i % 20+1, 0, sen), fs)
        states |= {1: other, 2: other}
    else:
        for st in (1, 2):
            states[st] = windows50(sensed(i, st, sen), fs)
    out = {'i': i, 'lab': LAB[i], 'seed': seed, 'cfg': cfg, 'fr_est': fr, 'hi': hi_stats(base, {str(k): v for k, v in states.items()}, fs, bw)}
    k = {'inner': 1, 'outer': 2}.get(LAB[i])
    tau = np.array([m.tau[c] for c in m.kinds])
    for st, w in states.items():
        z = m.z(Fu.feats(w, fs, fr, ORDERS, bw))
        s = smooth(m.scores(z))
        ans = Fu.decide(s, m.physics(z), tau)
        pm = smooth(m.multi_prob(z))
        rec = {'n': len(w), 'tra_loi': float((ans > 0).mean()), 'mo_ho': float(1-s.max(1).mean()), 'ans': np.bincount(ans, minlength=3).tolist(), 'm0': np.bincount(pm.argmax(1), minlength=3).tolist(), 'm0_type': np.bincount(pm[:, 1:].argmax(1)+1, minlength=3).tolist()}
        if cw is not None:
            pc = smooth(cw.predict_proba(z[:, :45]))
            rec['c'] = np.bincount(cw.classes_[pc.argmax(1)], minlength=3).tolist()
        out[str(st)] = rec
    return out


def lobo_job(a):
    """D: lỗi nặng thật từ các ổ khác, cùng cách chuẩn hóa theo nền riêng từng ổ."""
    i, seed, table = a
    X, y = [], []
    for j, f in table.items():
        if j == i or LAB[j] not in KINDS:
            continue
        X += [f['base'], f['fault']]
        y += [np.zeros(len(f['base']), int), np.full(len(f['fault']), 1+KINDS.index(LAB[j]))]
    m = RandomForestClassifier(random_state=seed, **Fu.SMALL).fit(np.concatenate(X), np.concatenate(y))
    f = table[i]
    r = {}
    for st, z in (('hold', f['hold']), ('1', f['dev']), ('2', f['fault'])):
        p = smooth(m.predict_proba(z))
        r[st] = np.bincount(m.classes_[p.argmax(1)], minlength=3).tolist()
    return i, seed, r


def fail_table(sen):
    t = {}
    fs, bw = sen.fs_out, float(sen.bw_hz)
    ALLOW_FAULT['on'] = True
    for i in LAB:
        base, hold, fr = machine(i, sen)
        fb = Fu.feats(base, fs, fr, ORDERS, bw)
        mu, sd = fb.mean(0), fb.std(0)+1e-9
        t[i] = {'base': (fb-mu)/sd, 'hold': (Fu.feats(hold, fs, fr, ORDERS, bw)-mu)/sd,
                'dev': (Fu.feats(windows50(sensed(i, 1, sen), fs), fs, fr, ORDERS, bw)-mu)/sd, 'fault': (Fu.feats(windows50(sensed(i, 2, sen), fs), fs, fr, ORDERS, bw)-mu)/sd}
    return t


def logged_rpm(x):
    """Cột 3 chỉ ghi một giá trị rpm trong cả file, còn lại bằng 0; chỉ để đối chiếu."""
    return float(x[:, 2].max())


def accel_1x(x):
    a = x[:, 0]-x[:, 0].mean()
    sp = np.abs(np.fft.rfft(a*signal.get_window('hann', len(a))))
    f = np.fft.rfftfreq(len(a), 1/42000)
    b = (f > 24) & (f < 36)
    return float(f[b][sp[b].argmax()]*60)


def check():
    rows = []
    for i in LAB:
        x = raw(i, 0)
        a = (x[:, 0]-x[:, 0].mean())/UNIT_DIV
        est = machine(i, SENSORS['1k'])[2]*60
        hr = accel_1x(x)
        rows.append({'i': i, 'rms_g': float(np.std(a)), 'max_g': float(np.abs(a).max()), 'clip8': float((np.abs(a) >= 8).mean()), 'rpm_uoc': est, 'rpm_1x_rong': hr, 'rpm_ghi': logged_rpm(x), 'sai%': abs(est-hr)/hr*100})
    for r in rows:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
    print('sai so toc do trung vi %', round(float(np.median([r['sai%'] for r in rows])), 2), 'max', round(max(r['sai%'] for r in rows), 2))


def code_hashes():
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('e8_uored.py', 'funnel.py', 'features.py', 'injection.py', 'cheap_sensor.py', 'PROTOCOL_E8.md')}


def cwru_model():
    from tn2_paderborn import cwru_features
    c = cwru_features(SENSORS['1k'], 0)
    mu, sd = c['healthy'].mean(0), c['healthy'].std(0)+1e-9
    X = np.concatenate([(c[k]-mu)/sd for k in ('healthy', 'inner', 'outer')])
    y = np.concatenate([np.full(len(c[k]), i) for i, k in enumerate(('healthy', 'inner', 'outer'))])
    return lambda seed: RandomForestClassifier(random_state=seed, **Fu.SMALL).fit(X, y)


def smoke():
    cw = cwru_model()(11)
    r = job((1, 11, '1k', True, cw, None))
    print({k: r[k] for k in ('fr_est', 'hi', 'hold', '2')})
    r6 = job((6, 11, '6k', True, None, None))
    print('6k', r6['2'])


def boot(values, n=10000):
    rng = np.random.default_rng(0)
    v = {k: np.array(x) for k, x in values.items()}
    d = [np.mean([x[rng.integers(len(x), size=len(x))].mean() for x in v.values()]) for _ in range(n)]
    return [float(np.quantile(d, .025)), float(np.quantile(d, .975))]


def test():
    frozen = json.loads((OUT/'FROZEN.json').read_text())
    if frozen != code_hashes():
        raise ValueError('Code/protocol changed after freeze')
    dest = OUT/'test.json'
    if dest.exists():
        raise FileExistsError('Test already opened once')
    ALLOW_FAULT['on'] = True
    cwm = cwru_model()
    jobs = [(i, s, '1k', False, cwm(s), None) for i in LAB for s in SEEDS]+[(i, s, '6k', False, None, None) for i in LAB for s in SEEDS]
    with ProcessPoolExecutor(14) as pool:
        rows = list(pool.map(job, jobs, chunksize=1))
    table = fail_table(SENSORS['1k'])
    with ProcessPoolExecutor(14) as pool:
        d = list(pool.map(lobo_job, [(i, s, table) for i in LAB for s in SEEDS], chunksize=2))
    bearing = {}
    for cfg in SENSORS:
        part = [r for r in rows if r['cfg'] == cfg]
        per = {}
        for i in LAB:
            rs = [r for r in part if r['i'] == i]
            mean = lambda st, key: np.mean([r[st][key] for r in rs], axis=0)
            k = {'inner': 1, 'outer': 2}.get(LAB[i])
            e = {}
            for st in ('hold', '1', '2'):
                ans, m0 = mean(st, 'ans'), mean(st, 'm0')
                t = ans.sum()
                e[st] = {'tra_loi': float(ans[1:].sum()/t), 'dung_khi_tl': float(ans[k]/ans[1:].sum()) if k and ans[1:].sum() else None, 'dung_tat_ca': float(ans[k]/t) if k else None,
                         'm0_acc': float(m0[k]/m0.sum()) if k else None, 'm0_loi': float(m0[1:].sum()/m0.sum()), 'm0_type': float(mean(st, 'm0_type')[k]/m0.sum()) if k else None, 'mo_ho': float(mean(st, 'mo_ho')), 'hi10': float(np.mean([r['hi'][st] for r in rs]))}
                if cfg == '1k':
                    c = mean(st, 'c')
                    e[st]['c_acc'] = float(c[k]/c.sum()) if k else None
                    e[st]['c_loi'] = float(c[1:].sum()/c.sum())
                    dd = np.mean([r[st] for ii, _, r in d if ii == i], axis=0)
                    e[st]['d_acc'] = float(dd[k]/dd.sum()) if k else None
                    e[st]['d_loi'] = float(dd[1:].sum()/dd.sum())
            per[i] = e
        bearing[cfg] = per
    (OUT/'test.json').write_text(json.dumps({'bearing': bearing, 'rows': rows, 'd': d}, indent=1, default=float))
    report()


def report():
    r = json.loads((OUT/'test.json').read_text())
    lab = lambda i: LAB[int(i)]
    res = {}
    for cfg, per in r['bearing'].items():
        cls = lambda c: [k for k in per if lab(k) == c]
        macro = lambda st, key: {c: [per[i][st][key] for i in cls(c) if per[i][st][key] is not None] for c in KINDS}
        m = lambda v: float(np.mean([np.mean(x) for x in v.values()]))
        row = {}
        for st in ('2', '1'):
            row[st] = {'M1_dung_khi_tl': m(macro(st, 'dung_khi_tl')), 'M1_ci': boot(macro(st, 'dung_khi_tl')), 'M1_tra_loi': float(np.mean([per[i][st]['tra_loi'] for c in KINDS for i in cls(c)])), 'M1_dung_tat_ca': m(macro(st, 'dung_tat_ca')),
                       'M0': m(macro(st, 'm0_acc')), 'M0_type': m(macro(st, 'm0_type'))}
            if cfg == '1k':
                row[st]['C'] = m(macro(st, 'c_acc'))
                row[st]['D'] = m(macro(st, 'd_acc'))
            row[st]['hi10_inner_outer'] = float(np.mean([per[i][st]['hi10'] for c in KINDS for i in cls(c)]))
            row[st]['hi10_ball_cage'] = float(np.mean([per[i][st]['hi10'] for c in ('ball', 'cage') for i in cls(c)]))
            row[st]['tra_loi_ball_cage'] = float(np.mean([per[i][st]['tra_loi'] for c in ('ball', 'cage') for i in cls(c)]))
        row['hold_goi_loi_M1'] = float(np.mean([per[i]['hold']['tra_loi'] for i in per]))
        row['hold_goi_loi_M0'] = float(np.mean([per[i]['hold']['m0_loi'] for i in per]))
        row['hold_hi10'] = float(np.mean([per[i]['hold']['hi10'] for i in per]))
        y = [int(lab(i) in ('ball', 'cage')) for i in per]
        s = [per[i]['2']['mo_ho'] for i in per]
        row['auroc_chua_biet'] = float(roc_auc_score(y, s))
        if cfg == '1k':
            d0 = {c: [per[i]['2']['m0_acc']-per[i]['2']['c_acc'] for i in cls(c)] for c in KINDS}
            row['M0_tru_C'] = {'hieu': m(d0), 'ci95': boot(d0)}
            dd = {c: [per[i]['2']['m0_acc']-per[i]['2']['d_acc'] for i in cls(c)] for c in KINDS}
            row['M0_tru_D'] = {'hieu': m(dd), 'ci95': boot(dd)}
            row['theo_lop'] = {c: {'M1_tl': float(np.mean([per[i]['2']['tra_loi'] for i in cls(c)])), 'M1_dung': (lambda v: float(np.mean(v)) if v else None)([per[i]['2']['dung_khi_tl'] for i in cls(c) if per[i]['2']['dung_khi_tl'] is not None]), 'M0': float(np.mean([per[i]['2']['m0_acc'] for i in cls(c)]))} for c in KINDS}
            row['tung_o'] = {i: {'lop': lab(i), 'tl': round(per[i]['2']['tra_loi'], 2), 'dung': None if per[i]['2']['dung_khi_tl'] is None else round(per[i]['2']['dung_khi_tl'], 2), 'm0': None if per[i]['2']['m0_acc'] is None else round(per[i]['2']['m0_acc'], 2), 'c': None if per[i]['2']['c_acc'] is None else round(per[i]['2']['c_acc'], 2), 'hold': round(per[i]['hold']['tra_loi'], 2)} for i in per}
        res[cfg] = row
        print(cfg, json.dumps(row, indent=0, ensure_ascii=False, default=float)[:3900], flush=True)
    (OUT/'summary.json').write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float))


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    stage = sys.argv[1]
    if stage == 'freeze':
        (OUT/'FROZEN.json').write_text(json.dumps(code_hashes(), indent=1))
        print('frozen', code_hashes()['e8_uored.py'][:12])
    else:
        {'check': check, 'smoke': smoke, 'test': test, 'report': report}[stage]()
