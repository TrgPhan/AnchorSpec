"""E5 (khám phá): Bosch CNC, CISS 3 trục 2 kHz, 3 máy, 15 nguyên công, 2019-2021.

Không phải lỗi ổ bi: dùng để đo tầng phát hiện theo máy và nhãn trạng thái trong dữ liệu sản xuất thật.
Nền: 20 file 'good' sớm nhất của từng cặp máy-nguyên công (80% khớp, 20% lấy ngưỡng 99%). So với gộp mọi
nguyên công; nền của máy khác; thêm 10 file good đầu mỗi đợt vào nền (giả định đã được kỹ sư xác nhận sạch).
"""
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import re

import h5py
import numpy as np
from scipy import signal, stats
from sklearn.covariance import LedoitWolf
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent/'data'/'bosch_cnc'/'repo'/'data'
OUT = ROOT/'results'/'e5'
FS = 2000


def feat(path):
    with h5py.File(path, 'r') as f:
        x = np.asarray(f['vibration_data'], float)
    x = x-x.mean(0)
    out = []
    for a in x.T:
        rms = np.sqrt(np.mean(a**2))+1e-15
        fq, p = signal.welch(a, FS, nperseg=512)
        bands = [np.log(p[(fq >= lo) & (fq < lo+200)].sum()+1e-18) for lo in range(0, 1000, 200)]
        out += [np.log(rms), float(stats.kurtosis(a)), np.max(np.abs(a))/rms]+bands
    m = re.match(r'(M\d+)_(\w+_\d+)_(OP\d+)_(\d+)', Path(path).stem)
    return {'machine': m[1], 'frame': m[2], 'op': m[3], 'idx': int(m[4]), 'label': Path(path).parent.name, 'f': np.array(out), 'n': len(x)}


def order(fr):
    mon = {k: i for i, k in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split())}
    a, b = fr.split('_')
    return int(b)*12+mon[a[:3]]


def fit(x):
    cut = max(int(.8*len(x)), 5)
    inv = np.linalg.pinv(LedoitWolf().fit(x[:cut]).covariance_)
    mu = x[:cut].mean(0)
    d = lambda v: np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', v-mu, inv, v-mu), 0))
    thr = float(np.quantile(d(x[cut:]), .99)) if len(x)-cut >= 3 else float(np.quantile(d(x[:cut]), .995))
    return d, thr


def summary(rows):
    good = [r for r in rows if r[1] == 'good']
    bad = [r for r in rows if r[1] == 'bad']
    s = np.array([r[0] for r in good+bad])
    y = [0]*len(good)+[1]*len(bad)
    return {'n_good': len(good), 'n_bad': len(bad), 'bao_nham': float(np.mean([r[2] for r in good])) if good else None,
            'phat_hien': float(np.mean([r[2] for r in bad])) if bad else None, 'auc': float(roc_auc_score(y, s)) if good and bad else None}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(str(p) for p in REPO.rglob('*.h5'))
    with ProcessPoolExecutor(14) as pool:
        R = list(pool.map(feat, files, chunksize=8))
    frames = sorted({r['frame'] for r in R}, key=order)
    print('files', len(R), 'machines', sorted({r['machine'] for r in R}), 'frames', frames, 'bad', sum(r['label'] == 'bad' for r in R))
    by = defaultdict(list)
    for r in R:
        by[(r['machine'], r['op'])].append(r)
    results = {k: [] for k in ('moi_nguyen_cong', 'gop_nguyen_cong', 'may_khac_cung_nguyen_cong', 'lam_moi_nen_moi_dot')}
    per_frame = defaultdict(list)
    BASE = 20
    first_good = {}
    for key, rows in by.items():
        rows.sort(key=lambda r: (order(r['frame']), r['idx']))
        first_good[key] = [r for r in rows if r['label'] == 'good'][:BASE]
    skipped = 0
    for (mach, op), rows in by.items():
        base_rows = first_good[(mach, op)]
        if len(base_rows) < BASE:
            skipped += 1
            continue
        ids = {id(r) for r in base_rows}
        test = [r for r in rows if id(r) not in ids]
        if not test:
            continue
        tf = np.array([r['f'] for r in test])
        d, t = fit(np.array([r['f'] for r in base_rows]))
        for r, v in zip(test, d(tf)):
            rec = (float(v), r['label'], bool(v > t))
            results['moi_nguyen_cong'].append(rec)
            per_frame[(mach, r['frame'])].append(rec)
        pool_base = np.array([x['f'] for k, v in first_good.items() if k[0] == mach for x in v])
        d2, t2 = fit(pool_base)
        results['gop_nguyen_cong'] += [(float(v), r['label'], bool(v > t2)) for r, v in zip(test, d2(tf))]
        other = np.array([x['f'] for k, v in first_good.items() if k[0] != mach and k[1] == op for x in v])
        if len(other) >= BASE:
            d3, t3 = fit(other)
            results['may_khac_cung_nguyen_cong'] += [(float(v), r['label'], bool(v > t3)) for r, v in zip(test, d3(tf))]
        # Làm mới: thêm 10 file good đầu mỗi đợt vào nền, chỉ chấm phần còn lại của đợt đó.
        for fr in sorted({r['frame'] for r in test}, key=order):
            part = [r for r in test if r['frame'] == fr]
            gp = [r for r in part if r['label'] == 'good'][:10]
            if len(gp) < 10:
                continue
            d4, t4 = fit(np.concatenate([np.array([r['f'] for r in base_rows]), np.array([r['f'] for r in gp])]))
            nid = {id(r) for r in gp}
            rest = [r for r in part if id(r) not in nid]
            if rest:
                results['lam_moi_nen_moi_dot'] += [(float(v), r['label'], bool(v > t4)) for r, v in zip(rest, d4(np.array([r['f'] for r in rest])))]
    print('bo qua cap may-nguyen cong thieu nen', skipped)
    table = {k: summary(v) for k, v in results.items() if v}
    for k, v in table.items():
        print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()}, flush=True)
    drift = {}
    for key in sorted(per_frame, key=lambda k: (k[0], order(k[1]))):
        s = summary(per_frame[key])
        drift[f'{key[0]}/{key[1]}'] = s
        print(key, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in s.items()}, flush=True)
    (OUT/'e5.json').write_text(json.dumps({'table': table, 'drift': drift, 'files': len(R)}, indent=1))


if __name__ == '__main__':
    main()
