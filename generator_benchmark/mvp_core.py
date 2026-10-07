"""Leakage-aware CPU utilities and audited CWRU-only synthetic export.

No ground-truth label is passed to the detector feature extractor. Gate features
are engineering diagnostics, not physical certification. No external services.
"""
from pathlib import Path
import hashlib
import json
import math
import time

import numpy as np
from scipy import signal, stats
from scipy.io import loadmat
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import confusion_matrix, f1_score, roc_auc_score

from generators import FS, N, LABELS, ORDERS, features
from benchmark import cyclic_copy_correlations, quality_mask, write_json

CLASSES = ('healthy',) + LABELS
ROOT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def waveform_hash(row):
    return hashlib.sha256(np.asarray(row, dtype=np.float32).tobytes()).hexdigest()


def valid_rows(x):
    x = np.asarray(x)
    if x.ndim != 2 or x.shape[1] != N:
        raise ValueError('Expected waveform matrix (n,2048)')
    return np.isfinite(x).all(1) & (np.std(x, axis=1) > 1e-8)


def detector_features(x, rpm=1797.):
    """All three fault orders for EVERY row; no label-dependent extraction."""
    x = np.asarray(x, dtype=float)
    if not valid_rows(x).all() or not np.isfinite(rpm) or rpm <= 0:
        raise ValueError('Finite, nonconstant windows and positive RPM required')
    x = x - x.mean(1, keepdims=True)
    power = np.sqrt(np.mean(x*x, axis=1))
    time_stats = np.column_stack([np.log(power),
        stats.kurtosis(x, axis=1, fisher=False, bias=False),
        np.max(np.abs(x), axis=1) / power,
        np.mean(np.abs(x), axis=1) / power])
    f, p = signal.welch(x, FS, nperseg=512, axis=1)
    bands = np.column_stack([np.log(np.maximum(p[:, (f >= lo) & (f < lo+500)].sum(1), 1e-15))
                             for lo in range(0, FS//2, 500)])
    env = np.abs(signal.hilbert(x, axis=1))
    e = np.abs(np.fft.rfft(env-env.mean(1, keepdims=True), axis=1))**2
    freq = np.fft.rfftfreq(N, 1/FS)
    total = np.maximum(e.sum(1), 1e-15)
    orders = np.column_stack([np.log(np.maximum(e[:, np.abs(freq-order*rpm/60*h) <= 12].sum(1)/total, 1e-15))
                              for order in ORDERS.values() for h in (1, 2, 3)])
    return np.column_stack([time_stats, bands, orders])


def load_records(manifest, roles):
    """Open only explicitly allowed roles. Validate source digest before decoding."""
    result = {}
    for item in manifest:
        if item['role'] not in roles:
            continue
        path = Path(item['file'])
        if sha(path) != item['sha256']:
            raise ValueError(f'Source hash mismatch: {path}')
        mat = loadmat(path)
        key = f"X{item['id']:03d}_DE_time"
        raw = np.asarray(mat[key], dtype=float).ravel()
        # Anti-alias first; raw-file roles are disjoint. Per-window centering.
        x = signal.resample_poly(raw, 1, 4) if item['label'] == 'healthy' else raw
        x = x[:len(x)//N*N].reshape(-1, N).copy()
        x -= x.mean(1, keepdims=True)
        rpm = float(np.asarray(mat.get(f"X{item['id']:03d}RPM", item['rpm_fallback'])).ravel()[0])
        result[(item['role'], item['label'])] = {
            'x': x.astype(np.float32), 'rpm': rpm, 'source': item,
            'raw_samples': len(raw), 'channel': key}
    return result


def validate_splits(manifest):
    ids, hashes = set(), set()
    for row in manifest:
        if row['id'] in ids or row['sha256'] in hashes:
            raise ValueError('Duplicate recording/hash across roles')
        ids.add(row['id']); hashes.add(row['sha256'])
    return {'recordings': len(ids), 'unique_hashes': len(hashes),
            'bearing_independence': False, 'window_random_split': False}


def conformal_threshold(scores, alpha=.05):
    """Strict 'score > threshold'; exchangeability NOT assumed across loads."""
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 1 or not len(scores) or not np.isfinite(scores).all() or not 0 < alpha < 1:
        raise ValueError('Valid healthy calibration scores and alpha required')
    rank = math.ceil((len(scores)+1)*(1-alpha))
    if rank > len(scores):
        raise ValueError('Insufficient calibration sample count for requested alpha')
    return float(np.sort(scores)[rank-1])


def summary_metrics(y, probabilities, scores, threshold, valid=None):
    """Rejected sensor rows remain in denominators; no silent abstention benefit."""
    y = np.asarray(y, dtype=int)
    valid = np.ones(len(y), bool) if valid is None else np.asarray(valid, bool)
    pred = np.argmax(probabilities, axis=1)
    alarm = (np.asarray(scores) > threshold) & valid
    pred = np.where(valid, pred, -1)
    per_class = {CLASSES[k]: float(np.mean(pred[y == k] == k)) for k in range(4) if np.any(y == k)}
    recalls = {CLASSES[k]: float(alarm[y == k].mean()) for k in range(1, 4) if np.any(y == k)}
    healthy = y == 0
    return {'n': len(y), 'n_healthy': int(healthy.sum()), 'n_fault': int((~healthy).sum()),
        'coverage': float(valid.mean()), 'invalid_rows': int((~valid).sum()),
        'sensor_alert_rate': float((~valid).mean()),
        'accuracy': float((pred == y).mean()),
        'macro_f1': float(f1_score(y, pred, labels=list(range(4)), average='macro', zero_division=0)),
        'class_recall': per_class, 'fault_recall': recalls,
        'macro_fault_recall': float(np.mean(list(recalls.values()))),
        'fpr': float(alarm[healthy].mean()),
        'healthy_any_alert_rate': float((alarm | ~valid)[healthy].mean()),
        'threshold': float(threshold),
        'auc_valid_only': float(roc_auc_score((y > 0)[valid], np.asarray(scores)[valid])) if len(np.unique(y[valid] > 0)) == 2 else None,
        'confusion_labels': [-1, 0, 1, 2, 3],
        'confusion_matrix': confusion_matrix(y, pred, labels=[-1, 0, 1, 2, 3]).tolist()}


def fit_detector(real_features, synthetic_features, seed, weight=.5, trees=200):
    """Each class total weight=1. Fault class: fixed real/synthetic mixture.

    Counts therefore do not change class priors; real access remains identical.
    No class_weight/implicit duplication. One RF configuration for all methods.
    """
    if not 0 < weight < 1:
        raise ValueError('Synthetic weight must be in (0,1)')
    xs, ys, weights = [], [], []
    for k, label in enumerate(CLASSES):
        x = real_features[label]
        syn = synthetic_features.get(label)
        mass = 1. if syn is None else 1-weight
        xs.append(x); ys.extend([k]*len(x)); weights.extend([mass/len(x)]*len(x))
        if syn is not None:
            xs.append(syn); ys.extend([k]*len(syn)); weights.extend([weight/len(syn)]*len(syn))
    model = RandomForestClassifier(n_estimators=trees, min_samples_leaf=1,
        max_features='sqrt', random_state=seed, n_jobs=2, bootstrap=False)
    model.fit(np.concatenate(xs), np.asarray(ys), sample_weight=np.asarray(weights))
    return model, {'class_weight_totals': np.bincount(ys, weights=weights).tolist(),
                   'real_counts': {k: len(v) for k, v in real_features.items()},
                   'synthetic_counts': {k: len(v) for k, v in synthetic_features.items()},
                   'synthetic_class_mass': weight if synthetic_features else 0.}


def fit_healthy(x, seed):
    return IsolationForest(n_estimators=200, random_state=seed, n_jobs=2).fit(x)


def generic_gate(x, anchors, label, rpm):
    mask = quality_mask(x, anchors) & valid_rows(x)
    a = features(anchors, label, rpm)
    if mask.any():
        g = features(x[mask], label, rpm)
        mask[mask] &= ((g[:, 15:] >= a[:, 15:].min(0)-np.log(4)) &
                       (g[:, 15:] <= a[:, 15:].max(0)+np.log(4))).all(1)
    return mask


def export_library(generator, anchors, label, quota, seed, output, source, rpm,
                   near_copy=True, max_multiplier=4, batch_size=128):
    """Sharded export. Persist ALL attempts and retain failure diagnostics.

    No final manifest until all shards verify. Existing output refused. Source
    must be a verified train recording; unsupported condition cannot be requested.
    """
    if quota < 1 or max_multiplier < 1 or batch_size < 1:
        raise ValueError('Positive quota/batch/retry required')
    if source.get('role') != 'train' or source.get('label') != label:
        raise ValueError('A matching train source is required')
    if sha(source['file']) != source['sha256']:
        raise ValueError('Anchor source hash mismatch')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    config = {'label': label, 'quota': quota, 'seed': seed, 'method': generator.method,
        'rpm': rpm, 'near_copy': near_copy, 'max_multiplier': max_multiplier,
        'batch_size': batch_size, 'fs_hz': FS, 'window_samples': N,
        'gate_version': 'mvp-1', 'source': source,
        'anchor_array_sha256': hashlib.sha256(anchors.tobytes()).hexdigest(),
        'generator_code_sha256': sha(ROOT/'generators.py'), 'core_code_sha256': sha(Path(__file__))}
    write_json(output/'config.json', config)
    seen = {waveform_hash(a) for a in anchors}
    accepted = attempted = 0
    shards, reasons = [], {}
    started = time.perf_counter()
    with (output/'attempts.jsonl').open('w', encoding='utf-8') as ledger:
        while accepted < quota and attempted < quota*max_multiplier:
            count = min(batch_size, quota-accepted, quota*max_multiplier-attempted)
            batch_seed = seed+attempted
            waves, provenance = generator.sample(label, count, batch_seed)
            ok = generic_gate(waves, anchors, label, rpm)
            corr = np.zeros(count)
            if ok.any():
                corr[ok] = cyclic_copy_correlations(waves[ok], anchors)
            indices = []
            shard_name = f'shard_{len(shards):05d}.npy'
            for i, row in enumerate(waves):
                h = waveform_hash(row)
                reason = 'quality' if not ok[i] else 'near_copy' if near_copy and corr[i] > .99 else 'duplicate' if h in seen else None
                if reason is None:
                    seen.add(h); indices.append(i)
                else:
                    reasons[reason] = reasons.get(reason, 0)+1
                entry = {'attempt_id': attempted+i, 'accepted': reason is None,
                    'rejection_reason': reason, 'is_synthetic': True,
                    'label_type': 'local_augmentation', 'intended_fault_mechanism': label,
                    'source_record_id': source['id'], 'source_sha256': source['sha256'],
                    'source_role': 'train', 'config_hash': digest(config),
                    'fs_hz': FS, 'n_samples': N, 'units': 'source accelerometer units; not recalibrated',
                    'condition_support': 'observed_anchor_condition_only', 'rpm': rpm,
                    'background_recording_id': None, 'measured_severity_label': None,
                    'waveform_sha256': h, 'batch_seed': batch_seed,
                    'max_cyclic_anchor_corr': float(corr[i]) if ok[i] else None,
                    'shard': shard_name if reason is None else None,
                    'row_index': len(indices)-1 if reason is None else None,
                    'generator_metadata': provenance[i]}
                ledger.write(json.dumps(entry, allow_nan=False)+'\n')
            if indices:
                path = output/shard_name
                with (output/(shard_name+'.tmp')).open('wb') as stream:
                    np.save(stream, waves[indices])
                (output/(shard_name+'.tmp')).replace(path)
                shards.append({'file': shard_name, 'sha256': sha(path), 'rows': len(indices)})
            attempted += count; accepted += len(indices)
    audit = {'accepted': accepted, 'attempted': attempted, 'rejected': attempted-accepted,
             'reasons': reasons, 'seconds': time.perf_counter()-started, 'shards': shards,
             'config_hash': digest(config), 'attempt_ledger_sha256': sha(output/'attempts.jsonl')}
    audit['accepted_per_second'] = accepted/max(audit['seconds'], 1e-9)
    write_json(output/'audit.json', audit)
    if accepted != quota:
        write_json(output/'FAILED.json', {'reason': 'quota_exhausted', **audit})
        raise RuntimeError(f'Quota not met; see {output}')
    write_json(output/'manifest.json', {'complete': True, 'redistribution_permission': 'NOT established', **audit})
    return audit


def audit_library(output, anchors):
    output = Path(output)
    manifest = json.loads((output/'manifest.json').read_text())
    config = json.loads((output/'config.json').read_text())
    if digest(config) != manifest['config_hash'] or sha(output/'attempts.jsonl') != manifest['attempt_ledger_sha256']:
        raise ValueError('Config/ledger corruption')
    waves = []
    for shard in manifest['shards']:
        if sha(output/shard['file']) != shard['sha256']:
            raise ValueError('Shard corruption')
        x = np.load(output/shard['file'], allow_pickle=False)
        if len(x) != shard['rows'] or not valid_rows(x).all():
            raise ValueError('Invalid shard')
        waves.extend((shard['file'], i, row) for i, row in enumerate(x))
    attempts = [json.loads(s) for s in (output/'attempts.jsonl').read_text().splitlines()]
    accepted = [a for a in attempts if a['accepted']]
    if len(attempts) != manifest['attempted'] or len(accepted) != len(waves) or len(waves) != config['quota']:
        raise ValueError('Ledger/count mismatch')
    hashes = set()
    for (name, index, wave), meta in zip(waves, accepted):
        h = waveform_hash(wave)
        if (h != meta['waveform_sha256'] or h in hashes or name != meta['shard'] or
                index != meta['row_index'] or meta['source_role'] != 'train'):
            raise ValueError('Provenance/hash mismatch')
        hashes.add(h)
    array = np.array([w for _, _, w in waves])
    corr = cyclic_copy_correlations(array, anchors)
    if config['near_copy'] and np.any(corr > .99):
        raise ValueError('Near copy escaped gate')
    if not generic_gate(array, anchors, config['label'], config['rpm']).all():
        raise ValueError('Quality audit failed')
    return {'rows_verified': len(array), 'attempts_verified': len(attempts),
            'unique': len(hashes), 'max_anchor_corr': float(corr.max()),
            'median_anchor_corr': float(np.median(corr)), 'all_quality_pass': True}