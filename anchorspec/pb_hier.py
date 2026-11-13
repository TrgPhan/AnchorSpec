"""PB-HIER (PROTOCOL_PB_HIER.md): the locked two-stage architecture on Paderborn real damages, 8 seeds.
    python pb_hier.py --workers 14
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from u_natural import training
import funnel as Fu
import pb_common as P
from m_hier import scores_for, ARMS

OUT = P.ROOT / 'results' / 'pb_hier'
SEEDS = (11, 29, 47, 101, 202, 303, 404, 505)
BUDGETS = (1, 2, 4)


def job(task):
    target, seed, m = task
    t = P.item(target); H = P.item(P.healthy_for(target, seed))
    donors = P.pick(P.INNER_REAL, target, seed, 1, m) + P.pick(P.OUTER_REAL, target, seed, 2, m)
    base = training(H['base'], [(n, P.item(n)['label'], P.item(n)['donor']) for n in donors], {}, 'real')
    rng = np.random.default_rng([seed, sum(map(ord, H['code'])), 31])
    inj = {c: Fu.feats(Fu.injected(H['donor_w'][:, None, :], k, 150, P.FR, P.ORDERS, P.SENSORS['1k'], 4000, rng), 4000, P.FR, P.ORDERS)
           for c, k in ((1, 'inner'), (2, 'outer'))}
    return dict(target=target, seed=seed, budget=m, label=t['label'], donors=donors, scores=scores_for(base, inj, seed, t['test']))


def per_bearing(rows, arm):
    d = {}
    for r in rows:
        d.setdefault(r['target'], []).append(float(np.mean(np.asarray(r['scores'][arm]) == r['label'])))
    return {k: float(np.mean(v)) for k, v in d.items()}


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]
    lab = {r['target']: r['label'] for r in rows}; rng = np.random.default_rng(20261112)
    L = ['# PB-HIER: kiến trúc hai tầng đã khóa trên Paderborn hỏng thật (giao thức PROTOCOL_PB_HIER.md)', '',
         f'{len(rows)} lượt. Chỉ chọn loại lỗi, macro vòng trong/ngoài, mỗi ổ trung bình trên các seed.', '',
         '| Seed | Sự cố/loại | ' + ' | '.join(ARMS) + ' | hier − real | hier − phẳng | hier − hier_real |', '|---|---:|' + '---:|' * len(ARMS) + '---|---|---|']
    fmt = lambda c: f"{c['delta']*100:+.1f} [{c['ci95'][0]*100:+.1f}; {c['ci95'][1]*100:+.1f}]"
    c1, c2, res = [], True, {}
    for gname, gseeds in (('cả 8', SEEDS), ('11/29/47', SEEDS[:3]), ('5 mới', SEEDS[3:])):
        for m in BUDGETS:
            sub = [r for r in rows if r['budget'] == m and r['seed'] in gseeds]
            per = {a: per_bearing(sub, a) for a in ARMS}
            cs = [P.bootstrap(per['hier'], per[b], lab, rng) for b in ('real', 'et500+inj_mix_0.25', 'hier_real')]
            L.append(f'| {gname} | {m} | ' + ' | '.join(f'{P.macro(per[a], lab)*100:.1f}' for a in ARMS) + ' | ' + ' | '.join(fmt(c) for c in cs) + ' |')
            if gname == 'cả 8':
                res[m] = {a: P.macro(per[a], lab) for a in ARMS} | {'hier_vs_real': cs[0], 'hier_vs_flat': cs[1]}
                if cs[0]['delta'] >= .03 and cs[0]['ci95'][0] > 0: c1.append(m)
                c2 &= cs[0]['delta'] >= -.01
    passed = bool(c1) and c2
    L += ['', f"Tiêu chí 1: {'ĐẠT ở m = ' + str(c1) if c1 else 'KHÔNG ĐẠT'}. Tiêu chí 2: {'ĐẠT' if c2 else 'KHÔNG ĐẠT'}. **Kết luận: {'ĐẠT' if passed else 'KHÔNG ĐẠT'}.**"]
    (OUT / 'summary.json').write_text(json.dumps(dict(criterion1=c1, criterion2=c2, passed=passed, levels=res), indent=2))
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=14); ap.add_argument('--report', action='store_true'); a = ap.parse_args()
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    h = {n: hashlib.sha256((P.ROOT / n).read_bytes()).hexdigest() for n in ('PROTOCOL_PB_HIER.md', 'pb_hier.py', 'm_hier.py', 'm_dev.py', 'pb_common.py')}
    pre = OUT / 'prerun.sha256'
    if pre.exists() and json.loads(pre.read_text()) != h: raise ValueError('Frozen sources changed')
    pre.write_text(json.dumps(h, indent=2))
    if not a.report:
        todo = [(t, s, m) for m in BUDGETS for t in P.REAL for s in SEEDS if not (OUT / 'tasks' / f'{t}_{s}_m{m}.json').exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, (t, row) in enumerate(zip(todo, pool.map(job, todo)), 1):
                (OUT / 'tasks' / f'{t[0]}_{t[1]}_m{t[2]}.json').write_text(json.dumps(row))
                if i % 44 == 0: print('pbhier', i, '/', len(todo), flush=True)
    report()


if __name__ == '__main__':
    main()
