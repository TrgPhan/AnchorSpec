"""E2 (khám phá; XJTU, IMS, Paderborn đã mở): phân loại luôn trả lời so với được nói "chưa rõ".

Chỉ số: tỉ lệ trả lời và độ đúng khi trả lời, macro theo ổ và lớp, 10% cuối đời.
Ổ vòng cách không có công thức ở đây: phải được từ chối. Ngưỡng tự động từ lỗi cấy; có thêm lưới.
"""
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('OMP_NUM_THREADS', '1')

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import funnel as Fu  # noqa: E402
import tn2b_xjtu as X  # noqa: E402
from bearing import PADERBORN_6203  # noqa: E402
from cheap_sensor import CheapSensor, simulate, windows  # noqa: E402
from features import extract  # noqa: E402
import tn2c_ims as I  # noqa: E402

OUT = ROOT/'results'/'e2'
SEEDS = (11, 29, 47)
S = CheapSensor()
GRID = (.3, .5, .6, .7, .8, .9)
KINDS = ('inner', 'outer')


def smooth(a, k=5):
    return np.array([a[max(0, i-k+1):i+1].mean(0) for i in range(len(a))])


def evaluate(model, f_late, f_hold, label, k_smooth=True):
    """Trả các phương án: dict tên -> (đáp_án_late, đáp_án_hold). 0 = chưa rõ / bình thường tùy cột."""
    out = {}
    for name, f, in (('late', f_late), ('hold', f_hold)):
        z = model.z(f)
        s, e = model.scores(z), model.physics(z)
        if k_smooth:
            s, e = smooth(s), smooth(e)
        out[name] = (s, e, smooth(model.multi_prob(z)) if k_smooth else model.multi_prob(z))
    res = {}
    tau_auto = np.array([model.tau[k] for k in model.kinds])
    plans = {'M1_ovr_nguong_tu_dong': (tau_auto, .1, None), 'M2_ovr_tu_dong_co_vat_ly': (tau_auto, .1, 1.)}
    for t in GRID:
        plans[f'M1_ovr_t{t}'] = (np.full(len(tau_auto), t), .1, None)
        plans[f'M2_ovr_t{t}_vat_ly'] = (np.full(len(tau_auto), t), .1, 1.)
    late, hold = out['late'], out['hold']
    for name, (tau, m, ph) in plans.items():
        a = Fu.decide(late[0], late[1], tau, m, ph)
        h = Fu.decide(hold[0], hold[1], tau, m, ph)
        res[name] = (a, h)
    # M0 luôn trả lời: bản nhiều lớp, argmax, 0 = gọi bình thường
    res['M0_luon_tra_loi'] = (late[2].argmax(1), hold[2].argmax(1))
    res['M3_chi_so_loi_khi_chac'] = (np.where(late[2][:, 1:].max(1) >= .6, late[2][:, 1:].argmax(1)+1, 0), np.where(hold[2][:, 1:].max(1) >= .6, hold[2][:, 1:].argmax(1)+1, 0))
    return {n: {'late_counts': np.bincount(a, minlength=3).tolist(), 'hold_fault': float((h > 0).mean()), 'n_late': len(a), 'n_hold': len(h)} for n, (a, h) in res.items()}


def xjtu_job(a):
    name, seed = a
    x = X.load(name).astype(float)
    base, hold, late = X.split(x)
    m = Fu.fit_funnel(base, X.fr_of(name), X.UER204.orders(), S, 4000, seed, KINDS)
    fr, o = X.fr_of(name), X.UER204.orders()
    return 'xjtu', name, X.LABEL[name], seed, evaluate(m, Fu.feats(late, 4000, fr, o), Fu.feats(hold, 4000, fr, o), X.LABEL[name])


