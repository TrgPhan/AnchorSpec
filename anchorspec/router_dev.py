"""PLAN.md WP5: one development run on UORED (PROTOCOL_ROUTER_DEV.md). Decisions are locked in results/router_dev/lock.json.
    python router_dev.py --smoke | --workers 14 | --report
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
import branch_c as BC
import ball_rule as BR
import openset as OS
from m_dev import Model

OUT = R.P.ROOT / 'results' / 'router_dev'
TARGETS = [i for c in (1, 2, 3, 4) for i in R.UORED_IDS[c]]
C_ARMS = ('c_copy', 'c_surr', 'c_trans', 'c_trans_flow', 'c_flowgain')
lab = lambda p: fault_labels(causal_average(p)).tolist()


def s1_job(target, seed, m):
    """All four classes in the library (m events each); ball and cage treated as 'no rule' -> branch C generators."""
    lib = R.library('uored', target, seed, m, (1, 2, 3, 4)); test = R.uored(target)['test_f']
    base, _ = R.real_base('uored', target, seed, lib); inj = R.injected('uored', target, seed)
    flow = R.fit_flow('uored', target, seed, lib)
    sc = {'real': lab(Model('rf500', seed).fit(*base).predict_proba(test))}
    sc['hier'], _ = RT.predict('uored', target, seed, lib, {}, test, flow, inj, base)
    for a in C_ARMS:
        sc[a], _ = RT.predict('uored', target, seed, lib, {'branch_c': a}, test, flow, inj, base)
    return dict(scenario='S1', target=target, seed=seed, budget=m, label=R.uored(target)['label'], lib={str(k): v for k, v in lib.items()}, scores=sc)


def s2_job(target, seed):
    """No ball event anywhere; 2 events for inner, outer, cage. Ball rule configs (branch A) and the unknown gate (branch D)."""
    lib = R.library('uored', target, seed, 2, (1, 2, 4)); test = R.uored(target)['test_f']
    base, events = R.real_base('uored', target, seed, lib); inj = R.injected('uored', target, seed)
    sc = {}
    p, m1, b1 = R.two_stage(base, {}, inj[0], seed, test, return_t1=True)
    sc['hier_noball'] = lab(p)
    h = R.target_healthy('uored', target, seed)
    ids = ['H'] * len(h['healthy_f']) + [n for n, c, f in events for _ in range(len(f))]
    dist, q95 = OS.gate_data(b1, ids, test)
    for cfg in BR.CONFIGS:
        sc[f'ball_{cfg}'], _ = RT.predict('uored', target, seed, lib, {'ball_rule': cfg}, test, None, inj, base)
    return dict(scenario='S2', target=target, seed=seed, budget=2, label=R.uored(target)['label'], lib={str(k): v for k, v in lib.items()},
                scores=sc, gate=dict(dist=dist.tolist(), q95=q95))


def job(task):
    start = time.perf_counter()
    row = s1_job(*task[1:]) if task[0] == 'S1' else s2_job(*task[1:])
    row['elapsed_seconds'] = time.perf_counter() - start
    return task, row


def name(t):
    return f'{t[0]}_{"_".join(map(str, t[1:]))}.json'


# ---------------- report + lock ----------------
def per_bearing(rows, arm):
    d = {}
    for r in rows:
        d.setdefault(r['target'], []).append(np.asarray(r['scores'][arm]) == r['label'])
    return {k: float(np.mean([np.mean(v) for v in vs])) for k, vs in d.items()}


def cls_mean(per, labels, classes):
    return float(np.mean([np.mean([v for k, v in per.items() if labels[k] == c]) for c in classes]))


def boot(A, B, labels, classes, rng, n=4000):
    g = {c: [k for k in A if labels[k] == c] for c in classes}
    f = lambda ks: np.mean([np.mean([A[k] - B[k] for k in ks if labels[k] == c]) for c in classes])
    bs = [f([x for c in classes for x in [g[c][i] for i in rng.integers(len(g[c]), size=len(g[c]))]]) for _ in range(n)]
    return float(f(list(A))), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]
    rng = np.random.default_rng(20261112); fmt = lambda t: f'{t[0]*100:+.1f} [{t[1]*100:+.1f}; {t[2]*100:+.1f}]'
    L = ['# ROUTER-DEV: một lượt phát triển trên UORED (PROTOCOL_ROUTER_DEV.md)', '', f'{len(rows)} lượt. Chỉ chọn loại lỗi, cửa sổ lỗi nặng. Recall từng lớp: trung bình theo ổ, mỗi ổ trung bình trên 8 seed.', '']
    lock = {'fneo': True}
    # ---- S1: branch C
    s1 = [r for r in rows if r['scenario'] == 'S1']; labels = {r['target']: r['label'] for r in s1}
    arms = ('real', 'hier') + C_ARMS
    L += ['## S1: nhánh C (bi và vòng cách coi là không có luật vật lý)', '',
          '| m | Nhánh | Trong | Ngoài | Bi | Cách | Macro 4 lớp | Không-luật (bi+cách) | Không-luật − hier (CI 95%) | Không-luật − photocopy (CI 95%) |', '|---:|---|---:|---:|---:|---:|---:|---:|---|---|']
    agg = {a: {'nr': [], 'macro': []} for a in arms}
    for m in (1, 2):
        sub = [r for r in s1 if r['budget'] == m]; per = {a: per_bearing(sub, a) for a in arms}
        for a in arms:
            cl = [cls_mean(per[a], labels, (c,)) for c in (1, 2, 3, 4)]; nr = cls_mean(per[a], labels, (3, 4)); mac = float(np.mean(cl))
            agg[a]['nr'].append(nr); agg[a]['macro'].append(mac)
            c1 = '' if a in ('real', 'hier') else fmt(boot({k: per[a][k] for k in per[a] if labels[k] in (3, 4)}, per['hier'], labels, (3, 4), rng))
            c2 = '' if a in ('real', 'hier', 'c_copy') else fmt(boot({k: per[a][k] for k in per[a] if labels[k] in (3, 4)}, per['c_copy'], labels, (3, 4), rng))
            L.append(f'| {m} | {a} | ' + ' | '.join(f'{v*100:.1f}' for v in cl) + f' | {mac*100:.1f} | {nr*100:.1f} | {c1} | {c2} |')
    nr = {a: float(np.mean(v['nr'])) for a, v in agg.items()}; mac = {a: float(np.mean(v['macro'])) for a, v in agg.items()}
    cands = [a for a in C_ARMS if a != 'c_copy' and nr[a] > nr['c_copy'] and mac[a] >= mac['hier'] - .01]
    if cands:
        best = max(cands, key=lambda a: nr[a])
        flowc = [a for a in cands if 'flow' in a and nr[a] >= nr[best] - .01]
        choice = max(flowc, key=lambda a: nr[a]) if flowc else best
    else:
        choice = 'c_none'
    lock['branch_c'] = choice
    L += ['', '**Trung bình hai mức m** (không-luật / macro): ' + '; '.join(f'{a} {nr[a]*100:.1f} / {mac[a]*100:.1f}' for a in arms),
          f'\n**Khóa nhánh C:** `{choice}` (ứng viên đạt: {cands or "không có"}).', '']
    # ---- S2: ball rule + gate
    s2 = [r for r in rows if r['scenario'] == 'S2']; labels2 = {r['target']: r['label'] for r in s2}
    L += ['## S2: không có sự cố bi nào (luật bi ở nhánh A; cổng "chưa biết" ở nhánh D)', '',
          '| Nhánh | Trong | Ngoài | Bi | Cách | Trong+ngoài − hier_noball (CI 95%) | Bi − hier_noball (CI 95%) |', '|---|---:|---:|---:|---:|---|---|']
    per2 = {a: per_bearing(s2, a) for a in ['hier_noball'] + [f'ball_{c}' for c in BR.CONFIGS]}
    passing = {}
    for a, pa in per2.items():
        cl = [cls_mean(pa, labels2, (c,)) for c in (1, 2, 3, 4)]
        io = boot({k: v for k, v in pa.items() if labels2[k] in (1, 2)}, per2['hier_noball'], labels2, (1, 2), rng) if a != 'hier_noball' else None
        bb = boot({k: v for k, v in pa.items() if labels2[k] == 3}, per2['hier_noball'], labels2, (3,), rng) if a != 'hier_noball' else None
        L.append(f'| {a} | ' + ' | '.join(f'{v*100:.1f}' for v in cl) + f" | {fmt(io) if io else ''} | {fmt(bb) if bb else ''} |")
        if a != 'hier_noball':
            ball_ci_lo = boot({k: v for k, v in pa.items() if labels2[k] == 3}, {k: 0. for k in pa}, labels2, (3,), rng)[1]
            if cl[2] >= .30 and ball_ci_lo > 0 and io[0] >= -.03:
                passing[a[5:]] = cl[2]
    lock['ball_rule'] = max(passing, key=passing.get) if passing else None
    L += ['', f"**Khóa luật bi:** {lock['ball_rule'] or 'không cấu hình nào đạt'} (đạt: {passing or 'không'}).", '']
    # gate
    L += ['### Cổng "chưa biết" (trên hier_noball)', '', '| κ | Cửa sổ bi báo "chưa biết" | Cửa sổ lớp đã biết bị báo "chưa biết" |', '|---:|---:|---:|']
    choice_k = None
    for kp in OS.KAPPAS:
        unk = {}
        for r in s2:
            g = OS.apply_gate(r['scores']['hier_noball'], r['gate']['dist'], r['gate']['q95'], kp)
            unk.setdefault(r['target'], []).append(float(np.mean(g == -1)))
        unk = {k: float(np.mean(v)) for k, v in unk.items()}
        ball_u = cls_mean(unk, labels2, (3,)); known_u = cls_mean(unk, labels2, (1, 2, 4))
        L.append(f'| {kp} | {ball_u*100:.1f}% | {known_u*100:.1f}% |')
        if choice_k is None and known_u <= .10:
            choice_k = kp
    lock['kappa'] = choice_k
    L += ['', f'**Khóa κ:** {choice_k}.', '', '```json', json.dumps(lock, indent=1), '```']
    (OUT / 'lock.json').write_text(json.dumps(lock, indent=1))
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=14); ap.add_argument('--report', action='store_true')
    ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    if a.smoke:
        for t in (('S1', 12, 11, 1), ('S2', 12, 11)):
            _, row = job(t); print(t, round(row['elapsed_seconds'], 1), 's', {k: round(float(np.mean(np.asarray(v) == row['label'])), 2) for k, v in row['scores'].items()})
        return
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    files = ('PROTOCOL_ROUTER_DEV.md', 'router_dev.py', 'router.py', 'router_common.py', 'branch_c.py', 'ball_rule.py', 'openset.py')
    h = {n: hashlib.sha256((R.P.ROOT / n).read_bytes()).hexdigest() for n in files}
    pre = OUT / 'prerun.sha256'
    if pre.exists() and json.loads(pre.read_text()) != h:
        raise ValueError('Frozen sources changed')
    pre.write_text(json.dumps(h, indent=2))
    if not a.report:
        todo = [('S1', t, s, m) for m in (1, 2) for t in TARGETS for s in R.SEEDS] + [('S2', t, s) for t in TARGETS for s in R.SEEDS]
        todo = [t for t in todo if not (OUT / 'tasks' / name(t)).exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, fut in enumerate(as_completed([pool.submit(job, t) for t in todo]), 1):
                t, row = fut.result()
                (OUT / 'tasks' / name(t)).write_text(json.dumps(row))
                if i % 40 == 0: print('dev', i, '/', len(todo), flush=True)
    report()


if __name__ == '__main__':
    main()
