"""Production CLI for the ONE selected path: bounded-phase constrained surrogate.

Outputs synthetic windows, not a continuous physical recording. Fail closed if
quota/quality/duplicates fail. Inputs must contain calibrated fault waveforms.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from generators import Generator, LABELS, FS, N
from benchmark import load_split, write_json
from finalize_generation import produce


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True, choices=LABELS)
    parser.add_argument('--count', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=9001)
    parser.add_argument('--anchors', type=Path, help='Optional .npy: calibrated 12kHz DE windows shape (>=2,2048), one declared fault label')
    parser.add_argument('--fs', type=int, default=FS)
    parser.add_argument('--output', type=Path, required=True, help='New directory; existing output refused')
    args = parser.parse_args()
    if args.count < 1 or args.fs != FS:
        parser.error('count must be positive; only verified 12000Hz supported, no implicit resampling')
    if args.output.exists():
        parser.error('Output already exists; choose new run directory to avoid overwrite')
    if args.anchors:
        x = np.load(args.anchors, allow_pickle=False)
        if x.ndim != 2 or x.shape[1] != N or len(x) < 2 or not np.isfinite(x).all():
            parser.error('anchors must be finite array (>=2,2048)')
        x = x.astype(np.float32)
        x -= x.mean(axis=1, keepdims=True)
        if np.any(np.std(x, axis=1) < 1e-8):
            parser.error('zero/near-zero anchor not allowed')
        anchors = {label: x for label in LABELS}
        bg = np.zeros((1, N), dtype=np.float32)
        source = {'file': str(args.anchors.resolve()),
                  'sha256': hashlib.sha256(args.anchors.read_bytes()).hexdigest(),
                  'label_asserted_by_user': args.label}
    else:
        anchors, bg, _, _ = load_split()
        ids = {'inner': 105, 'outer': 130, 'ball': 118}
        source = {'dataset': 'CWRU', 'record_id': ids[args.label],
                  'windows': list(range(8)), 'stride': N, 'fs': FS,
                  'permission': 'No commercial/redistribution license verified'}
    g = Generator('constrained_surrogate', anchors, bg, args.seed)
    waves, provenance, audit = produce(g, anchors, args.label, args.count, args.seed)
    # Only create output after complete validated production.
    args.output.mkdir(parents=True)
    np.save(args.output / 'waveforms.npy', waves)
    write_json(args.output / 'provenance.json', provenance)
    write_json(args.output / 'manifest.json', {
        'generator': 'constrained_surrogate', 'version': 3,
        'source': source, 'fs_hz': FS, 'samples_per_window': N,
        'seed': args.seed, 'audit': audit, 'phase_bound_radians': .65,
        'iterations': 30, 'quality_gate': 'train RMS/crest and envelope harmonic range x4',
        'copy_gate': 'all candidates: max absolute cyclic anchor correlation <=0.99',
        'phase_bound_scope': 'intermediate spectral projection only; final rank projection may exceed bound',
        'label_status': 'synthetic variation of declared known fault',
        'not_claimed': ['new fault mechanism', 'independent physical incidents',
                        'continuous waveform', 'verified DENSO distribution'],
    })
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()