def ims_job(a):
    name, seed = a
    x = np.load(I.CACHE/f'{name}.npy').astype(float)[:, None, :]
    late, base = x[-max(5, len(x)//10):], x[:30]
    hold = x[30:35]
    m = Fu.fit_funnel(base, I.FR, I.ORDERS, S, 4000, seed, KINDS)
    lab = I.LABEL.get(name, 'doi_chung')
    return 'ims', name, lab, seed, evaluate(m, Fu.feats(late, 4000, I.FR, I.ORDERS), Fu.feats(hold, 4000, I.FR, I.ORDERS), lab)


def pb_load(code):
    a = np.load(ROOT.parent/'data'/'paderborn'/'cache'/f'{code}.npz')
    rows = [windows(simulate(v.astype(float)/9.81, 64000, S, np.random.default_rng([i, sum(map(ord, code))])), 4000) for i, v in enumerate(a['vib'])]
    return np.concatenate(rows)[:, None, :]


def pb_job(a):
    code, seed = a
    base = np.concatenate([pb_load(c) for c in ('K001', 'K002', 'K003')])
    lab = 'outer' if code.startswith('KA') else 'inner'
    t = pb_load(code)
    hold = np.concatenate([pb_load(c) for c in ('K004', 'K005', 'K006')])
    o = PADERBORN_6203.orders()
    m = Fu.fit_funnel(base, 25., o, S, 4000, seed, KINDS)
    return 'paderborn', code, lab, seed, evaluate(m, Fu.feats(t, 4000, 25., o), Fu.feats(hold, 4000, 25., o), lab)


def table(rows):
    plans = list(rows[0][4])
    out = {}
    for ds in sorted({r[0] for r in rows}):
        part = [r for r in rows if r[0] == ds]
        for plan in plans:
            per = {}
            for lab in ('inner', 'outer', 'cage'):
                names = sorted({r[1] for r in part if r[2] == lab})
                acc, cov, wrong, wrong_type = [], [], [], []
                for n in names:
                    vals = [r[4][plan] for r in part if r[1] == n]
                    c = np.mean([v['late_counts'] for v in vals], axis=0)
                    t = c.sum()
                    answered = c[1:].sum()
                    cov.append(answered/t)
                    if lab == 'cage':
                        continue
                    k = KINDS.index(lab)+1
                    wrong.append(c[k]/max(answered, 1e-9) if answered else np.nan)
                    acc.append(c[k]/t)
                if names:
                    per[lab] = {'tra_loi': float(np.mean(cov)), 'dung_khi_tra_loi': float(np.nanmean(wrong)) if wrong else None, 'dung_tren_tat_ca': float(np.mean(acc)) if acc else None, 'n': len(names)}
            hold = float(np.mean([r[4][plan]['hold_fault'] for r in part]))
            out[f'{ds}/{plan}'] = {**per, 'binh_thuong_bi_goi_loi': hold}
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(14) as pool:
        rows = list(pool.map(xjtu_job, [(n, s) for n in X.LABEL for s in SEEDS]))
        rows += list(pool.map(ims_job, [(n, s) for n in list(I.LABEL)+I.CONTROL for s in SEEDS]))
        pb = ['KA04', 'KA15', 'KA16', 'KA30', 'KA22', 'KI04', 'KI14', 'KI16', 'KI17', 'KI18', 'KI21']
        rows += list(pool.map(pb_job, [(c, s) for c in pb for s in SEEDS]))
    t = table(rows)
    (OUT/'e2.json').write_text(json.dumps({'table': t, 'rows': rows}, indent=1, default=float))
    keys = ['M0_luon_tra_loi', 'M3_chi_so_loi_khi_chac', 'M1_ovr_nguong_tu_dong', 'M2_ovr_tu_dong_co_vat_ly']+[f'M1_ovr_t{g}' for g in GRID]+[f'M2_ovr_t{g}_vat_ly' for g in GRID]
    for ds in ('xjtu', 'paderborn', 'ims'):
        print('==', ds)
        for k in keys:
            v = t[f'{ds}/{k}']
            f = lambda c: '-' if c not in v else f"{v[c]['tra_loi']:.2f}/{(v[c]['dung_khi_tra_loi'] if v[c]['dung_khi_tra_loi'] is not None else float('nan')):.2f}"
            print(f"{k:28s} trong {f('inner')}  ngoai {f('outer')}  cach {f('cage')}  binh_thuong_goi_loi {v['binh_thuong_bi_goi_loi']:.2f}", flush=True)


if __name__ == '__main__':
    main()
