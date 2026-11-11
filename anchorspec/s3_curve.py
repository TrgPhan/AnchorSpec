"""S3 data-efficiency curve: how much real fault data does each method need?

Question (mentor, 11/11): "phương pháp thường cần bao nhiêu dữ liệu lỗi để đạt mức X,
phương pháp của nhóm cần bao nhiêu". This script answers it on XJTU-SY with the frozen
S3 configuration, varying only the amount of real fault data per donor bearing.

For every held-out target bearing (13), seed (11, 29, 47) and budget k (real terminal
windows kept per donor bearing):
  real : RF trained on 5 healthy windows of the target + k real fault windows per donor.
  flow : same real rows + 10 S3 flow samples per donor (strength 0.5, alpha 0.25).
         Codec, generator and anchors use ONLY the k kept windows of each donor.
The target bearing's faults never enter training or generation (leave-one-bearing-out).
Budget k=10 is the original S3 setting and should reproduce results/priorities
(real ~86.9 / 76.3, flow ~95.7 / 82.9 avg precision / recall, healthy+terminal stage).

Run from anchorspec/ after `python u_download.py; python u_natural.py prepare`:
    python s3_curve.py --workers 3
    python s3_curve.py --report          # rebuild tables/plot from saved tasks
Outputs: results/s3_curve/{tasks/*.json, curve.csv, curve.md, curve.png}
"""
import os
for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(variable, '1')
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from s3_spectral import SpectralResidual, ResidualGenerator
from u_natural import LABEL, ORDERS, bearing, training
from invariant_classifier import InvariantClassifier
from event_experts import causal_average
from t_readiness import selective
import funnel as Fu

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results/s3_curve'
SEEDS = (11, 29, 47)
BUDGETS = (2, 3, 5, 10)          # real fault windows kept per donor bearing (k=1 has no same-bearing pairs)
SYNTH_PER_DONOR = 10             # generated rows added per donor, as in the main S3 run
STRENGTH, ALPHA = .5, .25
LABELS = (-1, 0, 1, 2, 3, 4)
CLASSES = (0, 1, 2, 4)           # healthy, inner, outer, cage


def kept(seed, donor, k):
    rng = np.random.default_rng([seed, int(donor[0]), int(donor[-1]), k, 20261111])
    return np.sort(rng.choice(10, size=k, replace=False))


def predict(model, t):
    out = {}
    for stage in ('healthy', 'terminal'):
        x = t[stage + '_features'][5:] if stage == 'healthy' else t[stage + '_features']
        out[stage] = selective(causal_average(model.predict_proba(x)), 0).tolist()
    return out


def job(task):
    target, seed, k = task; start = time.perf_counter()
    t = bearing(target); donors = [n for n in LABEL if n != target]
    subsets = {n: kept(seed, n, k) for n in donors}
    events = [(n, LABEL[n], bearing(n)['terminal_features'][subsets[n]]) for n in donors]
    healthy = t['healthy_features'][:5]
    row = dict(target=target, seed=seed, budget=k, label=LABEL[target], scores={}, counts={})
    # --- real only
    x, y, w = training(healthy, events, {}, 'real')
    row['scores']['real'] = predict(InvariantClassifier('rf', seed).fit(x, y, w), t)
    row['counts']['real'] = dict(real_fault_windows=k * len(donors), synthetic=0)
    # --- S3 flow on the kept windows only
    waves, conditions, weights, groups, limits = [], [], [], [], []
    counts = Counter(LABEL[n] for n in donors)
    for g, n in enumerate(donors):
        s = bearing(n); sel = s['terminal'][subsets[n]]
        c = np.r_[np.eye(3)[{1: 0, 2: 1, 4: 2}[LABEL[n]]], float(s['fr']), np.log(np.sqrt(np.mean(s['healthy'][:5] ** 2)))]
        waves.append(sel); conditions.extend([c] * k); weights.extend([1 / counts[LABEL[n]]] * k); groups.extend([g] * k)
        limits.append(np.abs(sel).max())
    waves = np.concatenate(waves)
    codec = SpectralResidual().fit(waves, np.asarray(groups), np.asarray(conditions))
    gen = ResidualGenerator('flow', seed).fit(codec.z, codec.conditions[codec.pairs[:, 0]], np.asarray(weights)[codec.pairs[:, 0]])
    anchor_idx = np.concatenate([g * k + (np.arange(SYNTH_PER_DONOR) % k) for g in range(len(donors))])
    residuals = gen.sample(codec.conditions[anchor_idx], seed + 20261111) * codec.scale
    peak = np.repeat(np.asarray(limits), SYNTH_PER_DONOR)
    generated, _ = codec.apply(waves[anchor_idx], residuals, STRENGTH, peak)
    xs, ys, ws = [x], [y], [w]
    scale = len(x) / (1 + len(counts))
    for g, n in enumerate(donors):
        feats = Fu.feats(generated[g * SYNTH_PER_DONOR:(g + 1) * SYNTH_PER_DONOR, None, :], 4000, float(bearing(n)['fr']), ORDERS)
        xs.append(feats); ys.append(np.full(len(feats), LABEL[n], int))
        ws.append(np.full(len(feats), ALPHA * scale / (counts[LABEL[n]] * SYNTH_PER_DONOR)))
    model = InvariantClassifier('rf', seed).fit(np.concatenate(xs), np.concatenate(ys), np.concatenate(ws))
    row['scores']['flow'] = predict(model, t)
    row['counts']['flow'] = dict(real_fault_windows=k * len(donors), synthetic=SYNTH_PER_DONOR * len(donors),
                                 generator_training_seconds=gen.training_seconds, pairs=int(len(codec.pairs)))
    row['elapsed_seconds'] = time.perf_counter() - start
    return row


