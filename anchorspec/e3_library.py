"""E3 (khám phá): thêm thư viện lỗi thật công khai và đặc trưng bất biến có giúp không?

Mỗi ổ đích huấn luyện riêng: A0 (cấy vào nền của nó), L (ổ thật từ BỘ DỮ LIỆU KHÁC), A0+L, và bản chỉ dùng cột
không phụ thuộc thang Hz tuyệt đối. Mô hình RF 50 cây. Một trục mỗi lần, hai trục thì trung bình xác suất.
"""
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('OMP_NUM_THREADS', '1')

import numpy as np  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import funnel as Fu  # noqa: E402
import tn2b_xjtu as X  # noqa: E402
import tn2c_ims as I  # noqa: E402
from bearing import PADERBORN_6203  # noqa: E402
from cheap_sensor import CheapSensor  # noqa: E402
from e2_funnel import pb_load  # noqa: E402
from features import extract  # noqa: E402
from tn2_paderborn import cwru_features  # noqa: E402

OUT = ROOT/'results'/'e3'
S = CheapSensor()
SEEDS = (11, 29, 47)
LABS = ('healthy', 'inner', 'outer')
INV = np.r_[0:4, 16:45]  # bỏ 10 băng và trọng tâm, độ trải theo Hz
ARMS = ('A0', 'L', 'A0+L', 'A0+L_bat_bien', 'A0_bat_bien')
LIB = {}
O = PADERBORN_6203.orders()


