"""Post-hoc check (12/11, after PB-Flow): Truong's exact S3 recipe, not the locked flow_mix_0.25_30.

Recipe as described by Truong and implemented in s3_cpu_benchmark.py / s_additive.additive_training:
one flow sample per real fault window (ratio 1; also ratio 2 for "gen 2-3 times"), each synthetic row
weighted alpha = 0.25 of a real row, ADDED on top of the unchanged real weights.
Controls: real only, and exact copies of the real windows with the same ratio and weight.

XJTU: reuses the cached S3 flow features (data/s3_generation), so the flow rows are exactly Truong's.
Paderborn: same donors as PB-Flow; flow trained as pb_common.generate, but anchored one-to-one on each real window.
    python truong_recipe.py --workers 14
"""
import os
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from sklearn.ensemble import RandomForestClassifier as _RFC
import invariant_classifier as IC
from event_experts import causal_average
from diagnostic_experts import fault_labels
from t_readiness import selective
from s_additive import additive_training
from u_natural import LABEL, bearing
from s3_spectral import SpectralResidual, ResidualGenerator
import funnel as Fu
import pb_common as P

OUT = P.ROOT / 'results' / 'truong_recipe'
SEEDS = (11, 29, 47)
OFFSETS = (20261106, 1, 2)
DATA = P.ROOT.parent / 'data'


def use_trees(n):
    IC.RandomForestClassifier = lambda **kw: _RFC(**{**kw, 'n_estimators': n})


def score(xyw, seed, test):
    p = causal_average(IC.InvariantClassifier('rf', seed).fit(*xyw[:3]).predict_proba(test))
    return dict(cond=fault_labels(p).tolist(), sel=selective(p, 0).tolist())


def xjtu_job(task):
    target, seed, trees = task
    use_trees(trees)
    t = bearing(target); sources = [n for n in LABEL if n != target]
    events = [(n, LABEL[n], bearing(n)['terminal_features']) for n in sources]
    with np.load(DATA / 's_generation' / f'{target}_{seed}' / 'waveforms.npz') as z:
        di = z['duplicate_indices']
    dup = {n: {'duplicate': bearing(n)['terminal_features'][di[i * 20:(i + 1) * 20] - i * 10]} for i, n in enumerate(sources)}
    with np.load(DATA / 's3_generation' / f'{target}_{seed}' / 'features.npz') as f:
        flow = {n: {'flow': f[n + ':spectral_flow_half']} for n in sources}
    h = t['healthy_features'][:5]
    arms = {'real': additive_training(h, events, {}, 'real', 1., .25),
            'dup_r1': additive_training(h, events, dup, 'duplicate', 1., .25),
            'flow_r1': additive_training(h, events, flow, 'flow', 1., .25)}
    return dict(target=target, seed=seed, trees=trees, label=LABEL[target],
                scores={a: score(v, seed, t['terminal_features']) for a, v in arms.items()})


