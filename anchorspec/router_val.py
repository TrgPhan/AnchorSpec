"""PLAN.md WP6: single validation of the router locked in results/router_dev/lock.json (PROTOCOL_ROUTER_VAL.md).
HUST (S1 m=1,2,3 and S2 no-ball) + Paderborn (S1 m=1,2,4), 8 seeds. Arms: hier, router, router_noflow (+ real).
    python router_val.py --workers 14 | --report
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from event_experts import causal_average
from diagnostic_experts import fault_labels
import router_common as R
import router as RT
import openset as OS
from m_dev import Model

OUT = R.P.ROOT / 'results' / 'router_val'
LOCK = json.loads((R.P.ROOT / 'results' / 'router_dev' / 'lock.json').read_text())
lab = lambda p: fault_labels(causal_average(p)).tolist()
HUST_T = [k for c in (1, 2, 3) for k in R.HUST_IDS[c]]
PB_T = list(R.P.REAL)


def dev_noflow_choice():
    """Same rule as the dev lock, restricted to generators without Flow (for the router_noflow arm)."""
    import router_dev as RD
    rows = [json.loads(p.read_text()) for p in (RD.OUT / 'tasks').glob('S1_*.json')]; labels = {r['target']: r['label'] for r in rows}
    nr, mac = {}, {}
    for a in ('hier', 'c_copy', 'c_surr', 'c_trans'):
        v = [RD.per_bearing([r for r in rows if r['budget'] == m], a) for m in (1, 2)]
        nr[a] = np.mean([RD.cls_mean(x, labels, (3, 4)) for x in v]); mac[a] = np.mean([RD.cls_mean(x, labels, (1, 2, 3, 4)) for x in v])
    c = [a for a in ('c_surr', 'c_trans') if nr[a] > nr['c_copy'] and mac[a] >= mac['hier'] - .01]
    return max(c, key=lambda a: nr[a]) if c else 'c_none'


def cfgs():
    full = dict(fneo=LOCK['fneo'], branch_c=LOCK['branch_c'], ball_rule=LOCK['ball_rule'])
    noflow = dict(full, fneo=False)
    if 'flow' in (LOCK['branch_c'] or ''):
        noflow['branch_c'] = NOFLOW_C
    return full, noflow


NOFLOW_C = dev_noflow_choice() if 'flow' in (LOCK['branch_c'] or '') else None


def job(task):
    scen, ds, target, seed, m = task; start = time.perf_counter()
    test = R.record(ds, target)['test_f']; full, noflow = cfgs()
    classes = RT.CLASSES[ds] if scen == 'S1' else (1, 2)
    lib = R.library(ds, target, seed, m, classes)
    base, events = R.real_base(ds, target, seed, lib); inj = R.injected(ds, target, seed)
    flow = R.fit_flow(ds, target, seed, lib) if (full['fneo'] or 'flow' in (full['branch_c'] or '')) else None
    sc = {'real': lab(Model('rf500', seed).fit(*base).predict_proba(test))}
    p, m1, b1 = R.two_stage(base, {}, inj[0], seed, test, return_t1=True); sc['hier'] = lab(p)
    sc['router'], log = RT.predict(ds, target, seed, lib, full, test, flow, inj, base)
    sc['router_noflow'], _ = RT.predict(ds, target, seed, lib, noflow, test, flow, inj, base)
    row = dict(scenario=scen, ds=ds, target=str(target), seed=seed, budget=m, label=R.record(ds, target)['label'], scores=sc, routes={str(k): v for k, v in log.items()})
    if scen == 'S2' and LOCK.get('kappa') is not None:
        h = R.target_healthy(ds, target, seed)
        ids = ['H'] * len(h['healthy_f']) + [n for n, c, f in events for _ in range(len(f))]
        dist, q95 = OS.gate_data(b1, ids, test)
        row['gate'] = dict(dist=dist.tolist(), q95=q95)
    row['elapsed_seconds'] = time.perf_counter() - start
    return task, row


def name(t):
    return f'{t[0]}_{t[1]}_{"".join(map(str, t[2])) if isinstance(t[2], tuple) else t[2]}_{t[3]}_{t[4]}.json'


def per_bearing(rows, arm, gate=None):
    d = {}
    for r in rows:
        pred = np.asarray(r['scores'][arm])
        if gate is not None and 'gate' in r:
            pred = OS.apply_gate(pred, r['gate']['dist'], r['gate']['q95'], gate)
        d.setdefault(r['target'], []).append(float(np.mean(pred == r['label'])))
    return {k: float(np.mean(v)) for k, v in d.items()}


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]
    rng = np.random.default_rng(20261112); fmt = lambda c: f"{c['delta']*100:+.1f} [{c['ci95'][0]*100:+.1f}; {c['ci95'][1]*100:+.1f}]"
    L = ['# ROUTER-VAL: kiểm chứng một lần (PROTOCOL_ROUTER_VAL.md)', '', f'Cấu hình khóa: `{json.dumps(LOCK)}`. {len(rows)} lượt, 8 seed, chỉ chọn loại lỗi.', '']
    ok1, ok2, ok4, ok4neg = True, False, False, True
    for ds, budgets, classes, name_ in (('hust', (1, 2, 3), (1, 2, 3), 'HUST'), ('pb', (1, 2, 4), (1, 2), 'Paderborn')):
        L += [f'## {name_}, S1', '', '| m | Nhánh | ' + ' | '.join(R.NAMES[c] for c in classes) + ' | Macro | Trong+ngoài − hier (CI) | Macro − hier (CI) | router − router_noflow (CI) |',
              '|---:|---|' + '---:|' * (len(classes) + 1) + '---|---|---|']
        for m in budgets:
            sub = [r for r in rows if r['scenario'] == 'S1' and r['ds'] == ds and r['budget'] == m]
            if not sub:
                continue
            labels = {r['target']: r['label'] for r in sub}; per = {a: per_bearing(sub, a) for a in ('real', 'hier', 'router', 'router_noflow')}
            io = R.P.bootstrap(per['router'], per['hier'], labels, rng, classes=(1, 2))
            mc = R.P.bootstrap(per['router'], per['hier'], labels, rng, classes=classes)
            fl = R.P.bootstrap(per['router'], per['router_noflow'], labels, rng, classes=classes)
            ok1 &= io['delta'] >= -.01 and io['ci95'][0] > -.03
            if ds == 'hust':
                bb = R.P.bootstrap({k: v for k, v in per['router'].items() if labels[k] == 3}, per['hier'], labels, rng, classes=(3,))
                ok2 |= (bb['delta'] >= .05 and bb['ci95'][0] > 0) or (mc['delta'] >= .02 and mc['ci95'][0] > 0)
            ok4 |= fl['delta'] >= .02 and fl['ci95'][0] > 0; ok4neg &= fl['delta'] >= -.01
            for a in ('real', 'hier', 'router', 'router_noflow'):
                cl = [np.mean([v for k, v in per[a].items() if labels[k] == c]) for c in classes]
                extra = f' | {fmt(io)} | {fmt(mc)} | {fmt(fl)}' if a == 'router' else ' | | |'
                L.append(f'| {m} | {a} | ' + ' | '.join(f'{v*100:.1f}' for v in cl) + f' | {R.P.macro(per[a], labels, classes)*100:.1f}{extra} |')
        L.append('')
    s2 = [r for r in rows if r['scenario'] == 'S2']
    if s2:
        labels = {r['target']: r['label'] for r in s2}
        L += ['## HUST, S2 (không có sự cố bi nào)', '', '| Nhánh | trong | ngoài | bi | Bi "chưa biết" | Lớp đã biết bị báo "chưa biết" |', '|---|---:|---:|---:|---:|---:|']
        for a in ('hier', 'router'):
            per = per_bearing(s2, a); cl = [np.mean([v for k, v in per.items() if labels[k] == c]) for c in (1, 2, 3)]
            L.append(f'| {a} | ' + ' | '.join(f'{v*100:.1f}' for v in cl) + ' | | |')
        if LOCK['ball_rule']:
            pr = per_bearing(s2, 'router'); ph = per_bearing(s2, 'hier')
            ball = R.P.bootstrap({k: v for k, v in pr.items() if labels[k] == 3}, {k: 0. for k in pr}, labels, rng, classes=(3,))
            ok3 = ball['delta'] >= .30 and ball['ci95'][0] > 0
            L.append(f"\nRecall bi (luật {LOCK['ball_rule']}): {fmt(ball)}.")
        elif LOCK.get('kappa') is not None:
            unk = {}
            for r in s2:
                g = OS.apply_gate(r['scores']['hier'], r['gate']['dist'], r['gate']['q95'], LOCK['kappa'])
                unk.setdefault(r['target'], []).append(float(np.mean(g == -1)))
            unk = {k: float(np.mean(v)) for k, v in unk.items()}
            bu = np.mean([v for k, v in unk.items() if labels[k] == 3]); ku = np.mean([v for k, v in unk.items() if labels[k] in (1, 2)])
            ok3 = bu >= .5 and ku <= .10
            L.append(f'| hier + cổng (κ={LOCK["kappa"]}) | | | | {bu*100:.1f}% | {ku*100:.1f}% |')
        else:
            ok3 = False
    else:
        ok3 = False
    v = dict(c1_no_harm=bool(ok1), c2_ball_S1=bool(ok2), c3_S2=bool(ok3), c4_flow_contrib=bool(ok4 and ok4neg))
    L += ['', '## Tiêu chí', '', *[f'- {k}: {"ĐẠT" if b else "KHÔNG ĐẠT"}' for k, b in v.items()]]
    (OUT / 'summary.json').write_text(json.dumps(v, indent=1)); (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=14); ap.add_argument('--report', action='store_true'); a = ap.parse_args()
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    files = ('PROTOCOL_ROUTER_VAL.md', 'router_val.py', 'router.py', 'router_common.py', 'branch_c.py', 'ball_rule.py', 'openset.py')
    h = {n: hashlib.sha256((R.P.ROOT / n).read_bytes()).hexdigest() for n in files} | {'lock.json': json.dumps(LOCK, sort_keys=True)}
    pre = OUT / 'prerun.sha256'
    if pre.exists() and json.loads(pre.read_text()) != h:
        raise ValueError('Frozen sources changed')
    pre.write_text(json.dumps(h, indent=2))
    if not a.report:
        todo = [('S1', 'hust', t, s, m) for m in (1, 2, 3) for t in HUST_T for s in R.SEEDS] + \
               [('S2', 'hust', t, s, 2) for t in HUST_T for s in R.SEEDS] + \
               [('S1', 'pb', t, s, m) for m in (1, 2, 4) for t in PB_T for s in R.SEEDS]
        todo = [t for t in todo if not (OUT / 'tasks' / name(t)).exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, fut in enumerate(as_completed([pool.submit(job, t) for t in todo]), 1):
                t, row = fut.result(); (OUT / 'tasks' / name(t)).write_text(json.dumps(row))
                if i % 50 == 0: print('val', i, '/', len(todo), flush=True)
    report()


if __name__ == '__main__':
    main()
