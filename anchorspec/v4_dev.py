"""PLAN_V4 V1: development run on UORED (PROTOCOL_V4_DEV.md). Locks results/v4_dev/lock.json.
    python v4_dev.py --smoke | --workers 14 | --report
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import router_common as R
import v4_flow as V
from router_dev import per_bearing, cls_mean, boot

OUT = R.P.ROOT / 'results' / 'v4_dev'
TARGETS = [i for c in (1, 2, 3, 4) for i in R.UORED_IDS[c]]


def job(task):
    target, seed, m = task; start = time.perf_counter()
    lib = R.library('uored', target, seed, m, (1, 2, 3, 4)); test = R.uored(target)['test_f']
    base, _ = R.real_base('uored', target, seed, lib); inj = R.injected('uored', target, seed); cache = {}
    sc = {a: V.predict_arm(a, 'uored', target, seed, lib, base, inj, test, cache) for a in V.ARMS}
    return task, dict(target=target, seed=seed, budget=m, label=R.uored(target)['label'], lib={str(k): v for k, v in lib.items()},
                      scores=sc, elapsed_seconds=time.perf_counter() - start)


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]; labels = {r['target']: r['label'] for r in rows}
    rng = np.random.default_rng(20261112); fmt = lambda t: f'{t[0]*100:+.1f} [{t[1]*100:+.1f}; {t[2]*100:+.1f}]'
    L = ['# V4-DEV: phát triển trên UORED (PROTOCOL_V4_DEV.md)', '', f'{len(rows)} lượt, 8 seed, m = 1, 2. Chỉ chọn loại lỗi, cửa sổ lỗi nặng.', '',
         '| m | Nhánh | Trong | Ngoài | Bi | Cách | Macro | Không-luật | Không-luật − đối chứng (CI 95%) |', '|---:|---|---:|---:|---:|---:|---:|---:|---|']
    agg = {a: [] for a in V.ARMS}
    for m in (1, 2):
        sub = [r for r in rows if r['budget'] == m]; per = {a: per_bearing(sub, a) for a in V.ARMS}
        for a in V.ARMS:
            cl = [cls_mean(per[a], labels, (c,)) for c in (1, 2, 3, 4)]; agg[a].append(cl)
            ctl = V.CONTROL.get(a)
            c = fmt(boot({k: per[a][k] for k in per[a] if labels[k] in (3, 4)}, per[ctl], labels, (3, 4), rng)) + f' (vs {ctl})' if ctl else ''
            L.append(f'| {m} | {a} | ' + ' | '.join(f'{v*100:.1f}' for v in cl) + f' | {np.mean(cl)*100:.1f} | {np.mean(cl[2:])*100:.1f} | {c} |')
    mean = {a: np.mean(v, 0) for a, v in agg.items()}           # per-class, averaged over m
    nr = {a: float(np.mean(v[2:])) for a, v in mean.items()}; mac = {a: float(np.mean(v)) for a, v in mean.items()}
    h = mean['hier']
    guard = {a: bool(mean[a][0] >= h[0] - .02 and mean[a][1] >= h[1] - .02 and mac[a] >= mac['hier'] - .01) for a in V.ARMS}
    useful = [a for a in V.CONTROL if guard[a] and nr[a] > nr[V.CONTROL[a]] and nr[a] >= nr['hier'] + .02]
    if useful:
        best = max(useful, key=nr.get)
        fs = [a for a in V.FLOW_SRC if a in useful and nr[a] >= nr[best] - .01]
        locked, status = (max(fs, key=nr.get) if fs else best), 'useful'
    else:
        fs = [a for a in V.FLOW_SRC if guard[a]]
        locked, status = (max(fs, key=nr.get), 'neutral') if fs else ('hier', 'no_flow')
    lock = dict(arm=locked, status=status, copy_equivalent=V.CONTROL.get(locked))
    L += ['', '## Trung bình hai mức m', '', '| Nhánh | Trong | Ngoài | Bi | Cách | Macro | Không-luật | Bảo vệ đạt |', '|---|---:|---:|---:|---:|---:|---:|---|']
    L += [f'| {a} | ' + ' | '.join(f'{v*100:.1f}' for v in mean[a]) + f' | {mac[a]*100:.1f} | {nr[a]*100:.1f} | {"có" if guard[a] else "không"} |' for a in V.ARMS]
    L += ['', f'**Ứng viên có ích:** {useful or "không có"}. **Khóa:** `{locked}` ({status}).', '', '```json', json.dumps(lock, indent=1), '```']
    (OUT / 'lock.json').write_text(json.dumps(lock, indent=1)); (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=14); ap.add_argument('--report', action='store_true')
    ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        t, row = job((12, 11, 2)); print(round(row['elapsed_seconds'], 1), 's', {k: round(float(np.mean(np.asarray(v) == row['label'])), 2) for k, v in row['scores'].items()}); return
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    files = ('PROTOCOL_V4_DEV.md', 'v4_dev.py', 'v4_flow.py', 'router_common.py', 'branch_c.py', 'router_dev.py')
    hsh = {n: hashlib.sha256((R.P.ROOT / n).read_bytes()).hexdigest() for n in files}; pre = OUT / 'prerun.sha256'
    if pre.exists() and json.loads(pre.read_text()) != hsh:
        raise ValueError('Frozen sources changed')
    pre.write_text(json.dumps(hsh, indent=2))
    if not a.report:
        todo = [(t, s, m) for m in (1, 2) for t in TARGETS for s in R.SEEDS if not (OUT / 'tasks' / f'{t}_{s}_{m}.json').exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, fut in enumerate(as_completed([pool.submit(job, t) for t in todo]), 1):
                t, row = fut.result(); (OUT / 'tasks' / f'{t[0]}_{t[1]}_{t[2]}.json').write_text(json.dumps(row))
                if i % 40 == 0: print('v4dev', i, '/', len(todo), flush=True)
    report()


if __name__ == '__main__':
    main()
