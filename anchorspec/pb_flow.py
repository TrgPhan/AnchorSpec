"""PB-Flow (PROTOCOL_PB_FLOW.md): locked S3 flow configuration confirmed on Paderborn real damages.
    python pb_flow.py --workers 12        # run + report
    python pb_flow.py --report
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier as _RFC
import invariant_classifier as IC
from u_natural import training
from event_experts import causal_average
from t_readiness import selective
from diagnostic_experts import fault_labels
import s3_dose as D
import pb_common as P

N_TREES = 500
IC.RandomForestClassifier = lambda **kw: _RFC(**{**kw, 'n_estimators': N_TREES})   # locked: 500 trees, all else unchanged
OUT = P.ROOT / 'results' / 'pb_flow'
SEEDS = (11, 29, 47)
BUDGETS = (1, 2, 4)
OFFSETS = (20261106, 1, 2)
ARMS = ('real', 'dup_add_0.25', 'flow_mix_0.25_30')


def evaluate(xyw, seed, t, H):
    m = IC.InvariantClassifier('rf', seed).fit(*xyw)
    p = causal_average(m.predict_proba(t['test']))
    ph = causal_average(m.predict_proba(H['hold']))
    return dict(cond=fault_labels(p).tolist(), sel=selective(p, 0).tolist(), hold=selective(ph, 0).tolist())


def job(task):
    target, seed, m = task
    start = time.perf_counter()
    t = P.item(target)
    H = P.item(P.healthy_for(target, seed))
    donors = P.pick(P.INNER_REAL, target, seed, 1, m) + P.pick(P.OUTER_REAL, target, seed, 2, m)
    counts = Counter(P.item(n)['label'] for n in donors)
    events = [(n, P.item(n)['label'], P.item(n)['donor']) for n in donors]
    base = training(H['base'], events, {}, 'real')
    fixed = D.fixed_arms(base, counts)
    scores = {a: evaluate(fixed[a], seed, t, H) for a in ('real', 'dup_add_0.25')}
    for o, pools in zip(OFFSETS, P.generate(donors, seed, OFFSETS)):
        xyw = D.flow_arms(base, counts, pools, None, ['flow_mix_0.25_30'])['flow_mix_0.25_30']
        scores[f'flow_mix_0.25_30@{o}'] = evaluate(xyw, seed, t, H)
    return dict(target=target, seed=seed, budget=m, label=t['label'], healthy=H['code'], donors=donors,
                scores=scores, elapsed_seconds=time.perf_counter() - start)


def keys(a):
    return [a] if not a.startswith('flow') else [f'{a}@{o}' for o in OFFSETS]


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]
    rng = np.random.default_rng(20261112)
    lab = {r['target']: r['label'] for r in rows}
    out, L = {}, ['# PB-Flow: Flow S3 trên Paderborn hỏng thật (RF 500 cây; giao thức PROTOCOL_PB_FLOW.md)', '']
    L += ['| Sự cố/loại | Nhánh | Chỉ chọn loại lỗi | Vòng trong / ngoài | Có lựa chọn khỏe | Lượt chẩn đoán đúng (trên 33) | Gán lỗi trên khỏe |', '|---:|---|---:|---|---:|---:|---:|']
    crit1, crit2, crit3 = [], True, True
    for m in BUDGETS:
        sub = [r for r in rows if r['budget'] == m]
        if len(sub) != 33:
            continue
        res = {}
        for a in ARMS:
            per = {pol: {} for pol in ('cond', 'sel')}
            ev, hf = 0, []
            for r in sub:
                for pol in ('cond', 'sel'):
                    v = np.mean([np.mean(np.asarray(r['scores'][k][pol]) == r['label']) for k in keys(a)])
                    per[pol].setdefault(r['target'], []).append(v)
                ev += np.mean([np.mean(np.asarray(r['scores'][k]['cond']) == r['label']) for k in keys(a)]) > .5
                hf += [np.mean(np.asarray(r['scores'][k]['hold']) > 0) for k in keys(a)]
            per = {pol: {n: float(np.mean(v)) for n, v in d.items()} for pol, d in per.items()}
            res[a] = dict(cond=P.macro(per['cond'], lab), sel=P.macro(per['sel'], lab), event_correct=int(ev),
                          inner=float(np.mean([v for n, v in per['cond'].items() if lab[n] == 1])),
                          outer=float(np.mean([v for n, v in per['cond'].items() if lab[n] == 2])),
                          healthy_fault=float(np.mean(hf)), per=per)
            s = res[a]
            L.append(f"| {m} | {a} | {s['cond']*100:.1f} | {s['inner']*100:.1f} / {s['outer']*100:.1f} | {s['sel']*100:.1f} | {s['event_correct']} | {s['healthy_fault']*100:.1f} |")
        comps = {f'{a} - {b}': {pol: P.bootstrap(res[a]['per'][pol], res[b]['per'][pol], lab, rng) for pol in ('cond', 'sel')}
                 for a, b in (('flow_mix_0.25_30', 'real'), ('flow_mix_0.25_30', 'dup_add_0.25'), ('dup_add_0.25', 'real'))}
        mr = comps['flow_mix_0.25_30 - real']['cond']; md = comps['flow_mix_0.25_30 - dup_add_0.25']['cond']
        if mr['delta'] >= .03 and mr['ci95'][0] > 0:
            crit1.append(m); crit3 &= md['delta'] > 0
        crit2 &= mr['delta'] >= -.01
        for r_ in res.values():
            r_.pop('per')
        out[m] = dict(results=res, comparisons=comps)
    L += ['', '| Sự cố/loại | So sánh | Chỉ chọn loại lỗi (CI 95%) | Có lựa chọn khỏe (CI 95%) |', '|---:|---|---|---|']
    for m, v in out.items():
        for k, c in v['comparisons'].items():
            f = lambda d: f"{d['delta']*100:+.1f} [{d['ci95'][0]*100:+.1f}; {d['ci95'][1]*100:+.1f}]"
            L.append(f"| {m} | {k} | {f(c['cond'])} | {f(c['sel'])} |")
    verdict = bool(crit1) and crit2 and crit3
    L += ['', f'Tiêu chí 1 (≥ +3, CI > 0 ở ít nhất một mức): {"ĐẠT ở m = " + str(crit1) if crit1 else "KHÔNG ĐẠT"}',
          f'Tiêu chí 2 (không mức nào < −1): {"ĐẠT" if crit2 else "KHÔNG ĐẠT"}',
          f'Tiêu chí 3 (hơn bản sao ở mức đạt tiêu chí 1): {"ĐẠT" if crit1 and crit3 else "KHÔNG ĐẠT"}',
          f'**Kết luận theo giao thức: Flow {"CÓ" if verdict else "KHÔNG CÓ"} giá trị kiểm chứng trên Paderborn.**']
    (OUT / 'summary.json').write_text(json.dumps(dict(protocol='PROTOCOL_PB_FLOW.md', budgets=out, criteria=dict(c1=crit1, c2=crit2, c3=crit3, verdict=verdict)), indent=2))
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8')
    print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=12); ap.add_argument('--report', action='store_true')
    ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    if a.smoke:
        r = job(('KI04', 11, 2)); print('arms', list(r['scores']), 'donors', r['donors'], 'healthy', r['healthy'], len(r['scores']['real']['cond']), round(r['elapsed_seconds'], 1), 's')
        return
    if not a.report:
        todo = [(t, s, m) for m in BUDGETS for t in P.REAL for s in SEEDS if not (OUT / 'tasks' / f'{t}_{s}_m{m}.json').exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, (t, row) in enumerate(zip(todo, pool.map(job, todo)), 1):
                (OUT / 'tasks' / f'{t[0]}_{t[1]}_m{t[2]}.json').write_text(json.dumps(row))
                print('pb', i, '/', len(todo), t, round(row['elapsed_seconds'], 1), 's', flush=True)
    report()


if __name__ == '__main__':
    main()
