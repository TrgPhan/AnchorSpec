"""Read existing evidence; write review audit into a NEW directory only.

All production rows checked; pair and phase-sweep sampling budgets explicit.
No heldout data used for phase sweep or parameter selection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import numpy as np
from generators import LABELS, constrained_surrogate, surrogate_diagnostics
from benchmark import (ROOT, load_split, cyclic_copy_correlations,
                       paired_cyclic_correlations, write_json)
from finalize_generation import fidelity_mask, produce
from generators import Generator


def distribution(values):
    return {"count": len(values), "quantiles_0_05_50_95_100":
            np.quantile(values, [0, .05, .5, .95, 1]).tolist(),
            "fraction_gt_099": float(np.mean(values > .99))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'results_v2')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error('New output directory required')
    out.mkdir(parents=True)
    anchors, bg, data, metadata = load_split()
    write_json(out / 'preprocessing_manifest.json', metadata)
    source = args.source.resolve()
    old_scale = json.loads((source / 'scale.json').read_text(encoding='utf-8'))
    records = []
    for label in LABELS:
        path = source / f'production_{label}.npy'
        x = np.load(path, allow_pickle=False)
        provenance = json.loads((source / f'production_{label}_provenance.json').read_text(encoding='utf-8'))
        hashes = [hashlib.sha256(row.tobytes()).hexdigest() for row in x]
        old = next(row for row in old_scale if row['label'] == label)
        corr = cyclic_copy_correlations(x, anchors[label])
        np.save(out / f'{label}_all_anchor_correlations.npy', corr)
        by_anchor = {i: [] for i in range(len(anchors[label]))}
        provenance_ok = len(provenance) == len(x)
        hist_ok = True
        for i, p in enumerate(provenance):
            j = p['anchor_window']
            by_anchor[j].append(i)
            provenance_ok &= (p.get('waveform_sha256') == hashes[i] and
                              p.get('global_sample_index') == i and p['label'] == label)
            hist_ok &= bool(np.array_equal(np.sort(x[i]), np.sort(anchors[label][j])))
        rng = np.random.default_rng(817)
        left, right = [], []
        for group in by_anchor.values():
            if len(group) >= 2:
                for _ in range(128):
                    a, b = rng.choice(group, 2, replace=False)
                    left.append(a); right.append(b)
        pairs = paired_cyclic_correlations(x[left], x[right])
        phase = [surrogate_diagnostics(anchors[label][p['anchor_window']], x[i])
                 for i, p in enumerate(provenance[:256])]
        real_baselines = {}
        for split in ('anchor_train', 'development', 'locked_test'):
            real = data[(split, label)][0]
            # Exclude self anchors; other windows remain same-record dependent.
            if split == 'anchor_train':
                real = real[len(anchors[label]):]
            real_baselines[split] = distribution(cyclic_copy_correlations(real, anchors[label]))
        record = {"label": label, "synthetic_anchor": distribution(corr),
                  "real_anchor_baselines": real_baselines,
                  "same_source_synthetic_pairs": distribution(pairs),
                  "anchor_usage": {str(i): len(g) for i, g in by_anchor.items()},
                  "provenance_hashes_match": bool(provenance_ok),
                  "source_histogram_preserved_all": bool(hist_ok),
                  "array_hash_matches_scale": hashlib.sha256(x.tobytes()).hexdigest() == old['array_sha256'],
                  "unique_hashes": len(set(hashes)), "finite": bool(np.isfinite(x).all()),
                  "fidelity_accepted": int(fidelity_mask(x, anchors[label], label).sum()),
                  "phase_diagnostics_first_256": phase}
        records.append(record)
        write_json(out / 'production_audit.json', records)
        print('AUDIT', label, record['synthetic_anchor'], 'hist', hist_ok, 'hash', record['array_hash_matches_scale'], flush=True)
    old_stress = json.loads((source / 'stress.json').read_text(encoding='utf-8'))
    stress = []
    g = Generator('constrained_surrogate', anchors, bg, 11)
    for old in old_stress:
        a, _, audit = produce(g, anchors, old['label'], old['quota'], old['seed'])
        b, _, _ = produce(g, anchors, old['label'], old['quota'], old['seed'])
        stress.append({"label": old['label'], "seed": old['seed'],
                       "repeat_identical": bool(np.array_equal(a, b)),
                       "old_array_hash_reproduced": audit['array_sha256'] == old['array_sha256']})
    write_json(out / 'stress_reproduction.json', stress)
    sweep = []
    for bound in (.35, .65, 1., 1.5, np.pi):
        for seed in (11, 29, 47):
            for label in LABELS:
                rng = np.random.default_rng(seed)
                waves = []
                for i in range(64):
                    waves.append(constrained_surrogate(anchors[label][i % len(anchors[label])], rng, phase_bound=bound))
                x = np.array(waves, dtype=np.float32)
                corr = cyclic_copy_correlations(x, anchors[label])
                sweep.append({"bound": float(bound), "seed": seed, "label": label,
                              "fidelity_acceptance": float(fidelity_mask(x, anchors[label], label).mean()),
                              "correlations": distribution(corr)})
        write_json(out / 'train_only_phase_sweep.json', sweep)
    write_json(out / 'protocol.json', {"scope": "post-hoc review, not fresh confirmatory evidence",
               "source": str(source), "all_production_rows": True,
               "same_source_pairs_per_anchor": 128, "sweep_samples_per_label_seed_bound": 64,
               "sweep_uses_only_anchors": True, "python": platform.python_version()})
    print('AUDIT COMPLETE', flush=True)


if __name__ == '__main__':
    main()