def lib_build():
    rows = []  # (bộ, ổ, X, y)
    for n, lab in X.LABEL.items():
        if lab == 'cage':
            continue
        fr, o = X.fr_of(n), X.UER204.orders()
        base, hold, late = X.split(X.load(n).astype(float))
        b = Fu.feats(base, 4000, fr, o)
        mu, sd = b.mean(0), b.std(0)+1e-9
        for a in range(2):
            pick = slice(a*45, (a+1)*45)
            rows.append(('xjtu', n, ((b-mu)/sd)[:, pick], np.zeros(len(b), int)))
            rows.append(('xjtu', n, ((Fu.feats(late, 4000, fr, o)-mu)/sd)[:, pick], np.full(len(late), LABS.index(lab))))
    pb_base = np.concatenate([pb_load(c) for c in ('K001', 'K002', 'K003')])
    fb = Fu.feats(pb_base, 4000, 25., O)
    mu, sd = fb.mean(0), fb.std(0)+1e-9
    rows.append(('paderborn', 'K', (fb-mu)/sd, np.zeros(len(fb), int)))
    for c in ['KA01', 'KA03', 'KA04', 'KA05', 'KA06', 'KA07', 'KA08', 'KA09', 'KA15', 'KA16', 'KA22', 'KA30', 'KI01', 'KI03', 'KI04', 'KI05', 'KI07', 'KI08', 'KI14', 'KI16', 'KI17', 'KI18', 'KI21']:
        f = (Fu.feats(pb_load(c), 4000, 25., O)-mu)/sd
        rows.append(('paderborn', c, f, np.full(len(f), 1 if c.startswith('KI') else 2)))
    c = cwru_features(S, 0)
    mu, sd = c['healthy'].mean(0), c['healthy'].std(0)+1e-9
    for i, k in enumerate(LABS):
        rows.append(('cwru', k, (c[k]-mu)/sd, np.full(len(c[k]), i)))
    for n, lab in I.LABEL.items():
        x = np.load(I.CACHE/f'{n}.npy').astype(float)[:, None, :]
        b = Fu.feats(x[:30], 4000, I.FR, I.ORDERS)
        mu, sd = b.mean(0), b.std(0)+1e-9
        late = (Fu.feats(x[-max(5, len(x)//10):], 4000, I.FR, I.ORDERS)-mu)/sd
        rows.append(('ims', n, (b-mu)/sd, np.zeros(30, int)))
        rows.append(('ims', n, late, np.full(len(late), LABS.index(lab))))
    return rows


def target(ds, name):
    if ds == 'xjtu':
        base, hold, late = X.split(X.load(name).astype(float))
        return base, hold, late, X.fr_of(name), X.UER204.orders(), X.LABEL[name]
    if ds == 'ims':
        x = np.load(I.CACHE/f'{name}.npy').astype(float)[:, None, :]
        return x[:30], x[30:35], x[-max(5, len(x)//10):], I.FR, I.ORDERS, I.LABEL[name]
    base = np.concatenate([pb_load(c) for c in ('K001', 'K002', 'K003')])
    hold = np.concatenate([pb_load(c) for c in ('K004', 'K005', 'K006')])
    return base, hold, pb_load(name), 25., O, 'inner' if name.startswith('KI') else 'outer'


def job(a):
    ds, name, seed = a
    base, hold, late, fr, o, lab = target(ds, name)
    rng = np.random.default_rng([seed, sum(map(ord, name))])
    k = LABS.index(lab)
    fb = Fu.feats(base, 4000, fr, o)
    mu, sd = fb.mean(0), fb.std(0)+1e-9
    n_ax = base.shape[1]
    z = lambda f: (f-mu)/sd
    h0 = z(fb)
    inj = {c: z(Fu.feats(Fu.injected(base, c, 150, fr, o, S, 4000, rng), 4000, fr, o)) for c in LABS[1:]}
    split = lambda m: np.concatenate([m[:, a*45:(a+1)*45] for a in range(n_ax)])
    Xa = np.concatenate([split(h0)]+[split(inj[c]) for c in LABS[1:]])
    ya = np.concatenate([np.zeros(len(h0)*n_ax, int)]+[np.full(150*n_ax, i+1) for i in range(2)])
    lx = np.concatenate([r[2] for r in LIB['rows'] if r[0] != ds])
    ly = np.concatenate([r[3] for r in LIB['rows'] if r[0] != ds])
    late_z, hold_z = z(Fu.feats(late, 4000, fr, o)), z(Fu.feats(hold, 4000, fr, o))
    out = {'ds': ds, 'name': name, 'lab': lab, 'seed': seed}

    def fit_eval(arm, Xt, yt, cols=None, w=None):
        c = cols if cols is not None else np.arange(45)
        m = RandomForestClassifier(random_state=seed, **Fu.SMALL).fit(Xt[:, c], yt, sample_weight=w)
        prob = lambda q: np.mean([m.predict_proba(q[:, a*45:(a+1)*45][:, c]) for a in range(n_ax)], axis=0)
        cl = m.classes_
        pl, ph = cl[prob(late_z).argmax(1)], cl[prob(hold_z).argmax(1)]
        out[arm] = {'late': float((pl == k).mean()), 'hold': float((ph == 0).mean()), 'tgf': float((prob(late_z)[:, 1:].argmax(1)+1 == k).mean()) if len(cl) == 3 else None}
    fit_eval('A0', Xa, ya)
    fit_eval('A0_bat_bien', Xa, ya, INV)
    fit_eval('L', np.concatenate([split(h0), lx]), np.concatenate([np.zeros(len(h0)*n_ax, int), ly]))
    Xm = np.concatenate([Xa, lx])
    ym = np.concatenate([ya, ly])
    w = np.r_[np.full(len(ya), .5/len(ya)), np.full(len(ly), .5/len(ly))]*len(ym)
    fit_eval('A0+L', Xm, ym, w=w)
    fit_eval('A0+L_bat_bien', Xm, ym, INV, w)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    LIB['rows'] = lib_build()
    print('thu vien', {d: sum(len(r[2]) for r in LIB['rows'] if r[0] == d) for d in ('xjtu', 'paderborn', 'cwru', 'ims')}, flush=True)
    jobs = [('xjtu', n, s) for n, l in X.LABEL.items() if l != 'cage' for s in SEEDS]
    jobs += [('paderborn', c, s) for c in ('KA04', 'KA15', 'KA16', 'KA30', 'KA22', 'KI04', 'KI14', 'KI16', 'KI17', 'KI18', 'KI21') for s in SEEDS]
    jobs += [('ims', n, s) for n in I.LABEL for s in SEEDS]
    with ProcessPoolExecutor(14) as pool:
        rows = list(pool.map(job, jobs))
    tab = {}
    for ds in ('xjtu', 'paderborn', 'ims'):
        part = [r for r in rows if r['ds'] == ds]
        for arm in ARMS:
            per = {}
            for lab in ('inner', 'outer'):
                names = sorted({r['name'] for r in part if r['lab'] == lab})
                per[lab] = float(np.mean([np.mean([r[arm]['late'] for r in part if r['name'] == n]) for n in names]))
            tab[f'{ds}/{arm}'] = {'macro': .5*(per['inner']+per['outer']), **per, 'binh_thuong': float(np.mean([r[arm]['hold'] for r in part])),
                                  'tgf': float(np.mean([r[arm]['tgf'] for r in part if r[arm]['tgf'] is not None]))}
            print(ds, arm, {k: round(v, 3) for k, v in tab[f'{ds}/{arm}'].items()}, flush=True)
    (OUT/'e3.json').write_text(json.dumps({'table': tab, 'rows': rows}, indent=1, default=float))


if __name__ == '__main__':
    main()
