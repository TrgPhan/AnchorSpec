"""Logic thí nghiệm X1-X7; chạy được cả cục bộ khi có dữ liệu. Không dùng dịch vụ ngoài trừ tải dữ liệu."""
from collections import defaultdict
import json
import os
from pathlib import Path
import pickle
import subprocess
import tempfile

import numpy as np
from scipy import signal, stats
from scipy.io import loadmat
from sklearn.covariance import LedoitWolf
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

import funnel as Fu
import tn2b_xjtu as X
import e8_uored as U
from bearing import Bearing, PADERBORN_6203
from cheap_sensor import CheapSensor, simulate, windows
from injection import Prior

DATA = Path(__file__).resolve().parent.parent/'data'
S = CheapSensor()
SMALL = Fu.SMALL
PB_ALL = ['K001', 'K002', 'K003', 'K004', 'K005', 'K006', 'KA04', 'KA15', 'KA16', 'KA22', 'KA30', 'KI04', 'KI14', 'KI16', 'KI17', 'KI18', 'KI21']
PB_TEST = ['K004', 'K005', 'K006', 'KA04', 'KA15', 'KA16', 'KA22', 'KA30', 'KI04', 'KI14', 'KI16', 'KI17', 'KI18', 'KI21']
COND = {'N15_M07_F10': 25., 'N09_M07_F10': 15., 'N15_M01_F10': 25., 'N15_M07_F04': 25.}
FULL = {'xjtu': ('healthy', 'inner', 'outer', 'cage'), 'uored': ('healthy', 'inner', 'outer', 'ball', 'cage')}


def names(ds):
    return list(X.LABEL) if ds == 'xjtu' else ([str(i) for i in U.LAB] if ds == 'uored' else PB_ALL)


def lab_of(ds, n):
    return X.LABEL[n] if ds == 'xjtu' else U.LAB[int(n)]


def z_of(fb, *fs):
    mu, sd = fb.mean(0), fb.std(0)+1e-9
    return ((fb-mu)/sd, *[(f-mu)/sd for f in fs])


def store_item(a):
    ds, n = a
    if ds == 'xjtu':
        x = X.load(n).astype(float)
        base, hold, late = X.split(x)
        N = len(x)
        early = x[int(.7*N):int(.9*N)]
        fr, o = X.fr_of(n), X.UER204.orders()
        fb, fh, fe, fl = [Fu.feats(v, 4000, fr, o) for v in (base, hold, early, late)]
    elif ds == 'uored':
        i = int(n)
        U.ALLOW_FAULT['on'] = True
        base, hold, fr = U.machine(i, S)
        o = U.ORDERS
        fb, fh = [Fu.feats(v, 4000, fr, o) for v in (base, hold)]
        fe, fl = [Fu.feats(U.windows50(U.sensed(i, st, S), 4000), 4000, fr, o) for st in (1, 2)]
    else:
        return n, {}
    b, h, e, l = z_of(fb, fh, fe, fl)
    return n, {'base': b, 'hold': h, 'early': e, 'late': l, 'lab': lab_of(ds, n), 'fr': fr, 'mu': fb.mean(0), 'sd': fb.std(0)+1e-9}


def raw_base(ds, n):
    if ds == 'xjtu':
        return X.split(X.load(n).astype(float))[0], X.UER204.orders()
    U.ALLOW_FAULT['on'] = True
    return U.machine(int(n), S)[0], U.ORDERS


def weighted_fit(xs, ys, real_x, real_y, seed):
    """Mỗi lớp tổng trọng số 1; lớp vừa có cấy vừa có thật thì thật chiếm 0,5."""
    X_all = np.concatenate(xs+real_x) if real_x else np.concatenate(xs)
    y_syn = np.concatenate(ys)
    y_real = np.concatenate(real_y) if real_y else np.zeros(0, int)
    y_all = np.r_[y_syn, y_real]
    w = np.zeros(len(y_all))
    for c in np.unique(y_all):
        ms, mr = y_syn == c, y_real == c
        if c == 0 or not mr.any():
            w[:len(y_syn)][ms] = 1/ms.sum() if ms.any() else 0
            if not ms.any():
                w[len(y_syn):][mr] = 1/mr.sum()
            elif mr.any():
                w[:len(y_syn)][ms] = .5/ms.sum()
                w[len(y_syn):][mr] = .5/mr.sum()
        elif not ms.any():
            w[len(y_syn):][mr] = 1/mr.sum()
        else:
            w[:len(y_syn)][ms] = .5/ms.sum()
            w[len(y_syn):][mr] = .5/mr.sum()
    cfg = dict(SMALL, class_weight=None)
    return RandomForestClassifier(random_state=seed, **cfg).fit(X_all, y_all, sample_weight=w*len(y_all))


