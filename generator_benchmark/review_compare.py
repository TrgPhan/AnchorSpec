"""Recompute common development metrics using the newest explicitly supplied run.

Later input directories override earlier ones per method/seed/label. Mixed
budgets are reported, not called compute-matched. Heldout data never ranked.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from benchmark import load_split, evaluate, write_json, write_csv, SEEDS
from finalize_generation import fidelity_mask
from generators import LABELS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', nargs='+', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error('Choose new output directory')
    anchors, _, data, _ = load_split()
    selected = {}
    for folder in args.inputs:
        rows = json.loads((folder / 'development.json').read_text(encoding='utf-8'))
        for row in rows:
            selected[(row['method'], row['seed'], row['label'])] = (folder.resolve(), row)
    rows = []
    for (method, seed, label), (folder, old) in selected.items():
        x = np.load(folder / f'dev_{method}_{seed}_{label}.npy', allow_pickle=False)
        real, rpm = data[('development', label)]
        arpm = data[('anchor_train', label)][1]
        row = dict(old)
        row.update(evaluate(x, anchors[label], real, label, rpm, generated_rpm=arpm, anchor_rpm=arpm))
        row.update(fidelity_acceptance=float(fidelity_mask(x, anchors[label], label).mean()),
                   source_run=str(folder))
        rows.append(row)
    summary = []
    for method in sorted({r['method'] for r in rows}):
        values = [r for r in rows if r['method'] == method]
        if {(r['seed'], r['label']) for r in values} != {(s, l) for s in SEEDS for l in LABELS}:
            raise RuntimeError(f'Incomplete method: {method}')
        seed_w1 = [np.mean([r['feature_w1'] for r in values if r['seed'] == s]) for s in SEEDS]
        eligible = all(r['finite'] and r['acceptance_rate'] >= .95 and r['fidelity_acceptance'] >= .95
                       and r['unique_waveform_fraction'] == 1 and r['copy_fraction_corr_gt_099'] == 0
                       and r['repeat_seed_identical'] for r in values)
        summary.append({'method': method, 'eligible': eligible, 'mean_w1': float(np.mean(seed_w1)),
                        'seed_std_w1': float(np.std(seed_w1)),
                        'score': float(np.mean(seed_w1) + .25 * np.std(seed_w1)),
                        'min_sanity_acceptance': min(r['acceptance_rate'] for r in values),
                        'min_fidelity_acceptance': min(r['fidelity_acceptance'] for r in values),
                        'max_copy_fraction': max(r['copy_fraction_corr_gt_099'] for r in values),
                        'fit_seconds_3_seeds': sum(next(r['fit_seconds'] for r in values if r['seed'] == s) for s in SEEDS),
                        'source_runs': sorted({r['source_run'] for r in values})})
    eligible = [r for r in summary if r['eligible']]
    chosen = min(eligible, key=lambda r: r['score'])['method'] if eligible else None
    out.mkdir(parents=True)
    write_json(out / 'development.json', rows)
    write_csv(out / 'development.csv', rows)
    write_json(out / 'selection.json', {'selected': chosen, 'summary': summary,
               'scope': 'post-hoc exploratory review; fixed quota, NOT compute-matched or paper reproductions',
               'test_used_for_selection': False})
    print(json.dumps(summary, indent=2)); print('SELECTED', chosen)


if __name__ == '__main__':
    main()