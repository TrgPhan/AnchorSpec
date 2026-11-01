"""E1 (khám phá): nền dài, gộp theo thời gian, nền nhiều trạng thái có giảm báo nhầm không?

Phần A: FEMTO/XJTU/IMS, đặc trưng cảm biến rẻ đã cache, không dùng dự đoán mới về loại lỗi.
Phần B: CWRU S4: nền một tải, gộp hai tải, chọn lọc theo tải (Mahalanobis nhỏ nhất, DCASE).
Mọi tính toán chỉ dùng quá khứ. Không có nhãn thời điểm khởi phát nên chỉ có thước đo gián tiếp.
"""
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat
from sklearn.covariance import LedoitWolf
from sklearn.metrics import roc_auc_score

from tn3_trend import DEV
from tn1_cwru_cheap import DATA as CW, features_fs
from cheap_sensor import CheapSensor, simulate, windows

ROOT = Path(__file__).resolve().parent
CACHE = ROOT.parent/'data'/'tn3_cache'
OUT = ROOT/'results'/'e1'
BASES, AGGS, Z = (30, 60, 120), (1, 5, 20), (5., 10., 15., 25., 40.)


def load(ds):
    return {p.stem[len(ds)+1:-6]: (np.load(p)['x'], np.load(p)['t']) for p in sorted(CACHE.glob(f'{ds}_*_cheap.npz'))}


def hi_of(x, b):
    base = x[:b]
    inv = np.linalg.pinv(LedoitWolf().fit(base).covariance_)
    d = x-base.mean(0)
    return np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', d, inv, d), 0)/x.shape[1])


def causal_median(y, a):
    return y if a == 1 else np.array([np.median(y[max(0, i-a+1):i+1]) for i in range(len(y))])


def zs(hi, b, a):
    y = np.log(np.maximum(hi, 1e-6))
    ref = y[:b]
    med, mad = np.median(ref), 1.4826*np.median(np.abs(ref-np.median(ref)))+1e-6
    # mức nền của trung vị gộp nhỏ hơn: chuẩn hóa bằng độ lệch của chính chuỗi gộp trên nền
    g = causal_median(y, a)
    gref = g[a-1:b]
    mad_g = 1.4826*np.median(np.abs(gref-np.median(gref)))+1e-6
    return (g-np.median(gref))/mad_g


def first_alarm(z, b, h, persist):
    run = 0
    for i in range(b, len(z)):
        run = run+1 if z[i] > h else 0
        if run >= persist:
            return i
    return None


def part_a():
    out = {}
    for ds in ('femto', 'xjtu', 'ims'):
        data = load(ds)
        for b in BASES:
            for a in AGGS:
                persist = max(1, round(5/a))
                series = {n: (zs(hi_of(x, b), b, a), t) for n, (x, t) in data.items() if len(x) >= b+a+5}
                dev = [n for n in series if n in DEV[ds]]
                if not dev:
                    continue
                rank = []
                for h in Z:
                    fr = [(lambda i: 1.1 if i is None else series[n][1][i]/series[n][1][-1])(first_alarm(series[n][0], b, h, persist)) for n in dev]
                    rank.append((sum(f < .5 for f in fr), sum(f > 1 for f in fr), float(np.median(fr)), h))
                h = min(rank)[3]
                test = [n for n in series if n not in dev]
                fr, unstable, none = [], 0, 0
                for n in test:
                    z, t = series[n]
                    i = first_alarm(z, b, h, persist)
                    if i is None:
                        none += 1
                        continue
                    fr.append(float(t[i]/t[-1]))
                    unstable += float((z[i:] > h).mean()) < .5
                skipped = len([n for n in data if n not in series])
                row = {'h': h, 'n': len(test), 'khong_bao': none, 'khong_du_du_lieu': skipped, 'trung_vi_%doi': float(np.median(fr)) if fr else None,
                       'bao_truoc_50%': sum(f < .5 for f in fr), 'bao_truoc_90%': sum(f < .9 for f in fr), 'dao_dong': int(unstable)}
                out[f'{ds}/B{b}/A{a}'] = row
                print(f'{ds:6s}B={b:<4d}A={a:<3d}', row, flush=True)
    return out


def part_b():
    S = CheapSensor()
    N = round(2048*S.fs_out/12000)
    ids = {'healthy': (97, 98, 99, 100), 'inner': (105, 106, 107, 108), 'outer': (130, 131, 132, 133), 'ball': (118, 119, 120, 121)}
    rpm = (1797, 1772, 1750, 1730)
    F = {}
    for c, row in ids.items():
        for hp, i in enumerate(row):
            m = loadmat(CW/f'{i}.mat')
            raw = np.asarray(m[f'X{i:03d}_DE_time'], float).ravel()
            r = float(np.asarray(m.get(f'X{i:03d}RPM', rpm[hp])).ravel()[0])
            y = simulate(raw, 48000 if c == 'healthy' else 12000, S, np.random.default_rng([0, i]))
            F[(c, hp)] = features_fs(windows(y, N), S.fs_out, r)

    def model(x):
        cut = int(.8*len(x))
        fit, cal = x[:cut], x[cut:]
        inv = np.linalg.pinv(LedoitWolf().fit(fit).covariance_)
        return fit.mean(0), inv, cal

    def dist(x, ms):
        ds = []
        for mu, inv, _ in ms:
            d = x-mu
            ds.append(np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', d, inv, d), 0)))
        return np.min(ds, axis=0)

    def run(name, loads, selective):
        if selective:
            ms = [model(F[('healthy', h)]) for h in loads]
        else:
            ms = [model(np.concatenate([F[('healthy', h)] for h in loads]))]
        cal = np.concatenate([dist(m[2], ms) for m in ms])
        thr = float(np.quantile(cal, .99))
        res = {}
        for hp in (1, 3):
            h = dist(F[('healthy', hp)], ms)
            f = np.concatenate([dist(F[(c, hp)], ms) for c in ('inner', 'outer', 'ball')])
            res[hp] = {'auc': float(roc_auc_score([0]*len(h)+[1]*len(f), np.r_[h, f])), 'bao_nham': float((h > thr).mean()), 'phat_hien': float((f > thr).mean())}
        print(name, {k: {a: round(b, 3) for a, b in v.items()} for k, v in res.items()}, flush=True)
        return res
    return {'mot_tai_0HP': run('mot_tai_0HP', (0,), False), 'hai_tai_gop': run('hai_tai_gop', (0, 2), False), 'hai_tai_chon_loc': run('hai_tai_chon_loc', (0, 2), True)}


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    a = part_a()
    print('== CWRU nhieu trang thai')
    b = part_b()
    (OUT/'e1.json').write_text(json.dumps({'A': a, 'B': b}, indent=1))