def x1_job(ds, n, seed, store):
    """E9. Lỗi thật từ ổ khác cùng giàn (ổ đích không có trong học) và từ chính ổ, giai đoạn sớm hơn."""
    cls = FULL[ds]
    t = store[n]
    lab = t['lab']
    k = cls.index(lab)
    rng = np.random.default_rng([seed, sum(map(ord, n)), 7])
    base, orders = raw_base(ds, n)
    fr = t['fr']
    inj = {c: (Fu.feats(Fu.injected(base, c, 150, fr, orders, S, 4000, rng), 4000, fr, orders)-t['mu'])/t['sd'] for c in ('inner', 'outer')}
    xs = [t['base']]+[inj[c] for c in ('inner', 'outer')]
    ys = [np.zeros(len(t['base']), int)]+[np.full(150, cls.index(c)) for c in ('inner', 'outer')]
    sib = {c: [m for m in store if m != n and store[m]['lab'] == c] for c in cls[1:]}

    def score(model):
        p = np.zeros((len(t['late']), len(cls)))
        p[:, model.classes_] = model.predict_proba(t['late'])
        p = np.array([p[max(0, i-4):i+1].mean(0) for i in range(len(p))])
        ph = np.zeros((len(t['hold']), len(cls)))
        ph[:, model.classes_] = model.predict_proba(t['hold'])
        present = [c for c in model.classes_ if c > 0]
        tgf = float((np.array(present)[p[:, present].argmax(1)] == k).mean()) if present else 0.
        return {'acc': float((p.argmax(1) == k).mean()), 'tgf': tgf, 'hold': float((ph.argmax(1) == 0).mean())}

    out = {'ds': ds, 'n': n, 'lab': lab, 'seed': seed, 'A0': score(weighted_fit(xs, ys, [], [], seed))}

    def sib_real(m, kw):
        rx, ry = [], []
        for c, arr in sib.items():
            if not arr:
                continue
            for s in rng.choice(arr, size=min(m, len(arr)), replace=False):
                v = store[s]['late']
                v = v if kw is None else v[rng.choice(len(v), size=min(kw, len(v)), replace=False)]
                rx.append(v)
                ry.append(np.full(len(v), cls.index(c)))
        return rx, ry
    for m in (1, 2, 4):
        for kw in (5, None):
            rx, ry = sib_real(m, kw)
            out[f'S{m}_k{kw or "all"}'] = score(weighted_fit(xs, ys, rx, ry, seed))
            if kw is None:
                out[f'S{m}_all_khong_cay'] = score(weighted_fit([t['base']], [np.zeros(len(t['base']), int)], rx, ry, seed))
    for kw in (3, 5, 10):
        e = t['early'][:kw]
        if len(e) == kw:
            out[f'E{kw}_chinh_o'] = score(weighted_fit(xs, ys, [e], [np.full(kw, k)], seed))
    return out


