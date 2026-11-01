"""TN1b (khám phá): cảm biến rẻ S4, có khắc phục được việc không chuyển giữa các tải không?

Không ngưỡng báo động: chỉ độ đúng 4 lớp. Tải 1 HP và 3 HP đã xem từ TN1.
"""
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from tn1_cwru_cheap import CLASSES, DATA, ROOT, SEEDS, features_fs, fit_detector
from cheap_sensor import CheapSensor, simulate, windows

IDS = {'healthy': (97, 98, 99, 100), 'inner': (105, 106, 107, 108), 'outer': (130, 131, 132, 133), 'ball': (118, 119, 120, 121)}
RPM = (1797, 1772, 1750, 1730)
S = CheapSensor()
N = round(2048*S.fs_out/12000)


def load(seed):
    out = {}
    for c, ids in IDS.items():
        for hp, i in enumerate(ids):
            m = loadmat(DATA/f'{i}.mat')
            raw = np.asarray(m[f'X{i:03d}_DE_time'], float).ravel()
            rpm = float(np.asarray(m.get(f'X{i:03d}RPM', RPM[hp])).ravel()[0])
            y = simulate(raw, 48000 if c == 'healthy' else 12000, S, np.random.default_rng([seed, i]))
            out[(c, hp)] = features_fs(windows(y, N), S.fs_out, rpm)
    return out


def run(f, loads, take, norm, seed):
    """norm=True: z-score theo 20 cửa sổ bình thường ĐẦU TIÊN của cùng tải (nền từng điều kiện)."""
    def z(x, hp):
        if not norm:
            return x
        h = f[('healthy', hp)][:20]
        return (x-h.mean(0))/(h.std(0)+1e-9)
    real = {}
    for c in CLASSES:
        k = (20 if c == 'healthy' else 8) if take == 'neo' else None
        real[c] = np.concatenate([z(f[(c, hp)][:k], hp) for hp in loads])
    model, _ = fit_detector(real, {}, seed)
    res = {}
    for hp in (1, 3):
        rows = {}
        for k, c in enumerate(CLASSES):
            x = f[(c, hp)]
            if norm and c == 'healthy':
                x = x[20:]  # 20 cửa sổ dùng làm nền không được tính điểm
            rows[c] = float((model.predict(z(x, hp)) == k).mean())
        res[hp] = {'macro': float(np.mean(list(rows.values()))), **rows}
    return res


CASES = {'a_goc_0HP_neo': ((0,), 'neo', False), 'b_0HP_toan_bo': ((0,), 'all', False), 'c_0_2HP_neo': ((0, 2), 'neo', False),
         'd_0_2HP_toan_bo': ((0, 2), 'all', False), 'e_0HP_neo_nen_tung_tai': ((0,), 'neo', True), 'f_0_2HP_toan_bo_nen_tung_tai': ((0, 2), 'all', True)}
out = {}
for name, cfg in CASES.items():
    rows = []
    for seed in SEEDS:
        rows.append(run(load(seed), *cfg, seed))
    out[name] = {hp: {k: float(np.mean([r[hp][k] for r in rows])) for k in rows[0][hp]} for hp in (1, 3)}
    print(name, {hp: {k: round(v, 3) for k, v in out[name][hp].items()} for hp in (1, 3)}, flush=True)
(ROOT/'results'/'tn1'/'multiload.json').write_text(json.dumps(out, indent=1))