def metrics(rows, method):
    m = np.zeros((6, 6), int)
    for r in rows:
        for stage in ('healthy', 'terminal'):
            truth = 0 if stage == 'healthy' else r['label']
            for p in r['scores'][method][stage]: m[LABELS.index(truth), LABELS.index(p)] += 1
    prec, rec = [], []
    for c in CLASSES:
        i = LABELS.index(c); tp = m[i, i]; issued = m[:, i].sum(); support = m[i].sum()
        prec.append(tp / issued if issued else 0.); rec.append(tp / support if support else 0.)
    return dict(accuracy=float(np.trace(m) / m.sum()), avg_precision=float(np.mean(prec)), avg_recall=float(np.mean(rec)),
                predictions=int(m.sum()))


def needed(curve, metric, level):
    """Smallest budget (linear interpolation) at which `metric` reaches `level`; None if never."""
    ks = sorted(curve); vals = [curve[k][metric] for k in ks]
    if vals[0] >= level: return float(ks[0])
    for (k0, v0), (k1, v1) in zip(zip(ks, vals), zip(ks[1:], vals[1:])):
        if v0 < level <= v1: return k0 + (level - v0) / (v1 - v0) * (k1 - k0)
    return None


def report():
    rows = [json.loads(p.read_text())['row'] for p in sorted((OUT / 'tasks').glob('*.json'))]
    table = []; curve = {'real': {}, 'flow': {}}
    for k in BUDGETS:
        sub = [r for r in rows if r['budget'] == k]
        if len(sub) != 13 * len(SEEDS): continue
        for method in ('real', 'flow'):
            mt = metrics(sub, method); curve[method][k] = mt
            table.append(dict(budget=k, real_fault_windows_total=k * 12, method=method, **mt))
    import csv
    with (OUT / 'curve.csv').open('w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(table[0])); wr.writeheader(); wr.writerows(table)
    lines = ['# S3 data-efficiency curve (XJTU-SY, 13 bearings LOBO, 3 seeds, healthy+terminal, 4 classes)', '',
             '| Cửa sổ lỗi thật / ổ | Tổng cửa sổ lỗi thật | Chỉ mẫu thật P / R / Acc | + AnchorSpec Flow P / R / Acc |', '|---:|---:|---|---|']
    for k in sorted(curve['real']):
        a, b = curve['real'][k], curve['flow'][k]
        lines.append(f"| {k} | {k*12} | {a['avg_precision']*100:.1f} / {a['avg_recall']*100:.1f} / {a['accuracy']*100:.1f} | "
                     f"{b['avg_precision']*100:.1f} / {b['avg_recall']*100:.1f} / {b['accuracy']*100:.1f} |")
    lines += ['', '## Dữ liệu lỗi thật cần để đạt mức của "chỉ mẫu thật, đủ 10 cửa sổ/ổ"', '']
    full = curve['real'].get(10)
    if full:
        for metric in ('avg_precision', 'avg_recall', 'accuracy'):
            level = full[metric]; kr = needed(curve['real'], metric, level); kf = needed(curve['flow'], metric, level)
            ratio = f'{kr / kf:.1f} lần' if kr and kf else 'n/a'
            lines.append(f"- {metric} = {level*100:.1f}%: chỉ mẫu thật cần {kr if kr is None else round(kr,1)} cửa sổ/ổ; "
                         f"AnchorSpec Flow cần {kf if kf is None else round(kf,1)} cửa sổ/ổ → ít hơn {ratio}.")
    lines += ['', 'Cửa sổ của cùng một ổ không phải sự kiện độc lập; 13 ổ bi là đơn vị độc lập. Kết quả thăm dò, không phải xác nhận.']
    (OUT / 'curve.md').write_text('\n'.join(lines), encoding='utf-8'); print('\n'.join(lines))
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), dpi=160)
    for ax, metric, name in ((axs[0], 'avg_precision', 'Avg Precision'), (axs[1], 'avg_recall', 'Avg Recall')):
        for method, col, lab in (('real', '#94A3B8', 'Chỉ mẫu thật'), ('flow', '#10B981', '+ AnchorSpec Flow')):
            ks = sorted(curve[method]); ax.plot([k * 12 for k in ks], [curve[method][k][metric] * 100 for k in ks], 'o-', color=col, lw=2.5, label=lab)
        ax.set_title(name); ax.set_xlabel('Số cửa sổ lỗi thật dùng để học'); ax.set_ylabel('%'); ax.grid(alpha=.3)
    axs[0].legend(); fig.tight_layout(); fig.savefig(OUT / 'curve.png')


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=3); ap.add_argument('--report', action='store_true')
    a = ap.parse_args(); (OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    if not a.report:
        todo = [(t, s, k) for k in BUDGETS for t in LABEL for s in SEEDS if not (OUT / 'tasks' / f'{t}_{s}_k{k}.json').exists()]
        with ProcessPoolExecutor(a.workers) as pool:
            for i, (task, row) in enumerate(zip(todo, pool.map(job, todo)), 1):
                (OUT / 'tasks' / f'{task[0]}_{task[1]}_k{task[2]}.json').write_text(json.dumps(dict(row=row)))
                print('curve', i, '/', len(todo), task, round(row['elapsed_seconds'], 1), 's', flush=True)
    report()


if __name__ == '__main__': main()