def x2_bosch():
    """E10. Quy tắc làm mới nền trên dòng dữ liệu theo thời gian; chỉ thêm tệp theo quy tắc của từng nhánh."""
    import e5_bosch as B
    from concurrent.futures import ProcessPoolExecutor
    files = sorted(str(p) for p in (DATA/'bosch_cnc'/'repo'/'data').rglob('*.h5'))
    with ProcessPoolExecutor(8) as pool:
        R = list(pool.map(B.feat, files, chunksize=8))
    key = lambda r: (B.order(r['frame']), r['op'], r['idx'])

    def model(x):
        cut = max(int(.8*len(x)), 5)
        inv = np.linalg.pinv(LedoitWolf().fit(x[:cut]).covariance_)
        mu = x[:cut].mean(0)
        d = lambda v: np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', v-mu, inv, v-mu), 0))
        return d, float(np.quantile(d(x[cut:]), .99))

    def stream(rows, init, window, every, add):
        rows = sorted(rows, key=key)
        buf = []
        res = []
        d = None
        since = 0
        for r in rows:
            if d is None:
                if r['label'] == 'good':
                    buf.append(r['f'])
                if len(buf) >= init:
                    d, t = model(np.array(buf))
                continue
            v = float(d(r['f'][None])[0])
            res.append((v, r['label'], v > t))
            if (add == 'xac_nhan' and r['label'] == 'good') or (add == 'tu_dong' and v <= t):
                buf.append(r['f'])
                since += 1
            if window and since >= every and len(buf) >= init:
                d, t = model(np.array(buf[-window:]))
                since = 0
        return res

    rules = {'co_dinh_theo_nguyen_cong': ('op', 20, None, 0, None), 'co_dinh_gop': ('m', 60, None, 0, None),
             'lam_moi_xac_nhan_op20': ('op', 20, 20, 5, 'xac_nhan'), 'lam_moi_xac_nhan_op40': ('op', 20, 40, 5, 'xac_nhan'),
             'lam_moi_xac_nhan_gop100': ('m', 60, 100, 10, 'xac_nhan'), 'lam_moi_xac_nhan_gop300': ('m', 60, 300, 20, 'xac_nhan'),
             'lam_moi_tu_dong_op40': ('op', 20, 40, 5, 'tu_dong'), 'lam_moi_tu_dong_gop300': ('m', 60, 300, 20, 'tu_dong')}
    out = {}
    for name, (scope, init, w, ev, add) in rules.items():
        groups = defaultdict(list)
        for r in R:
            groups[(r['machine'], r['op']) if scope == 'op' else r['machine']].append(r)
        rec = []
        for g in groups.values():
            rec += stream(g, init, w, ev, add)
        good = [x for x in rec if x[1] == 'good']
        bad = [x for x in rec if x[1] == 'bad']
        out[name] = {'n_good': len(good), 'n_bad': len(bad), 'bao_nham': float(np.mean([x[2] for x in good])), 'phat_hien': float(np.mean([x[2] for x in bad])),
                     'auc': float(roc_auc_score([0]*len(good)+[1]*len(bad), [x[0] for x in good]+[x[0] for x in bad]))}
    return out


def x3_prepare(code):
    out = DATA/'paderborn'/'cond'
    out.mkdir(parents=True, exist_ok=True)
    rar = DATA/'paderborn'/'rar'/f'{code}.rar'
    rar.parent.mkdir(parents=True, exist_ok=True)
    if not rar.exists():
        subprocess.run(['curl', '-sSfL', '--retry', '3', '-o', str(rar), f'https://groups.uni-paderborn.de/kat/BearingDataCenter/{code}.rar'], check=True)
    for cond in COND:
        p = out/f'{code}_{cond}.npy'
        if p.exists():
            continue
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(['bsdtar', '-xf', str(rar), '-C', d, f'{code}/{cond}_{code}_*.mat'], check=True)
            vs = []
            for f in sorted(Path(d, code).glob('*.mat'), key=lambda q: int(q.stem.rsplit('_', 1)[1])):
                s = loadmat(f, squeeze_me=True, struct_as_record=False)[f.stem]
                vs.append(np.asarray({str(y.Name): y for y in s.Y}['vibration_1'].Data, np.float32))
            n = min(map(len, vs))
            np.save(p, np.stack([v[:n] for v in vs]))
    rar.unlink()
    return code


def pb_win(code, cond):
    a = np.load(DATA/'paderborn'/'cond'/f'{code}_{cond}.npy')
    rows = [windows(simulate(v.astype(float)/9.81, 64000, S, np.random.default_rng([i, sum(map(ord, code)), sum(map(ord, cond))])), 4000) for i, v in enumerate(a)]
    return np.concatenate(rows)[:, None, :]


def hi_fe(x):
    v = x[:, 0]
    r = np.sqrt((v**2).mean(1))+1e-15
    f, p = signal.welch(v, 4000, nperseg=256, axis=1)
    return np.column_stack([stats.kurtosis(v, axis=1), np.abs(v).max(1)/r]+[np.log(p[:, (f >= u) & (f < u+200)].sum(1)/(p[:, f <= 1000].sum(1)+1e-18)+1e-18) for u in range(0, 1000, 200)])


