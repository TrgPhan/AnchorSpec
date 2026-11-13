"""PLAN_V4 V2: single validation of results/v4_dev/lock.json (PROTOCOL_V5_VAL.md).
HUST (inner/outer/ball, m=1,2,3) + XJTU (inner/outer/cage, natural library; reference only). 8 seeds.
    python v4_val.py --workers 14 | --report
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import router_common as R
import v5_fg as V

OUT = R.P.ROOT / 'results' / 'v5_val'
LOCK = json.loads((R.P.ROOT / 'results' / 'v5_dev' / 'lock.json').read_text())
ARMS = tuple(dict.fromkeys(['hier', LOCK['arm']] + ([LOCK['copy_equivalent']] if LOCK.get('copy_equivalent') else [])))
CLASSES = {'hust': (1, 2, 3), 'xjtu': (1, 2, 4)}


def job(task):
    ds, target, seed, m = task; start = time.perf_counter()
    lib = R.library(ds, target, seed, m, CLASSES[ds]); test = R.record(ds, target)['test_f']
    base, _ = R.real_base(ds, target, seed, lib); inj = R.injected(ds, target, seed); cache = {}
    sc = {a: V.predict(a, ds, target, seed, lib, base, inj, test, cache) for a in ARMS}
    return task, dict(ds=ds, target=str(target) if ds == 'xjtu' else f'{target[0]}{target[1]}', seed=seed, budget=m,
                      label=R.record(ds, target)['label'], scores=sc, elapsed_seconds=time.perf_counter() - start)


def name(t):
    tg = t[1] if t[0] == 'xjtu' else f'{t[1][0]}{t[1][1]}'
    return f'{t[0]}_{tg}_{t[2]}_{t[3]}.json'


def per_bearing(rows, arm):
    d = {}
    for r in rows:
        d.setdefault(r['target'], []).append(float(np.mean(np.asarray(r['scores'][arm]) == r['label'])))
    return {k: float(np.mean(v)) for k, v in d.items()}


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]
    rng = np.random.default_rng(20261112); fmt = lambda c: f"{c['delta']*100:+.1f} [{c['ci95'][0]*100:+.1f}; {c['ci95'][1]*100:+.1f}]"
    L = ['# V5-VAL: kiểm chứng một lần (PROTOCOL_V5_VAL.md)', '', f"Khóa: `{json.dumps(LOCK)}`. {len(rows)} lượt, 8 seed, chỉ chọn loại lỗi.", '']
    c1, c2, c3, c3neg = True, False, False, True
    lk, ce = LOCK['arm'], LOCK.get('copy_equivalent')
    for ds, budgets, nl, title in (('hust', (1, 2, 3), 3, 'HUST (tiêu chí)'), ('xjtu', (0,), 4, 'XJTU (tham khảo, 2 ổ vòng cách)')):
        cls = CLASSES[ds]
        L += [f'## {title}', '', '| m | Nhánh | ' + ' | '.join(R.NAMES[c] for c in cls) + ' | Macro | Trong − hier | Ngoài − hier | ' + f'{R.NAMES[nl]} − hier | Macro − hier | {lk} − {ce} |',
              '|---:|---|' + '---:|' * (len(cls) + 1) + '---|---|---|---|---|']
        for m in budgets:
            sub = [r for r in rows if r['ds'] == ds and r['budget'] == m]
            if not sub:
                continue
            lab = {r['target']: r['label'] for r in sub}; per = {a: per_bearing(sub, a) for a in ARMS}
            only = lambda a, c: {k: v for k, v in per[a].items() if lab[k] == c}
            d_in = R.P.bootstrap(only(lk, 1), per['hier'], lab, rng, classes=(1,)); d_out = R.P.bootstrap(only(lk, 2), per['hier'], lab, rng, classes=(2,))
            d_nl = R.P.bootstrap(only(lk, nl), per['hier'], lab, rng, classes=(nl,)); d_mac = R.P.bootstrap(per[lk], per['hier'], lab, rng, classes=cls)
            d_fl = R.P.bootstrap(per[lk], per[ce], lab, rng, classes=cls) if ce else None
            if ds == 'hust':
                c1 &= d_in['delta'] >= -.02 and d_out['delta'] >= -.02 and d_nl['delta'] >= -.02
                c2 |= d_mac['delta'] >= .02 and d_mac['ci95'][0] > 0
                if d_fl:
                    c3 |= d_fl['delta'] >= .02 and d_fl['ci95'][0] > 0; c3neg &= d_fl['delta'] >= -.01
            for a in ARMS:
                cl = [np.mean([v for k, v in per[a].items() if lab[k] == c]) for c in cls]
                extra = f" | {fmt(d_in)} | {fmt(d_out)} | {fmt(d_nl)} | {fmt(d_mac)} | {fmt(d_fl) if d_fl else ''}" if a == lk else ' | | | | |'
                L.append(f'| {m} | {a} | ' + ' | '.join(f'{v*100:.1f}' for v in cl) + f' | {R.P.macro(per[a], lab, cls)*100:.1f}{extra} |')
        L.append('')
    v = dict(c1_no_harm_each_class=bool(c1), c2_macro_gain=bool(c2), c3_flow_own=bool(c3 and c3neg and ce is not None))
    L += ['## Tiêu chí (HUST)', '', *[f'- {k}: {"ĐẠT" if b else "KHÔNG ĐẠT"}' for k, b in v.items()]]
    (OUT / 'summary.json').write_text(json.dumps(v, indent=1)); (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=14); ap.add_argument('--report', action='store_true'); a = ap.parse_args()
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    files = ('PROTOCOL_V5_VAL.md', 'v4_val.py', 'v4_flow.py', 'router_common.py', 'branch_c.py')
    hsh = {n: hashlib.sha256((R.P.ROOT / n).read_bytes()).hexdigest() for n in files} | {'lock': json.dumps(LOCK, sort_keys=True)}
    pre = OUT / 'prerun.sha256'
    if pre.exists() and json.loads(pre.read_text()) != hsh:
        raise ValueError('Frozen sources changed')
    pre.write_text(json.dumps(hsh, indent=2))
    if not a.report:
        from u_natural import LABEL as XL
        todo = [('hust', t, s, m) for m in (1, 2, 3) for c in (1, 2, 3) for t in R.HUST_IDS[c] for s in R.SEEDS] + \
               [('xjtu', t, s, 0) for t in XL for s in R.SEEDS]
        todo = [t for t in todo if not (OUT / 'tasks' / name(t)).exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, fut in enumerate(as_completed([pool.submit(job, t) for t in todo]), 1):
                t, row = fut.result(); (OUT / 'tasks' / name(t)).write_text(json.dumps(row))
                if i % 50 == 0: print('v5val', i, '/', len(todo), flush=True)
    report()


if __name__ == '__main__':
    main()
