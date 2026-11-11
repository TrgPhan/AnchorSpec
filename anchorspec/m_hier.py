"""HIER (PROTOCOL_HIER.md): two-stage model keeps injection for inner/outer only. Step 1: development sets.
    python m_hier.py dev --workers 14
    python m_hier.py hust --workers 14
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import json
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from u_natural import LABEL as XLABEL, training
from event_experts import causal_average
from diagnostic_experts import fault_labels
from bearing import Bearing
from cheap_sensor import CheapSensor, simulate, windows
import funnel as Fu
import s3_dose as D
from m_dev import Model, mix, injected_pool
from x_core import GEO
import pb_common as P

ROOT = Path(__file__).resolve().parent
SEEDS = (11, 29, 47)
ARMS = ('real', 'et500', 'et500+inj_mix_0.25', 'hier', 'hier_real')
SENSOR = CheapSensor()


def two_stage(base, inj, seed, x, use_inj=True):
    xb, yb, wb = base
    ring = np.isin(yb, (1, 2))
    y1 = np.where(ring, 1, yb); w1 = np.where(ring, wb * .5, wb)
    m1 = Model('et500', seed).fit(xb, y1, w1)
    if use_inj:
        x2, y2, w2 = mix(base, inj, .25)
    else:
        x2, y2, w2 = base
    keep = np.isin(y2, (1, 2))
    m2 = Model('et500', seed).fit(x2[keep], y2[keep], w2[keep])
    p1, p2 = m1.predict_proba(x), m2.predict_proba(x)
    p = p1.copy()
    p[:, 1], p[:, 2] = p1[:, 1] * p2[:, 1], p1[:, 1] * p2[:, 2]
    return p


def scores_for(base, inj, seed, x):
    out = {}
    out['real'] = Model('rf500', seed).fit(*base).predict_proba(x)
    out['et500'] = Model('et500', seed).fit(*base).predict_proba(x)
    out['et500+inj_mix_0.25'] = Model('et500', seed).fit(*mix(base, inj, .25)).predict_proba(x)
    out['hier'] = two_stage(base, inj, seed, x, True)
    out['hier_real'] = two_stage(base, inj, seed, x, False)
    return {a: fault_labels(causal_average(p)).tolist() for a, p in out.items()}


def dev_job(task):
    ds, target, seed, profile = task
    start = time.perf_counter()
    t = D.item(ds, target)
    donors = D.donors_for(ds, target, seed, profile)
    base = training(t['base'], [(n, D.item(ds, n)['label'], D.item(ds, n)['donor']) for n in donors], {}, 'real')
    inj = injected_pool(ds, target, seed)
    return dict(ds=ds, target=str(target), seed=seed, profile=profile, label=t['label'], scores=scores_for(base, inj, seed, t['severe']),
                elapsed_seconds=time.perf_counter() - start)


# ---------------- HUST ----------------
HUST = ROOT.parent / 'data'
CODE = {'I': 1, 'O': 2, 'B': 3}


def hust_file(name):
    folder = 'hust_v6204' if name[1] == '4' else 'hust_v'
    d = loadmat(HUST / folder / f'{name}.mat', squeeze_me=True)
    return np.asarray(d['data'], float).ravel(), float(np.mean(d['fs']))


@lru_cache(maxsize=None)
def hust_item(cls, size):
    d, Dd, ball, nb = GEO[size]
    orders = Bearing(nb, ball, (d + Dd) / 2, 0.).orders()
    wins, feats = [], []
    for load in (0, 2, 4):
        x, fr = hust_file(f'{cls}{size}0{load}')
        y = simulate(x - x.mean(), 51200, SENSOR, np.random.default_rng([ord(cls), size, load, 7]))
        w = windows(y, 4000)
        wins.append((w, fr)); feats.append(Fu.feats(w[:, None, :], 4000, fr, orders))
    f = np.concatenate(feats)
    spread = np.linspace(0, len(f) - 1, 10).round().astype(int)
    w0, fr0 = wins[0]
    return dict(label=0 if cls == 'N' else CODE[cls], test=f, donor=f[spread], base=feats[0][:10],
                base_w=w0[:10][:, None, :], fr0=fr0, orders=orders)


def hust_targets():
    return [(c, s) for c in 'IOB' for s in (4, 5, 6, 7, 8) if not (c == 'B' and s == 4)]


def hust_job(task):
    cls, size, seed, m = task
    start = time.perf_counter()
    t = hust_item(cls, size); H = hust_item('N', size)
    donors = []
    for c in 'IOB':
        pool = sorted(s for s in (4, 5, 6, 7, 8) if not (c == 'B' and s == 4) and (c, s) != (cls, size))
        donors += [(c, int(s)) for s in np.random.default_rng([seed, CODE[c], 20261112]).permutation(pool)[:m]]
    base = training(H['base'], [(f'{c}{s}', CODE[c], hust_item(c, s)['donor']) for c, s in donors], {}, 'real')
    rng = np.random.default_rng([seed, size, 31])
    inj = {c: Fu.feats(Fu.injected(H['base_w'], k, 150, H['fr0'], H['orders'], SENSOR, 4000, rng), 4000, H['fr0'], H['orders'])
           for c, k in ((1, 'inner'), (2, 'outer'))}
    return dict(target=f'{cls}{size}', seed=seed, budget=m, label=t['label'], donors=[f'{c}{s}' for c, s in donors],
                scores=scores_for(base, inj, seed, t['test']), elapsed_seconds=time.perf_counter() - start)


# ---------------- reporting ----------------

def per_bearing(rows, arm):
    d = {}
    for r in rows:
        d.setdefault(r['target'], []).append(float(np.mean(np.asarray(r['scores'][arm]) == r['label'])))
    return {k: float(np.mean(v)) for k, v in d.items()}


def summarize(rows, classes, groups_of, other):
    rng = np.random.default_rng(20261112)
    out, L = {}, []
    for key, sub in groups_of(rows):
        lab = {r['target']: r['label'] for r in sub}
        per = {a: per_bearing(sub, a) for a in ARMS}
        res = {}
        for a in ARMS:
            cls = {c: float(np.mean([v for k, v in per[a].items() if lab[k] == c])) for c in classes}
            res[a] = dict(macro=P.macro(per[a], lab, classes), inner_outer=P.macro(per[a], lab, (1, 2)), other=cls[other], classes=cls)
            if a != 'real':
                res[a]['vs_real'] = P.bootstrap(per[a], per['real'], lab, rng, classes=classes)
        out[key] = res
    return out


def dev_report():
    rows = [json.loads(p.read_text()) for p in sorted((ROOT / 'results/hier_dev/tasks').glob('*.json'))]
    settings = [('uored', p) for p in D.PROFILES] + [('xjtu', 'natural')]
    res = summarize(rows, (1, 2, 4), lambda rs: [(f'{ds}:{p}', [r for r in rs if r['ds'] == ds and r['profile'] == p]) for ds, p in settings], 4)
    g = [res[k]['hier']['vs_real']['delta'] for k in res]
    cage = np.mean([res[k]['hier']['other'] - res[k]['real']['other'] for k in res])
    eligible = bool(np.mean(g) >= .02 and min(g) >= -.02 and cage >= -.05)
    L = ['# HIER bước 1 (phát triển): macro 3 lớp, chỉ chọn loại lỗi', '', '| Bộ | ' + ' | '.join(ARMS) + ' | vòng cách: real / hier | hier − real (CI 95%) |', '|---|' + '---:|' * len(ARMS) + '---|---|']
    for k, v in res.items():
        c = v['hier']['vs_real']
        L.append(f'| {k} | ' + ' | '.join(f"{v[a]['macro']*100:.1f}" for a in ARMS) + f" | {v['real']['other']*100:.1f} / {v['hier']['other']*100:.1f} | {c['delta']*100:+.1f} [{c['ci95'][0]*100:+.1f}; {c['ci95'][1]*100:+.1f}] |")
    L += ['', f'hier − real: TB {np.mean(g)*100:+.2f}, thấp nhất {min(g)*100:+.1f}; vòng cách TB {cage*100:+.1f} điểm', f'**Đủ điều kiện khóa: {"CÓ" if eligible else "KHÔNG"}**', '',
          '| Bộ (vòng trong+ngoài) | ' + ' | '.join(ARMS) + ' |', '|---|' + '---:|' * len(ARMS)]
    for k, v in res.items():
        L.append(f'| {k} | ' + ' | '.join(f"{v[a]['inner_outer']*100:.1f}" for a in ARMS) + ' |')
    (ROOT / 'results/hier_dev/summary.json').write_text(json.dumps(dict(results=res, eligible=eligible), indent=2))
    (ROOT / 'results/hier_dev/summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def hust_report():
    rows = [json.loads(p.read_text()) for p in sorted((ROOT / 'results/hier_hust/tasks').glob('*.json'))]
    res = summarize(rows, (1, 2, 3), lambda rs: [(m, [r for r in rs if r['budget'] == m]) for m in (1, 2, 3)], 3)
    eligible = json.loads((ROOT / 'results/hier_dev/summary.json').read_text())['eligible']
    c1 = [m for m in res if res[m]['hier']['vs_real']['delta'] >= .03 and res[m]['hier']['vs_real']['ci95'][0] > 0]
    c2 = bool(all(res[m]['hier']['vs_real']['delta'] >= -.01 for m in res))
    c3 = bool(np.mean([res[m]['hier']['other'] - res[m]['real']['other'] for m in res]) >= -.05)
    L = [f"# HIER bước 2: HUST (3 lớp trong / ngoài / bi), {'xác nhận' if eligible else 'THĂM DÒ'}", '',
         '| Sự cố/loại | ' + ' | '.join(ARMS) + ' | bi: real / hier | trong+ngoài: real / hier | hier − real (CI 95%) |', '|---:|' + '---:|' * len(ARMS) + '---|---|---|']
    for m, v in res.items():
        c = v['hier']['vs_real']
        L.append(f'| {m} | ' + ' | '.join(f"{v[a]['macro']*100:.1f}" for a in ARMS) + f" | {v['real']['other']*100:.1f} / {v['hier']['other']*100:.1f} | "
                 f"{v['real']['inner_outer']*100:.1f} / {v['hier']['inner_outer']*100:.1f} | {c['delta']*100:+.1f} [{c['ci95'][0]*100:+.1f}; {c['ci95'][1]*100:+.1f}] |")
    L += ['', '| Sự cố/loại | Nhánh | So với real (CI 95%) |', '|---:|---|---|']
    for m, v in res.items():
        for a in ARMS[1:]:
            c = v[a]['vs_real']; L.append(f"| {m} | {a} | {c['delta']*100:+.1f} [{c['ci95'][0]*100:+.1f}; {c['ci95'][1]*100:+.1f}] |")
    ok = bool(c1) and c2 and c3
    L += ['', f'Tiêu chí 1: {"ĐẠT ở m = " + str(c1) if c1 else "KHÔNG ĐẠT"}; tiêu chí 2: {"ĐẠT" if c2 else "KHÔNG ĐẠT"}; tiêu chí 3 (bi): {"ĐẠT" if c3 else "KHÔNG ĐẠT"}',
          f'**Kết luận: {"ĐẠT" if ok else "KHÔNG ĐẠT"}{"" if eligible else " (thăm dò, vì bước 1 không đủ điều kiện)"}**']
    (ROOT / 'results/hier_hust/summary.json').write_text(json.dumps(dict(results=res, passed=ok, confirmatory=eligible), indent=2))
    (ROOT / 'results/hier_hust/summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def run(job, todo, out, workers):
    (out / 'tasks').mkdir(parents=True, exist_ok=True)
    todo = [t for t in todo if not (out / 'tasks' / ('_'.join(map(str, t)) + '.json')).exists()]
    with ProcessPoolExecutor(workers) as pool:
        for i, (t, row) in enumerate(zip(todo, pool.map(job, todo)), 1):
            (out / 'tasks' / ('_'.join(map(str, t)) + '.json')).write_text(json.dumps(row))
            print('hier', i, '/', len(todo), t, round(row['elapsed_seconds'], 1), 's', flush=True)


def main():
    stage = sys.argv[1]
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 14
    if stage == 'smoke':
        print(dev_job(('uored', 16, 11, '2-2-2'))['scores'].keys()); r = hust_job(('B', 6, 11, 2)); print(r['donors'], len(r['scores']['hier'])); return
    if stage == 'dev':
        todo = [('uored', n, s, p) for p in D.PROFILES for n in D.UNAMES for s in SEEDS] + [('xjtu', n, s, 'natural') for n in XLABEL for s in SEEDS]
        run(dev_job, todo, ROOT / 'results/hier_dev', workers); dev_report()
    elif stage == 'hust':
        todo = [(c, s, seed, m) for m in (1, 2, 3) for c, s in hust_targets() for seed in SEEDS]
        run(hust_job, todo, ROOT / 'results/hier_hust', workers); hust_report()


if __name__ == '__main__':
    main()