def x3_job(code, seed):
    """Nền một điều kiện so với nền từng điều kiện: đổi tốc độ, tải có làm báo nhầm tăng không?"""
    o = PADERBORN_6203.orders()
    lab = 0 if code.startswith('K0') else 2 if code.startswith('KA') else 1
    rng = np.random.default_rng([seed, sum(map(ord, code))])
    ref = 'N15_M07_F10'
    res = {'code': code, 'seed': seed, 'lab': lab}
    base = {c: np.concatenate([pb_win(k, c) for k in ('K001', 'K002', 'K003')]) for c in COND}

    def hi_model(x):
        f = hi_fe(x)
        inv = np.linalg.pinv(LedoitWolf().fit(f).covariance_)
        d = lambda q: np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', hi_fe(q)-f.mean(0), inv, hi_fe(q)-f.mean(0)), 0))
        return d, float(np.quantile(d(x), .99))

    def rf(xb, fr):
        fb = Fu.feats(xb, 4000, fr, o)
        mu, sd = fb.mean(0), fb.std(0)+1e-9
        fi = [(Fu.feats(Fu.injected(xb, c, 100, fr, o, S, 4000, rng), 4000, fr, o)-mu)/sd for c in ('inner', 'outer')]
        Xa = np.concatenate([(fb-mu)/sd]+fi)
        ya = np.r_[np.zeros(len(fb), int), np.ones(100, int), np.full(100, 2)]
        return RandomForestClassifier(random_state=seed, **SMALL).fit(Xa, ya), mu, sd
    d0, t0 = hi_model(base[ref])
    m0, mu0, sd0 = rf(base[ref], COND[ref])
    for cond, fr in COND.items():
        x = pb_win(code, cond)
        dc, tc = hi_model(base[cond])
        mc, muc, sdc = rf(base[cond], fr)
        f = Fu.feats(x, 4000, fr, o)
        res[cond] = {'hi_nen_goc': float((d0(x) > t0).mean()), 'hi_nen_dung': float((dc(x) > tc).mean()), 'rf_nen_goc': float((m0.predict((f-mu0)/sd0) == lab).mean()), 'rf_nen_dung': float((mc.predict((f-muc)/sdc) == lab).mean())}
    return res


def x4_mic():
    """Micro so với rung trên UORED. Chỉ dùng học từ ổ khác (lỗi thật), không cấy, vì công thức cấy là của rung."""
    from concurrent.futures import ProcessPoolExecutor
    out = {}
    for cfg, col, sen in (('rung_1k', 0, S), ('rung_6k', 0, CheapSensor(fs_out=16000, bw_hz=6000.)), ('mic_1k', 1, CheapSensor(noise_ug_rthz=0, range_g=None, bits=None)), ('mic_6k', 1, CheapSensor(fs_out=16000, bw_hz=6000., noise_ug_rthz=0, range_g=None, bits=None))):
        with ProcessPoolExecutor(8) as p:
            T = dict(p.map(_mic_item, [(i, col, sen) for i in U.LAB]))
        cls = ('healthy', 'inner', 'outer', 'ball', 'cage')
        per = defaultdict(list)
        for st in ('s1', 's2'):
            for i in U.LAB:
                k = cls.index(U.LAB[i])
                preds = []
                for seed in (11, 29, 47):
                    Xa = np.concatenate([T[j][q] for j in U.LAB if j != i for q in ('base', 's2')]+[T[i]['base']])
                    ya = np.concatenate([np.r_[np.zeros(len(T[j]['base']), int), np.full(len(T[j]['s2']), cls.index(U.LAB[j]))] for j in U.LAB if j != i]+[np.zeros(len(T[i]['base']), int)])
                    m = RandomForestClassifier(random_state=seed, **SMALL).fit(Xa, ya)
                    preds.append((m.predict(T[i][st]) == k).mean())
                per[st, U.LAB[i]].append(float(np.mean(preds)))
        tab = {f'{st}/{c}': float(np.mean(per[st, c])) for st in ('s1', 's2') for c in ('inner', 'outer', 'ball', 'cage')}
        for st in ('s1', 's2'):
            tab[f'{st}/macro4'] = float(np.mean([tab[f'{st}/{c}'] for c in ('inner', 'outer', 'ball', 'cage')]))
        out[cfg] = tab
    return out