def pb_job(task):
    target, seed, trees = task
    use_trees(trees); start = time.perf_counter()
    t = P.item(target); H = P.item(P.healthy_for(target, seed)); rows = []
    for m in (1, 2, 4):
        donors = P.pick(P.INNER_REAL, target, seed, 1, m) + P.pick(P.OUTER_REAL, target, seed, 2, m)
        its = [P.item(n) for n in donors]; counts = Counter(i['label'] for i in its); k = len(its[0]['donor_w'])
        events = [(n, i['label'], i['donor']) for n, i in zip(donors, its)]
        waves = np.concatenate([i['donor_w'] for i in its]); groups = np.repeat(np.arange(len(its)), k)
        peak = np.repeat([np.abs(i['donor_w']).max() for i in its], k)
        cond = np.concatenate([[np.r_[np.eye(3)[{1: 0, 2: 1}[i['label']]], i['fr'], np.log(P.rig_rms())]] * k for i in its])
        wts = np.repeat([1 / counts[i['label']] for i in its], k)
        codec = SpectralResidual().fit(waves, groups, cond)
        gen = ResidualGenerator('flow', seed).fit(codec.z, codec.conditions[codec.pairs[:, 0]], wts[codec.pairs[:, 0]])
        scores = {'real': score(additive_training(H['base'], events, {}, 'real', 1., .25), seed, t['test'])}
        for r in (1, 2):
            dup = {n: {'duplicate': np.tile(i['donor'], (r, 1))} for n, i in zip(donors, its)}
            scores[f'dup_r{r}'] = score(additive_training(H['base'], events, dup, 'duplicate', float(r), .25), seed, t['test'])
            idx = np.concatenate([np.tile(np.arange(j * k, (j + 1) * k), r) for j in range(len(its))])
            for o in OFFSETS:
                res = gen.sample(codec.conditions[idx], seed + o) * codec.scale
                g, _ = codec.apply(waves[idx], res, P.STRENGTH, peak[idx])
                f = Fu.feats(g[:, None, :], its[0]['fs'], P.FR, P.ORDERS, P.SENSORS['1k'].bw_hz)
                flow = {n: {'flow': f[j * k * r:(j + 1) * k * r]} for j, n in enumerate(donors)}
                scores[f'flow_r{r}@{o}'] = score(additive_training(H['base'], events, flow, 'flow', float(r), .25), seed, t['test'])
        rows.append(dict(target=target, seed=seed, trees=trees, budget=m, label=t['label'], donors=donors, scores=scores))
    return dict(rows=rows, elapsed_seconds=time.perf_counter() - start)


def recall(r, arm, pol):
    keys = [k for k in r['scores'] if k == arm or k.startswith(arm + '@')]
    return float(np.mean([np.mean(np.asarray(r['scores'][k][pol]) == r['label']) for k in keys]))


def table(rows, arms, comps, classes, groups, rng):
    lab = {r['target']: r['label'] for r in rows}; L = []
    for gname, sub in groups:
        per = {(a, pol): {} for a in arms for pol in ('cond', 'sel')}
        for r in sub:
            for a, pol in per:
                per[a, pol].setdefault(r['target'], []).append(recall(r, a, pol))
        per = {k: {n: float(np.mean(v)) for n, v in d.items()} for k, d in per.items()}
        cells = ' | '.join(f"{P.macro(per[a, 'cond'], lab, classes) * 100:.1f} ({P.macro(per[a, 'sel'], lab, classes) * 100:.1f})" for a in arms)
        cs = []
        for a, b in comps:
            c = P.bootstrap(per[a, 'cond'], per[b, 'cond'], lab, rng, classes=classes)
            cs.append(f"{c['delta'] * 100:+.1f} [{c['ci95'][0] * 100:+.1f}; {c['ci95'][1] * 100:+.1f}]")
        L.append(f"| {gname} | {cells} | {' | '.join(cs)} |")
    return L


