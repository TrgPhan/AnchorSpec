"""E7 (khám phá): 4 mức trạng thái + đường thay đổi đột ngột, thay cho RUL theo giờ.

Mức: 0 Bình thường, 1 Theo dõi, 2 Cảnh báo, 3 Nguy hiểm. Lên mức cần 5 lần liên tiếp, riêng
đột biến lên thẳng mức 2. Xuống mức cần 30 lần liên tiếp (trễ). So với không có trễ.
Ngưỡng Nguy hiểm lấy từ ổ dev (một nửa z trung vị 5% cuối đời) cho từng bộ dữ liệu.
"""
import json
from pathlib import Path

import numpy as np

from e1_baseline import hi_of, load, zs
from tn3_trend import DEV

OUT = Path(__file__).resolve().parent/'results'/'e7'
B = 60
WATCH, ALARM = 5., 10.


def levels(z, danger, hysteresis=True, cliff=15., up=5, down=30):
    lv = np.zeros(len(z), int)
    cur = 0
    for i in range(1, len(z)):
        tgt = 3 if z[i] >= danger else 2 if z[i] >= ALARM else 1 if z[i] >= WATCH else 0
        w = z[max(0, i-up+1):i+1]
        hold_up = 0
        for k, thr in ((3, danger), (2, ALARM), (1, WATCH)):
            if len(w) == up and (w >= thr).all():
                hold_up = k
                break
        if z[i]-z[i-1] >= cliff:
            hold_up = max(hold_up, 2)
        if hold_up > cur:
            cur = hold_up
        elif tgt < cur:
            w2 = z[max(0, i-(down if hysteresis else up)+1):i+1]
            limit = (0, WATCH, ALARM, danger)[cur]
            if len(w2) == (down if hysteresis else up) and (w2 < limit).all():
                cur = max(tgt, 0)
        lv[i] = cur
    return lv


def summarize(rows, name):
    n = len(rows)
    first = lambda k: [r['first'][k] for r in rows]
    fr2 = [x for x in first(2) if x is not None]
    fr3 = [x for x in first(3) if x is not None]
    return {'n': n, 'dat_canh_bao': len(fr2), 'canh_bao_trung_vi_%doi': float(np.median(fr2)) if fr2 else None, 'canh_bao_truoc_50%': sum(x < .5 for x in fr2),
            'dat_nguy_hiem': len(fr3), 'nguy_hiem_trung_vi_%doi': float(np.median(fr3)) if fr3 else None, 'nguy_hiem_truoc_50%': sum(x < .5 for x in fr3), 'ha_muc_trung_binh': float(np.mean([r['down'] for r in rows])),
            'doi_muc_trung_binh': float(np.mean([r['changes'] for r in rows])), 'muc_cuoi_ge2': sum(r['last'] >= 2 for r in rows)}


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    for ds in ('femto', 'xjtu', 'ims'):
        data = {n: v for n, v in load(ds).items() if len(v[0]) >= B+10}
        series = {n: (zs(hi_of(x, B), B, 5), t) for n, (x, t) in data.items()}
        dev = [n for n in series if n in DEV[ds]]
        danger = max(15., .5*float(np.median([np.median(series[n][0][-max(5, len(series[n][0])//20):]) for n in dev])))
        for hyst in (True, False):
            rows = []
            for n, (z, t) in series.items():
                if n in dev:
                    continue
                lv = levels(z, danger, hyst)
                d = np.diff(lv)
                f = {k: (float(t[np.argmax(lv >= k)]/t[-1]) if (lv >= k).any() else None) for k in (1, 2, 3)}
                rows.append({'name': n, 'first': f, 'down': int((d < 0).sum()), 'changes': int((d != 0).sum()), 'last': int(lv[-1])})
            res[f'{ds}/{"tre" if hyst else "khong_tre"}'] = {'danger_z': danger, **summarize(rows, ds), 'rows': rows}
            print(ds, 'tre' if hyst else 'khong_tre', {k: (round(v, 2) if isinstance(v, float) else v) for k, v in res[f'{ds}/{"tre" if hyst else "khong_tre"}'].items() if k != 'rows'}, flush=True)
    (OUT/'e7.json').write_text(json.dumps(res, indent=1))