def _mic_item(a):
    i, col, sen = a
    U.ALLOW_FAULT['on'] = True
    fs, bw = sen.fs_out, float(sen.bw_hz)

    def get(st):
        x = U.raw(i, st)[:, col].astype(float)
        x = x-x.mean()
        if col == 0:
            x = x/U.UNIT_DIV
        return simulate(x, 42000, sen, np.random.default_rng([i, st, 5]) if sen.noise_ug_rthz > 0 else None)
    y0 = get(0)
    w = U.windows50(y0, fs)
    base, hold = w[:11], w[12:]
    fr = 1782/60
    fb = Fu.feats(base, fs, fr, U.ORDERS, bw)
    mu, sd = fb.mean(0), fb.std(0)+1e-9
    z = lambda v: (Fu.feats(v, fs, fr, U.ORDERS, bw)-mu)/sd
    return i, {'base': (fb-mu)/sd, 'hold': z(hold), 's1': z(U.windows50(get(1), fs)), 's2': z(U.windows50(get(2), fs))}


def x5_job(ds, n, seed):
    """Công thức cấy cho băng rộng: mode tới gần 6 kHz; so với tiên nghiệm cũ ở cùng cảm biến 6 kHz."""
    sen = CheapSensor(fs_out=16000, bw_hz=6000.)
    fs, bw = 16000, 6000.
    wide = Prior(fn_low_hz=(150., 5500.), fn_high_hz=(2000., 7500.), high_ratio=(0., 3.))
    if ds == 'xjtu':
        x = np.load(DATA/'xjtu'/'cache_bw'/f'6k_16kHz_8g_{n}.npy', mmap_mode='r')
        base, hold, _ = X.split(np.arange(len(x)))
        base = np.asarray(x[base], float)
        late = np.asarray(x[len(x)-max(5, len(x)//10):], float)
        fr, o = X.fr_of(n), X.UER204.orders()
        k = {'inner': 1, 'outer': 2}.get(X.LABEL[n])
    else:
        U.ALLOW_FAULT['on'] = True
        i = int(n)
        base, hold, fr = U.machine(i, sen)
        o = U.ORDERS
        late = U.windows50(U.sensed(i, 2, sen), fs)
        k = {'inner': 1, 'outer': 2}.get(U.LAB[i])
    res = {'ds': ds, 'n': n, 'seed': seed, 'lab': lab_of(ds, n)}
    fb = Fu.feats(base, fs, fr, o, bw)
    mu, sd = fb.mean(0), fb.std(0)+1e-9
    fl = (Fu.feats(late, fs, fr, o, bw)-mu)/sd
    for name, prior in (('cu', Prior()), ('rong', wide)):
        rng = np.random.default_rng([seed, sum(map(ord, n)), 3])
        fi = [(Fu.feats(Fu.injected(base, c, 150, fr, o, sen, fs, rng, prior), fs, fr, o, bw)-mu)/sd for c in ('inner', 'outer')]
        m = RandomForestClassifier(random_state=seed, **SMALL).fit(np.concatenate([(fb-mu)/sd]+fi), np.r_[np.zeros(len(fb), int), np.ones(150, int), np.full(150, 2)])
        p = m.predict_proba(fl)
        res[name] = {'acc': float((p.argmax(1) == k).mean()) if k else None, 'tgf': float((p[:, 1:].argmax(1)+1 == k).mean()) if k else None, 'goi_loi': float((p.argmax(1) > 0).mean())}
    return res


def x6_job(ds, n, seed):
    """CNN 1D đối chứng, GPU. A: cấy vào nền chính ổ. D: lỗi thật từ ổ khác (cả vòng cách, bi nếu có)."""
    import torch
    from torch import nn
    torch.manual_seed(seed)
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    cls = FULL[ds]
    lab = lab_of(ds, n)
    k = cls.index(lab)
    rng = np.random.default_rng([seed, sum(map(ord, n))])

    def get(m):
        if ds == 'xjtu':
            x = X.load(m).astype(float)
            b, h, l = X.split(x)
            return b, h, l, X.fr_of(m), X.UER204.orders()
        U.ALLOW_FAULT['on'] = True
        b, h, fr = U.machine(int(m), S)
        return b, h, U.windows50(U.sensed(int(m), 2, S), 4000), fr, U.ORDERS
    base, hold, late, fr, o = get(n)
    sc = lambda v, b: (v-v.mean(-1, keepdims=True))/(np.sqrt((b**2).mean(axis=(0, 2), keepdims=True))+1e-9)
    inj = {c: Fu.injected(base, c, 150, fr, o, S, 4000, rng) for c in ('inner', 'outer')}
    XA = np.concatenate([sc(base, base)]+[sc(inj[c], base) for c in inj])
    yA = np.r_[np.zeros(len(base), int), np.full(150, cls.index('inner')), np.full(150, cls.index('outer'))]
    xs, ys = [sc(base, base)], [np.zeros(len(base), int)]
    for m in names(ds):
        if m == n:
            continue
        b, _, l, _, _ = get(m)
        xs += [sc(b, b), sc(l, b)]
        ys += [np.zeros(len(b), int), np.full(len(l), cls.index(lab_of(ds, m)))]
    XD, yD = np.concatenate(xs), np.concatenate(ys)
    ch = base.shape[1]

    def train(Xt, yt):
        net = nn.Sequential(nn.Conv1d(ch, 16, 64, 8, 28), nn.BatchNorm1d(16), nn.ReLU(), nn.MaxPool1d(2), nn.Conv1d(16, 32, 3, padding=1), nn.BatchNorm1d(32), nn.ReLU(), nn.MaxPool1d(2),
                            nn.Conv1d(32, 64, 3, padding=1), nn.BatchNorm1d(64), nn.ReLU(), nn.AdaptiveAvgPool1d(4), nn.Flatten(), nn.Linear(256, 64), nn.ReLU(), nn.Linear(64, len(cls))).to(dev)
        opt = torch.optim.Adam(net.parameters(), 1e-3)
        cw = np.bincount(yt, minlength=len(cls)).astype(float)
        w = torch.tensor(np.where(cw > 0, len(yt)/(cw+1e-9), 0.), dtype=torch.float32, device=dev)
        loss_fn = nn.CrossEntropyLoss(weight=w)
        Xd, yd = torch.tensor(Xt, dtype=torch.float32, device=dev), torch.tensor(yt, device=dev)
        for _ in range(30):
            net.train()
            perm = torch.randperm(len(yd), device=dev)
            for i in range(0, len(yd), 32):
                idx = perm[i:i+32]
                if len(idx) < 2:
                    continue
                opt.zero_grad()
                loss_fn(net(Xd[idx]), yd[idx]).backward()
                opt.step()
        net.eval()
        return net

    def pred(net, v):
        with torch.no_grad():
            return net(torch.tensor(sc(v, base), dtype=torch.float32, device=dev)).softmax(1).cpu().numpy()
    out = {'ds': ds, 'n': n, 'lab': lab, 'seed': seed, 'dev': dev}
    for arm, (Xt, yt) in (('A_cay', (XA, yA)), ('D_that', (XD, yD))):
        net = train(Xt, yt)
        p, ph = pred(net, late), pred(net, hold)
        out[arm] = {'acc': float((p.argmax(1) == k).mean()), 'hold': float((ph.argmax(1) == 0).mean()), 'tgf': float((p[:, 1:].argmax(1)+1 == k).mean())}
    return out


GEO = {4: (20, 47, 7.6, 8), 5: (25, 52, 7.8, 9), 6: (30, 62, 9.0, 9), 7: (35, 72, 11.0, 9), 8: (40, 80, 12.0, 9)}


def hust_machines():
    return [f'{s}0{l}' for s in GEO for l in (0, 2, 4)]


def x7_prepare():
    import requests
    d = DATA/'hust'
    d.mkdir(exist_ok=True)
    fs = requests.get('https://data.mendeley.com/public-api/datasets/cbv7jyx4p9/files', params={'folder_id': '72793f17-cac2-4cc6-ac18-2b047e0d45f8', 'version': 3}, headers={'User-Agent': 'curl/8'}, timeout=60).json()
    import hashlib
    bad = 0
    for f in fs:
        p = d/f['filename']
        if not p.exists():
            p.write_bytes(requests.get(f['content_details']['download_url'], headers={'User-Agent': 'curl/8'}, timeout=300).content)
        if hashlib.sha256(p.read_bytes()).hexdigest() != f['content_details']['sha256_hash']:
            bad += 1
    return {'n': len(fs), 'bad': bad}


def _hust(code):
    return loadmat(DATA/'hust'/f'{code}.mat', squeeze_me=True)


def x7_job(machine, seed):
    size = int(machine[0])
    d, D, ball, nb = GEO[size]
    o = Bearing(nb, ball, (d+D)/2, 0.).orders()
    m = _hust(f'N{machine}')
    x0 = np.asarray(m['data'], float).ravel()
    fr = float(np.mean(m['fs'])) if 'fs' in m else 30.
    unit = 9.81 if np.std(x0) > 2 else 1.  # quyết định chỉ từ tệp N, theo giao thức
    sens = lambda v, seq: simulate((v-v.mean())/unit, 51200, S, np.random.default_rng(seq))
    y = sens(x0, [seed, size, 1])
    w = U.windows50(y, 4000)
    base, hold = w[:11], w[12:]
    f = Fu.fit_funnel(base, fr, o, S, 4000, seed, ('inner', 'outer'))
    res = {'machine': machine, 'seed': seed, 'fr': fr, 'unit': unit}
    tau = np.array([f.tau[k] for k in f.kinds])
    states = {'hold': hold}
    for t in ('I', 'O', 'B', 'IO', 'IB', 'OB'):
        p = DATA/'hust'/f'{t}{machine}.mat'
        if p.exists():
            states[t] = U.windows50(sens(np.asarray(_hust(f'{t}{machine}')['data'], float).ravel(), [seed, size, sum(map(ord, t))]), 4000)
    hi = U.hi_stats(base, states, 4000, 1000.)
    for t, v in states.items():
        z = f.z(Fu.feats(v, 4000, fr, o))
        s = np.array([f.scores(z)[max(0, i-4):i+1].mean(0) for i in range(len(z))])
        ans = Fu.decide(s, f.physics(z), tau)
        pm = f.multi_prob(z)
        pm = np.array([pm[max(0, i-4):i+1].mean(0) for i in range(len(pm))])
        res[t] = {'ans': np.bincount(ans, minlength=3).tolist(), 'm0': np.bincount(pm.argmax(1), minlength=3).tolist(), 'mo_ho': float(1-s.max(1).mean()), 'hi10': hi[t], 'n': len(z)}
    return res


def x8_job(ds, n, seed):
    """Giao thức PROTOCOL_X8: tiên nghiệm cũ/rộng ở 1 kHz và 6 kHz, có đo báo nhầm."""
    wide = Prior(fn_low_hz=(150., 5500.), fn_high_hz=(2000., 7500.), high_ratio=(0., 3.))
    cfgs = {'1k': (CheapSensor(), 4000, 1000.), '6k': (CheapSensor(fs_out=16000, bw_hz=6000.), 16000, 6000.)}
    res = {'ds': ds, 'n': n, 'seed': seed}
    if ds == 'hust':
        size = int(n[0])
        d, D, ball, nb = GEO[size]
        o = Bearing(nb, ball, (d+D)/2, 0.).orders()
        m = _hust(f'N{n}')
        x0 = np.asarray(m['data'], float).ravel()
        fr = float(np.mean(m['fs'])) if 'fs' in m else 30.
        unit = 9.81 if np.std(x0) > 2 else 1.
        res['lab'] = 'many'
    else:
        res['lab'] = lab_of(ds, n)
    for bw_name, (sen, fs, bw) in cfgs.items():
        if ds == 'hust':
            sens = lambda v, tag: simulate((v-v.mean())/unit, 51200, sen, np.random.default_rng([seed, size, tag]))
            w = U.windows50(sens(x0, 1), fs)
            base, hold = w[:11], w[12:]
            tests = {t: U.windows50(sens(np.asarray(_hust(f'{t}{n}')['data'], float).ravel(), sum(map(ord, t))), fs) for t in ('I', 'O', 'B', 'IO', 'IB', 'OB') if (DATA/'hust'/f'{t}{n}.mat').exists()}
        elif ds == 'xjtu':
            fr, o = X.fr_of(n), X.UER204.orders()
            x = X.load(n) if bw_name == '1k' else np.load(DATA/'xjtu'/'cache_bw'/f'6k_16kHz_8g_{n}.npy', mmap_mode='r')
            ib, ih, _ = X.split(np.arange(len(x)))
            base, hold = np.asarray(x[ib], float), np.asarray(x[ih], float)
            tests = {'late': np.asarray(x[len(x)-max(5, len(x)//10):], float)}
        else:
            U.ALLOW_FAULT['on'] = True
            base, hold, fr = U.machine(int(n), sen)
            o = U.ORDERS
            tests = {'late': U.windows50(U.sensed(int(n), 2, sen), fs)}
        fb = Fu.feats(base, fs, fr, o, bw)
        mu, sd = fb.mean(0), fb.std(0)+1e-9
        zt = lambda v: (Fu.feats(v, fs, fr, o, bw)-mu)/sd
        zh, zs = zt(hold), {t: zt(v) for t, v in tests.items()}
        for pn, prior in (('cu', Prior()), ('rong', wide)):
            rng = np.random.default_rng([seed, sum(map(ord, n)), 8])
            fi = [zt(Fu.injected(base, c, 150, fr, o, sen, fs, rng, prior)) for c in ('inner', 'outer')]
            clf = RandomForestClassifier(random_state=seed, **SMALL).fit(np.concatenate([(fb-mu)/sd]+fi), np.r_[np.zeros(len(fb), int), np.ones(150, int), np.full(150, 2)])
            r = {'hold_loi': float((clf.predict(zh) > 0).mean()), 'hold_n': len(zh)}
            for t, z in zs.items():
                r[t] = np.bincount(clf.predict(z), minlength=3).tolist()
            res[f'{bw_name}_{pn}'] = r
    return res


def x9_job(ds, n, seed):
    """Khám phá sau X8: 1k_cu và 6k_rong qua phễu đã freeze. Không lật kết quả X8."""
    wide = Prior(fn_low_hz=(150., 5500.), fn_high_hz=(2000., 7500.), high_ratio=(0., 3.))
    res = {'ds': ds, 'n': n, 'seed': seed, 'lab': 'many' if ds == 'hust' else lab_of(ds, n)}
    for arm, sen, fs, bw, prior in (('1k_cu', CheapSensor(), 4000, 1000., None), ('6k_rong', CheapSensor(fs_out=16000, bw_hz=6000.), 16000, 6000., wide)):
        if ds == 'hust':
            size = int(n[0])
            d, D, ball, nb = GEO[size]
            o = Bearing(nb, ball, (d+D)/2, 0.).orders()
            m = _hust(f'N{n}')
            x0 = np.asarray(m['data'], float).ravel()
            fr = float(np.mean(m['fs'])) if 'fs' in m else 30.
            unit = 9.81 if np.std(x0) > 2 else 1.
            sens = lambda v, tag: simulate((v-v.mean())/unit, 51200, sen, np.random.default_rng([seed, size, tag]))
            w = U.windows50(sens(x0, 1), fs)
            base, hold = w[:11], w[12:]
            tests = {t: U.windows50(sens(np.asarray(_hust(f'{t}{n}')['data'], float).ravel(), sum(map(ord, t))), fs) for t in ('I', 'O') if (DATA/'hust'/f'{t}{n}.mat').exists()}
        elif ds == 'xjtu':
            fr, o = X.fr_of(n), X.UER204.orders()
            x = X.load(n) if arm == '1k_cu' else np.load(DATA/'xjtu'/'cache_bw'/f'6k_16kHz_8g_{n}.npy', mmap_mode='r')
            ib, ih, _ = X.split(np.arange(len(x)))
            base, hold = np.asarray(x[ib], float), np.asarray(x[ih], float)
            tests = {'late': np.asarray(x[len(x)-max(5, len(x)//10):], float)}
        else:
            U.ALLOW_FAULT['on'] = True
            base, hold, fr = U.machine(int(n), sen)
            o = U.ORDERS
            tests = {'late': U.windows50(U.sensed(int(n), 2, sen), fs)}
        f = Fu.fit_funnel(base, fr, o, sen, fs, seed, ('inner', 'outer'), max_hz=bw, prior=prior)
        tau = np.array([f.tau[k] for k in f.kinds])
        r = {}
        for t, v in {'hold': hold, **tests}.items():
            z = f.z(Fu.feats(v, fs, fr, o, bw))
            s = np.array([f.scores(z)[max(0, i-4):i+1].mean(0) for i in range(len(z))])
            r[t] = np.bincount(Fu.decide(s, f.physics(z), tau), minlength=3).tolist()
        res[arm] = r
    return res