def report():
    rng = np.random.default_rng(20261112)
    xj = [json.loads(p.read_text()) for p in sorted((OUT / 'xjtu').glob('*.json'))]
    pb = [r for p in sorted((OUT / 'pb').glob('*.json')) for r in json.loads(p.read_text())['rows']]
    pb50 = [r for p in sorted((OUT / 'pb50').glob('*.json')) for r in json.loads(p.read_text())['rows']]
    L = ['# Kiểm tra đúng công thức của Trường (hậu nghiệm, ghi 12/11)', '',
         'Công thức: mỗi cửa sổ lỗi thật sinh 1 mẫu Flow (r1) hoặc 2 mẫu (r2); mỗi mẫu sinh nặng 0,25 mẫu thật, **cộng thêm** vào trọng số thật.',
         'Đối chứng `dup`: chép y nguyên cửa sổ thật, cùng số lượng và cùng trọng số. Ô: chỉ chọn loại lỗi (trong ngoặc: có lựa chọn khỏe).', '',
         '## XJTU, 13 ổ, mẫu Flow gốc của S3', '',
         '| RF | real | dup_r1 | flow_r1 | flow_r1 − real | dup_r1 − real | flow_r1 − dup_r1 |', '|---|---:|---:|---:|---|---|---|']
    L += table(xj, ('real', 'dup_r1', 'flow_r1'), (('flow_r1', 'real'), ('dup_r1', 'real'), ('flow_r1', 'dup_r1')), (1, 2, 4),
               [(f'{n} cây', [r for r in xj if r['trees'] == n]) for n in (50, 500)], rng)
    L += ['', '## Paderborn hỏng thật, RF 500 cây, Flow trung bình 3 hạt giống lấy mẫu', '',
          '| Sự cố/loại | real | dup_r1 | flow_r1 | dup_r2 | flow_r2 | flow_r1 − real | flow_r1 − dup_r1 | flow_r2 − real | flow_r2 − dup_r2 |',
          '|---:|---:|---:|---:|---:|---:|---|---|---|---|']
    L += table(pb, ('real', 'dup_r1', 'flow_r1', 'dup_r2', 'flow_r2'),
               (('flow_r1', 'real'), ('flow_r1', 'dup_r1'), ('flow_r2', 'real'), ('flow_r2', 'dup_r2')), (1, 2),
               [(m, [r for r in pb if r['budget'] == m]) for m in (1, 2, 4)], rng)
    if pb50:
        L += ['', '## Paderborn hỏng thật, RF 50 cây (cấu hình gốc của S3), Flow trung bình 3 hạt giống lấy mẫu', '',
              '| Sự cố/loại | real | dup_r1 | flow_r1 | dup_r2 | flow_r2 | flow_r1 − real | flow_r1 − dup_r1 | flow_r2 − real | flow_r2 − dup_r2 |',
              '|---:|---:|---:|---:|---:|---:|---|---|---|---|']
        L += table(pb50, ('real', 'dup_r1', 'flow_r1', 'dup_r2', 'flow_r2'),
                   (('flow_r1', 'real'), ('flow_r1', 'dup_r1'), ('flow_r2', 'real'), ('flow_r2', 'dup_r2')), (1, 2),
                   [(m, [r for r in pb50 if r['budget'] == m]) for m in (1, 2, 4)], rng)
    pf = {(r['target'], r['seed'], r['budget']): r for r in (json.loads(p.read_text()) for p in (P.ROOT / 'results' / 'pb_flow' / 'tasks').glob('*.json'))}
    same = sum(pf[r['target'], r['seed'], r['budget']]['scores']['real']['cond'] == r['scores']['real']['cond'] for r in pb)
    L += ['', f'Kiểm tra mã: nhánh `real` Paderborn trùng dự đoán với PB-Flow ở {same}/{len(pb)} lượt.']
    (OUT / 'summary.md').write_text('\n'.join(L), encoding='utf-8'); print('\n'.join(L))


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=14); ap.add_argument('--report', action='store_true'); a = ap.parse_args()
    for d in ('xjtu', 'pb', 'pb50'):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    if not a.report:
        xt = [(t, s, n) for n in (50, 500) for t in LABEL for s in SEEDS if not (OUT / 'xjtu' / f'{t}_{s}_{n}.json').exists()]
        pt = [(t, s, n) for n in (500, 50) for t in P.REAL for s in SEEDS
              if not (OUT / ('pb' if n == 500 else 'pb50') / f'{t}_{s}.json').exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for t, row in zip(xt, pool.map(xjtu_job, xt)):
                (OUT / 'xjtu' / f'{t[0]}_{t[1]}_{t[2]}.json').write_text(json.dumps(row))
            print('xjtu done', len(xt), flush=True)
            for i, (t, row) in enumerate(zip(pt, pool.map(pb_job, pt)), 1):
                (OUT / ('pb' if t[2] == 500 else 'pb50') / f'{t[0]}_{t[1]}.json').write_text(json.dumps(row))
                print('pb', i, '/', len(pt), t, round(row['elapsed_seconds'], 1), 's', flush=True)
    report()


if __name__ == '__main__':
    main()
