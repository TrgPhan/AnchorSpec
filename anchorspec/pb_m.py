"""PB-M (PROTOCOL_M_DEV.md, section PB-M): confirm the arm(s) locked by M-Dev on Paderborn real damages.
Locked arms are read from results/m_dev/summary.json; nothing is chosen here.
    python pb_m.py --workers 12
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from u_natural import training
from event_experts import causal_average
from diagnostic_experts import fault_labels
import funnel as Fu
import s3_dose as D
import pb_common as P
from m_dev import Model, mix, inj_only

OUT = P.ROOT / 'results' / 'pb_m'
SEEDS = (11, 29, 47)
BUDGETS = (1, 2, 4)
LOCK = json.loads((P.ROOT / 'results' / 'm_dev' / 'summary.json').read_text())
ARMS = LOCK['locked'] or [LOCK['exploratory_if_none']]
CONFIRMATORY = bool(LOCK['locked'])


def build(arm, base, counts, H, donors, seed):
    kind, data = (arm.split('+') + [None])[:2] if '+' in arm else (None, arm)
    if kind is None:
        kind = arm if arm in ('et500', 'hgb', 'lr', 'svm1') else 'rf500'
        data = 'real' if arm in ('et500', 'hgb', 'lr', 'svm1') else arm
    if data == 'real':
        xyw = base
    elif data.startswith('inj'):
        rng = np.random.default_rng([seed, sum(map(ord, H['code'])), 31])
        inj = {c: Fu.feats(Fu.injected(H['donor_w'][:, None, :], k, 150, P.FR, P.ORDERS, P.SENSORS['1k'], 4000, rng), 4000, P.FR, P.ORDERS)
               for c, k in ((1, 'inner'), (2, 'outer'))}
        xyw = inj_only(H['base'], inj) if data == 'inj_only' else mix(base, inj, float(data.split('_')[-1]))
    elif data == 'flow_mix_0.25_30':
        pools = P.generate(donors, seed, (20261106,))[0]
        xyw = D.flow_arms(base, counts, pools, None, ['flow_mix_0.25_30'])['flow_mix_0.25_30']
    return kind, xyw


def job(task):
    target, seed, m = task
    start = time.perf_counter()
    t = P.item(target); H = P.item(P.healthy_for(target, seed))
    donors = P.pick(P.INNER_REAL, target, seed, 1, m) + P.pick(P.OUTER_REAL, target, seed, 2, m)
    counts = Counter(P.item(n)['label'] for n in donors)
    base = training(H['base'], [(n, P.item(n)['label'], P.item(n)['donor']) for n in donors], {}, 'real')
    scores = {}
    for arm in ('real',) + tuple(ARMS):
        kind, xyw = ('rf500', base) if arm == 'real' else build(arm, base, counts, H, donors, seed)
        mdl = Model(kind, seed).fit(*xyw)
        scores[arm] = fault_labels(causal_average(mdl.predict_proba(t['test']))).tolist()
    return dict(target=target, seed=seed, budget=m, label=t['label'], scores=scores, elapsed_seconds=time.perf_counter() - start)


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]
    rng = np.random.default_rng(20261112)
    lab = {r['target']: r['label'] for r in rows}
    L = [f"# PB-M: kiểm chứng trên Paderborn ({'xác nhận, nhánh đã khóa' if CONFIRMATORY else 'THĂM DÒ, không nhánh nào đủ điều kiện'})", '',
         f'Nhánh: {ARMS}. RF 500 cây làm mốc `real`. Chỉ chọn loại lỗi, macro 2 lớp.', '',
         '| Sự cố/loại | Nhánh | Macro | Vòng trong | Vòng ngoài | So với real (CI 95%) | Lượt đúng (trên 33) |', '|---:|---|---:|---:|---:|---|---:|']
    verdict = {}
    for arm in ARMS:
        c1, c2 = [], True
        for m in BUDGETS:
            sub = [r for r in rows if r['budget'] == m]
            per = {a: {} for a in ('real', arm)}
            for r in sub:
                for a in per:
                    per[a].setdefault(r['target'], []).append(float(np.mean(np.asarray(r['scores'][a]) == r['label'])))
            per = {a: {n: float(np.mean(v)) for n, v in d.items()} for a, d in per.items()}
            c = P.bootstrap(per[arm], per['real'], lab, rng)
            for a in ('real', arm):
                ev = sum(np.mean(np.asarray(r['scores'][a]) == r['label']) > .5 for r in sub)
                inn = np.mean([v for k, v in per[a].items() if lab[k] == 1]); out = np.mean([v for k, v in per[a].items() if lab[k] == 2])
                cs = '' if a == 'real' else f"{c['delta']*100:+.1f} [{c['ci95'][0]*100:+.1f}; {c['ci95'][1]*100:+.1f}]"
                L.append(f'| {m} | {a} | {P.macro(per[a], lab)*100:.1f} | {inn*100:.1f} | {out*100:.1f} | {cs} | {ev} |')
            if c['delta'] >= .03 and c['ci95'][0] > 0:
                c1.append(m)
            c2 &= c['delta'] >= -.01
        verdict[arm] = dict(criterion1=c1, criterion2=c2, passed=bool(c1) and c2)
        L.append(f"\n**{arm}:** tiêu chí 1 {'ĐẠT ở m = ' + str(c1) if c1 else 'KHÔNG ĐẠT'}; tiêu chí 2 {'ĐẠT' if c2 else 'KHÔNG ĐẠT'} -> "
                 f"{'ĐẠT' if verdict[arm]['passed'] else 'KHÔNG ĐẠT'}{'' if CONFIRMATORY else ' (thăm dò)'}\n")
    (OUT / 'summary.json').write_text(json.dumps(dict(arms=ARMS, confirmatory=CONFIRMATORY, verdict=verdict), indent=2))
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=12); ap.add_argument('--report', action='store_true'); a = ap.parse_args()
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    if not a.report:
        todo = [(t, s, m) for m in BUDGETS for t in P.REAL for s in SEEDS if not (OUT / 'tasks' / f'{t}_{s}_m{m}.json').exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, (t, row) in enumerate(zip(todo, pool.map(job, todo)), 1):
                (OUT / 'tasks' / f'{t[0]}_{t[1]}_m{t[2]}.json').write_text(json.dumps(row))
                print('pbm', i, '/', len(todo), t, round(row['elapsed_seconds'], 1), 's', flush=True)
    report()


if __name__ == '__main__':
    main()
