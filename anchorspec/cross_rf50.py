"""Post-hoc (12/11): Truong's recipe (real + S3 Flow, within-event pairs, strength 0.5, 1 per real window, +0.25 additive, RF 50)
vs real only (RF 50), photocopy +0.25 (RF 50) and hier, on Paderborn, HUST, UORED (4 classes), XJTU. Only-fault-type scoring, 8 seeds."""
import os, json
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import invariant_classifier as IC
from event_experts import causal_average
from diagnostic_experts import fault_labels
import router_common as R
import branch_c as BC
import v4_flow as V

OUT = R.P.ROOT / 'results' / 'cross_rf50'
CLS = {'pb': (1, 2), 'hust': (1, 2, 3), 'uored': (1, 2, 3, 4), 'xjtu': (1, 2, 4)}
BUD = {'pb': (1, 2, 4), 'hust': (1, 2, 3), 'uored': (1, 2), 'xjtu': (0,)}


def targets(ds):
    if ds == 'pb': return list(R.P.REAL)
    if ds == 'hust': return [k for c in (1, 2, 3) for k in R.HUST_IDS[c]]
    if ds == 'uored': return [k for c in (1, 2, 3, 4) for k in R.UORED_IDS[c]]
    return [k for v in R.xjtu_ids().values() for k in v]


def job(task):
    ds, tg, s, m = task
    lib = R.library(ds, tg, s, m, CLS[ds]); test = R.record(ds, tg)['test_f']
    base, events = R.real_base(ds, tg, s, lib); inj = R.injected(ds, tg, s)
    codec, gen = R.fit_flow(ds, tg, s, lib)                    # S3 flow, within-event pairs, all fault classes
    flow_rows, copy_rows = {}, {}
    for c, keys in lib.items():
        for k in keys:
            rec = R.record(ds, k); idx = np.arange(len(rec['donor_w']))
            q = codec.conditions[[i for i in range(len(codec.conditions))]]  # placeholder (conditions are per library window)
            w = R.flow_variants(codec, gen, rec['donor_w'], c, float(np.mean(rec['donor_fr'])), s + 20261106)
            flow_rows.setdefault(c, []).append(BC._src_feats(rec, w, idx)); copy_rows.setdefault(c, []).append(rec['donor_f'])
    flow_rows = {c: np.concatenate(v) for c, v in flow_rows.items()}; copy_rows = {c: np.concatenate(v) for c, v in copy_rows.items()}
    rf = lambda xyw: fault_labels(causal_average(IC.InvariantClassifier('rf', s).fit(*xyw).predict_proba(test))).tolist()   # RF 50 (locked default)
    sc = {'real_rf50': rf(base), 'copy_add_rf50': rf(V.add_rows(base, copy_rows)), 'flow_within_rf50': rf(V.add_rows(base, flow_rows)),
          'hier': V.predict_arm('hier', ds, tg, s, lib, base, inj, test, {})}
    return task, dict(ds=ds, target=str(tg) if not isinstance(tg, tuple) else f'{tg[0]}{tg[1]}', seed=s, budget=m, label=R.record(ds, tg)['label'], scores=sc)


def name(t):
    tg = f'{t[1][0]}{t[1][1]}' if isinstance(t[1], tuple) else t[1]
    return f'{t[0]}_{tg}_{t[2]}_{t[3]}.json'


def metrics(sub, a, C):
    m = np.zeros((5, 5))
    for r in sub:
        for p in r['scores'][a]: m[r['label'], p] += 1
    pr = [m[c, c] / m[:, c].sum() if m[:, c].sum() else 0. for c in C]; rc = [m[c, c] / m[c].sum() for c in C]
    return float(np.mean(pr)), float(np.trace(m) / m.sum()), float(np.mean(rc))


def report():
    rows = [json.loads(p.read_text()) for p in sorted((OUT / 'tasks').glob('*.json'))]
    ARMS = [('real_rf50', 'Chỉ dữ liệu thật, RF 50'), ('copy_add_rf50', 'Thật + photocopy (cộng 0,25), RF 50'), ('flow_within_rf50', 'Thật + Flow within 0,5 (cộng 0,25), RF 50')] + \
           [(f'flow_within_{st}_rf50', f'Thật + Flow within {st} (cộng 0,25), RF 50') for st in (.25, .3, .75, 1.) if f'flow_within_{st}_rf50' in rows[0]['scores']] + [('hier', 'hier (chốt)')]
    rng = np.random.default_rng(7); L = ['# Chéo bộ dữ liệu: công thức Trường (RF 50) so với chỉ thật và hier', '', 'Chỉ chọn loại lỗi; ma trận nhầm lẫn gộp; 8 seed. ΔRecall so với chỉ thật RF 50: bootstrap theo ổ.', '']
    for ds, title in (('pb', 'Paderborn (trong/ngoài, 11 ổ)'), ('hust', 'HUST (trong/ngoài/bi, 14 ổ)'), ('uored', 'UORED (4 lớp, 20 ổ)'), ('xjtu', 'XJTU (trong/ngoài/cách, 13 ổ)')):
        C = CLS[ds]; L += [f'## {title}', '', '| Sự cố/loại | Phương pháp | Avg Precision | Accuracy | Avg Recall | ΔAvg Recall so với chỉ thật (CI 95%) |', '|---:|---|---:|---:|---:|---|']
        for m in BUD[ds] + (('TB',) if len(BUD[ds]) > 1 else ()):
            sub = [r for r in rows if r['ds'] == ds and (m == 'TB' or r['budget'] == m)]
            if not sub: continue
            tg = sorted({r['target'] for r in sub}); lab = {r['target']: r['label'] for r in sub}
            G = {c: [t for t in tg if lab[t] == c] for c in C}; by = {t: [r for r in sub if r['target'] == t] for t in tg}
            bs = {a: [] for a, _ in ARMS}
            for _ in range(500):
                s2 = [r for c in C for i in rng.integers(len(G[c]), size=len(G[c])) for r in by[G[c][i]]]; b0 = metrics(s2, 'real_rf50', C)[2]
                for a, _ in ARMS: bs[a].append(metrics(s2, a, C)[2] - b0)
            b0 = metrics(sub, 'real_rf50', C)[2]
            for a, n in ARMS:
                p, acc, rc = metrics(sub, a, C)
                d = '' if a == 'real_rf50' else f'{(rc-b0)*100:+.1f} [{np.percentile(bs[a],2.5)*100:+.1f}; {np.percentile(bs[a],97.5)*100:+.1f}]'
                L.append(f'| {m if m else "tự nhiên"} | {n} | {p*100:.1f} | {acc*100:.1f} | {rc*100:.1f} | {d} |')
        L.append('')
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


if __name__ == '__main__':
    (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    todo = [(ds, t, s, m) for ds in ('pb', 'hust', 'uored', 'xjtu') for m in BUD[ds] for t in targets(ds) for s in R.SEEDS]
    todo = [t for t in todo if not (OUT / 'tasks' / name(t)).exists()]
    with ProcessPoolExecutor(14) as ex:
        for i, f in enumerate(as_completed([ex.submit(job, t) for t in todo]), 1):
            t, row = f.result(); (OUT / 'tasks' / name(t)).write_text(json.dumps(row))
            if i % 100 == 0: print('cross', i, '/', len(todo), flush=True)
    report()
