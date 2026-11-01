"""E6 (khám phá; XJTU đã mở): cổng học lại v2 và vòng học cảnh báo đáng quan tâm.

Cổng v2 không tự nhận lô khi: (a) mô hình hiện tại chắc chắn vào lớp lỗi khác, (b) bằng chứng vật lý
mạnh trái nhãn. Lô bị gắn cờ cần kỹ sư thứ hai xác nhận; đây không phải từ chối vĩnh viễn.
Vòng A: học từ phản hồi kỹ sư giả lập (cảnh báo trong 20% cuối đời coi là đáng quan tâm), LOBO trong từng bộ.
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
from e1_baseline import hi_of, load  # noqa: E402
from retrain import MachineModel  # noqa: E402
from tn6_retrain_cage import K_LIST, build  # noqa: E402

OUT = ROOT/'results'/'e6'
FAULT_KEYS = {1: 'bpfi', 2: 'bpfo', 3: 'ftf'}
AGREE, PHYS = .6, 1.5


def physics_conflict(z, label):
    """Vật lý mạnh chỉ về lớp khác hẳn nhãn: trung vị z ở lớp khác lớn hơn lớp nhãn đủ nhiều."""
    half = z.shape[1]//2
    score = {}
    for k, key in FAULT_KEYS.items():
        lo, hi = Fu.ENV[key]
        score[k] = np.median(np.maximum(z[:, lo:hi].mean(1), z[:, lo+half:hi+half].mean(1)))
    best = max(score, key=score.get)
    return best != label and score[best]-score[label] >= PHYS


def flagged(m, x, label):
    p = m.predict_proba(x)
    z = m._z(x)
    faults = p[:, 1:].argmax(1)+1
    conflict_model = np.mean((p[:, label] < .3) & (p[:, 1:].max(1) >= AGREE) & (faults != label)) >= .5
    return bool(conflict_model or physics_conflict(z, label))


def job(a):
    name, seed = a
    label = X.CLASSES.index(X.LABEL[name])
    d, inj, y, fx, fy = build(name, seed)
    late = d['f']['late']
    mid = len(late)//2
    out = {'name': name, 'seed': seed, 'label': X.LABEL[name]}
    mk = lambda: MachineModel(d['f']['base'], inj, y, fx, fy, seed=seed)
    test = late[mid:]
    for k in K_LIST:
        if mid < k:
            continue
        for kind, lab in (('dung', label), ('sai', (label % 3)+1)):
            m = mk()
            f = flagged(m, late[:k], lab)
            auto = (not f) and m.propose(late[:k], np.full(k, lab), 'ky_su')[0]
            out[f'{kind}{k}'] = {'co': f, 'tu_nhan': bool(auto), 'acc': float((m.predict_proba(test).argmax(1) == label).mean())}
    return out


def alarm_events(name, ds, b=30, persist=5, h=5.):
    x, t = load(ds)[name]
    if len(x) < b+10:
        return []
    hi = hi_of(x, b)
    y = np.log(np.maximum(hi, 1e-6))
    ref = y[:b]
    med, mad = np.median(ref), 1.4826*np.median(np.abs(ref-np.median(ref)))+1e-6
    z = (y-med)/mad
    ev, run = [], 0
    for i in range(b, len(z)):
        run = run+1 if z[i] > h else 0
        if run == persist:
            run = 0
            w = z[max(b, i-20):i+1]
            ev.append({'f': [z[i], w.mean(), w.max(), w.std(), float((z[b:i+1] > h).mean()), z[i]-z[max(b, i-5)]], 'y': int(t[i]/t[-1] >= .8), 'name': name})
    return ev


def relevance():
    res = {}
    for ds in ('femto', 'xjtu', 'ims'):
        names = list(load(ds))
        evs = {n: alarm_events(n, ds) for n in names}
        before_tp = before_fp = after_tp = after_fp = 0
        for n in names:
            test = evs[n]
            train = [e for m in names if m != n for e in evs[m]]
            if not test or len({e['y'] for e in train}) < 2:
                continue
            clf = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=0).fit([e['f'] for e in train], [e['y'] for e in train])
            p = clf.predict_proba([e['f'] for e in test])[:, 1] >= .5
            yy = np.array([e['y'] for e in test])
            before_tp += yy.sum()
            before_fp += (1-yy).sum()
            after_tp += (p & (yy == 1)).sum()
            after_fp += (p & (yy == 0)).sum()
        res[ds] = {'su_kien_dung': int(before_tp), 'su_kien_sai_truoc': int(before_fp), 'giu_dung': int(after_tp), 'sai_con_lai': int(after_fp),
                   'giam_bao_nham': float(1-after_fp/max(before_fp, 1)), 'bo_sot_su_kien_dung': float(1-after_tp/max(before_tp, 1))}
        print(ds, res[ds], flush=True)
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(14) as pool:
        rows = list(pool.map(job, [(n, s) for n in X.LABEL for s in X.SEEDS]))
    summary = {}
    for k in K_LIST:
        d = [r[f'dung{k}'] for r in rows if f'dung{k}' in r]
        b = [r[f'sai{k}'] for r in rows if f'sai{k}' in r]
        summary[k] = {'lo_dung_tu_nhan': sum(x['tu_nhan'] for x in d), 'lo_dung': len(d), 'lo_sai_tu_nhan': sum(x['tu_nhan'] for x in b), 'lo_sai': len(b),
                      'lo_dung_gan_co': sum(x['co'] for x in d), 'lo_sai_gan_co': sum(x['co'] for x in b)}
        print(k, summary[k], flush=True)
    for lab in X.FAULTS:
        part = [r for r in rows if r['label'] == lab]
        print(lab, {k: (sum(r[f'dung{k}']['tu_nhan'] for r in part if f'dung{k}' in r), sum(r[f'sai{k}']['tu_nhan'] for r in part if f'sai{k}' in r), sum(f'dung{k}' in r for r in part)) for k in K_LIST})
    rel = relevance()
    (OUT/'e6.json').write_text(json.dumps({'rows': rows, 'summary': summary, 'relevance': rel}, indent=1, default=float))


if __name__ == '__main__':
    main()
