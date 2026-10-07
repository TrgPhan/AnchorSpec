"""Generation-first benchmark with development selection and locked-load test.

Run from any directory. No classifier is fitted. Windows are NOT independent
bearing samples. Original prototypes are NOT reproductions of paper results.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import platform
import time

import numpy as np
import scipy
from scipy import signal, stats
from scipy.io import loadmat

from generators import FS, N, LABELS, Generator, features, rms

ROOT = Path(__file__).resolve().parent
METHODS = Generator.METHODS + ("gan_prototype", "ddpm_prototype")
SEEDS = (11, 29, 47)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def load_split():
    manifest = json.loads((ROOT / "data_manifest.json").read_text(encoding="utf-8"))
    data, metadata = {}, []
    for entry in manifest:
        path = Path(entry["file"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Hash mismatch: {path}")
        mat = loadmat(path)
        # 99.mat also contains X098 arrays: explicit ID matching prevents leak.
        key = f"X{entry['id']:03d}_DE_time"
        raw = mat[key].ravel().astype(float)
        healthy = entry["label"] == "healthy"
        native_fs = 48000 if healthy else FS
        x = signal.resample_poly(raw, 1, 4) if healthy else raw
        x -= x.mean()
        windows = x[:len(x) // N * N].reshape(-1, N).astype(np.float32)
        rpm_keys = [k for k in mat if k == f"X{entry['id']:03d}RPM"]
        rpm = float(mat[rpm_keys[0]].ravel()[0]) if rpm_keys else (1796, 1772, 1750)[entry["load_hp"]]
        data[(entry["split"], entry["label"])] = (windows, rpm)
        metadata.append({**entry, "mat_key": key, "raw_samples": len(raw),
                         "native_fs_hz": native_fs, "windows": len(windows), "rpm": rpm,
                         "fs_note": "Normal DE 48k is working assumption; official normal page omits per-file fs. Rotor peak sanity checked separately." if healthy else "Official 12k fault page",
                         "window_samples": N, "window_overlap": 0})
    anchors = {label: data[("anchor_train", label)][0][:8] for label in LABELS}
    backgrounds = data[("anchor_train", "healthy")][0][:20]
    return anchors, backgrounds, data, metadata


def cyclic_copy_correlations(x, anchors):
    """All rows: maximum absolute normalized correlation over anchors/shifts.

    Nonfinite and constant rows are invalid inputs, not evidence of diversity.
    Float64 avoids float32 roundoff near the copy threshold. Inputs not mutated.
    """
    x, anchors = np.asarray(x, dtype=float), np.asarray(anchors, dtype=float)
    if (x.ndim != 2 or anchors.ndim != 2 or not len(anchors) or
            x.shape[1] != anchors.shape[1] or
            not np.isfinite(x).all() or not np.isfinite(anchors).all()):
        raise ValueError("Correlation requires finite 2D arrays of equal window length")
    a = anchors - anchors.mean(axis=1, keepdims=True)
    y = x - x.mean(axis=1, keepdims=True)
    an, yn = np.linalg.norm(a, axis=1, keepdims=True), np.linalg.norm(y, axis=1, keepdims=True)
    if np.any(an <= 1e-15) or np.any(yn <= 1e-15):
        raise ValueError("Constant waveforms have undefined correlation")
    a /= an
    y /= yn
    af = np.fft.rfft(a, axis=1)
    maxima = []
    for row in y:
        cross = np.fft.irfft(np.fft.rfft(row)[None, :] * af.conj(), n=x.shape[1], axis=1)
        maxima.append(float(np.clip(np.max(np.abs(cross)), 0, 1)))
    return np.array(maxima)


def paired_cyclic_correlations(x, y):
    """One correlation per matched pair, maximizing over shifts and sign."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.shape != y.shape or x.ndim != 2 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Pairs require matching finite 2D arrays")
    x = x - x.mean(1, keepdims=True)
    y = y - y.mean(1, keepdims=True)
    nx, ny = np.linalg.norm(x, axis=1), np.linalg.norm(y, axis=1)
    if np.any(nx <= 1e-15) or np.any(ny <= 1e-15):
        raise ValueError("Constant pair has undefined correlation")
    cross = np.fft.irfft(np.fft.rfft(x, axis=1) * np.fft.rfft(y, axis=1).conj(), n=x.shape[1], axis=1)
    return np.clip(np.max(np.abs(cross), axis=1) / (nx * ny), 0, 1)


def quality_mask(x, anchor):
    """Frozen train-only engineering sanity gate, not proof of fault fidelity."""
    energy = rms(x)
    reference = float(np.median(rms(anchor)))
    crest = np.max(np.abs(x), axis=1) / energy
    anchor_crest = np.max(np.abs(anchor), axis=1) / rms(anchor)
    finite = np.isfinite(x).all(axis=1)
    return finite & (energy >= .5 * reference) & (energy <= 2 * reference) & (crest <= 2 * np.max(anchor_crest))


def evaluate(x, anchor, real, label, rpm, generated_rpm=1797, anchor_rpm=1797):
    a = features(anchor, label, anchor_rpm)
    g = features(x, label, generated_rpm)
    r = features(real, label, rpm)
    # Fixed anchor scaling used identically for all variants, including test.
    scale = np.maximum(np.std(a, axis=0), .3)
    distances = np.array([stats.wasserstein_distance(g[:, j], r[:, j]) / scale[j]
                          for j in range(g.shape[1])])
    correlations = cyclic_copy_correlations(x, anchor)
    gx = x[:64] - x[:64].mean(axis=1, keepdims=True)
    gx /= np.maximum(np.linalg.norm(gx, axis=1, keepdims=True), 1e-15)
    pairs = np.abs(gx @ gx.T)[np.triu_indices(len(gx), 1)]
    unique = len({hashlib.sha256(row.tobytes()).hexdigest() for row in x}) / len(x)
    return {
        "label": label, "attempted": len(x), "accepted": int(quality_mask(x, anchor).sum()),
        "acceptance_rate": float(quality_mask(x, anchor).mean()),
        "feature_w1": float(distances.mean()),
        "shape_w1": float(distances[:3].mean()),
        "spectrum_w1": float(distances[3:15].mean()),
        "envelope_w1": float(distances[15:].mean()),
        "per_feature_w1": distances.tolist(),
        "cyclic_anchor_corr_median": float(np.median(correlations)),
        "cyclic_anchor_corr_max": float(correlations.max()),
        "anchor_corr_audited_count": len(correlations),
        "cyclic_anchor_corr_p05_p95": np.quantile(correlations, [.05, .95]).tolist(),
        "copy_fraction_corr_gt_099": float(np.mean(correlations > .99)),
        "pair_corr_median": float(np.median(pairs)),
        "unique_waveform_fraction": unique,
        "generated_rms_median": float(np.median(rms(x))),
        "real_rms_median": float(np.median(rms(real))),
        "generated_kurtosis_median": float(np.median(stats.kurtosis(x, axis=1, fisher=False))),
        "real_kurtosis_median": float(np.median(stats.kurtosis(real, axis=1, fisher=False))),
        "finite": bool(np.isfinite(x).all()),
    }


def make_generator(method, anchors, backgrounds, seed, steps, rpms=None):
    if method in Generator.METHODS:
        return Generator(method, anchors, backgrounds, seed, rpms=rpms)
    from deep_generators import DeepGenerator
    return DeepGenerator(method, anchors, seed, steps)


def write_csv(path, rows):
    keys = [k for k in rows[0] if k != "per_feature_w1"]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=keys, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def main():
    import torch
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=256)
    parser.add_argument("--deep-steps", type=int, default=300)
    parser.add_argument("--scale-count", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=ROOT / "results", help="New directory only")
    parser.add_argument("--methods", nargs="+", choices=METHODS,
                        default=tuple(m for m in METHODS if m != "constrained_surrogate"))
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error("Output exists; choose a new directory to preserve prior evidence")
    if args.count < 2 or args.scale_count < 1 or args.deep_steps < 1:
        parser.error("count>=2, scale-count>=1 and deep-steps>=1 required")
    out.mkdir(parents=True)
    anchors, backgrounds, data, metadata = load_split()
    rpms = {label: data[("anchor_train", label)][1] for label in LABELS}
    write_json(out / "preprocessing_manifest.json", metadata)
    write_json(out / "protocol.json", {
        "primary_goal": "many valid, diverse, reproducible raw fault waveforms, not best detector",
        "methods": list(args.methods), "seeds": SEEDS, "count_per_class_seed": args.count,
        "anchor_windows_per_class": 8, "anchor_seconds_per_class": 8 * N / FS,
        "physical_anchor_records_per_class": 1, "healthy_background_windows": len(backgrounds),
        "fs": FS, "window_samples": N, "deep_steps": args.deep_steps,
        "generation_quota_equal": True, "tuning": "single fixed config; not compute-matched",
        "selection": "Development only: finite, acceptance>=0.95 all rows, unique=1, no audited correlation>0.99; then minimize mean feature W1 + 0.25*seed std",
        "limitations": "load split, not independent-bearing test; engineered feature distance is not proof of class fidelity; deep prototypes budget limited",
        "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
        "torch": torch.__version__, "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    })
    dev_rows, fit_logs, instances = [], {}, {}
    for method in args.methods:
        for seed in SEEDS:
            start = time.perf_counter()
            generator = make_generator(method, anchors, backgrounds, seed, args.deep_steps, rpms)
            fit_seconds = time.perf_counter() - start
            instances[(method, seed)] = generator
            fit_logs[f"{method}_{seed}"] = generator.fit_log
            if method not in Generator.METHODS:
                torch.save({"state_dict": generator.model.state_dict(),
                            "method": method, "seed": seed, "scales": generator.scales,
                            "support": generator.support, "fit_log": generator.fit_log},
                           out / f"checkpoint_{method}_{seed}.pt")
            for label in LABELS:
                start = time.perf_counter()
                x, provenance = generator.sample(label, args.count, seed + 1000)
                seconds = time.perf_counter() - start
                real, rpm = data[("development", label)]
                metrics = evaluate(x, anchors[label], real, label, rpm,
                                   generated_rpm=rpms[label], anchor_rpm=rpms[label])
                metrics.update(method=method, seed=seed, fit_seconds=fit_seconds,
                               generation_seconds=seconds, samples_per_second=args.count / seconds)
                dev_rows.append(metrics)
                np.save(out / f"dev_{method}_{seed}_{label}.npy", x)
                write_json(out / f"dev_{method}_{seed}_{label}_provenance.json", provenance)
                repeat, _ = generator.sample(label, 8, seed + 1000)
                # Batch shape affects deep arithmetic; test exact repeat at same quota.
                repeat2, _ = generator.sample(label, 8, seed + 1000)
                metrics["repeat_seed_identical"] = bool(np.array_equal(repeat, repeat2))
                print(method, seed, label, "W1", round(metrics["feature_w1"], 3),
                      "valid", metrics["accepted"], "copy", metrics["copy_fraction_corr_gt_099"], flush=True)
            write_json(out / "development.json", dev_rows)
            write_json(out / "fit_logs.json", fit_logs)
    summary = []
    for method in args.methods:
        rows = [r for r in dev_rows if r["method"] == method]
        per_seed = [np.mean([r["feature_w1"] for r in rows if r["seed"] == s]) for s in SEEDS]
        eligible = all(r["finite"] and r["acceptance_rate"] >= .95 and
                       r["unique_waveform_fraction"] == 1 and r["copy_fraction_corr_gt_099"] == 0 and
                       r["repeat_seed_identical"] for r in rows)
        summary.append({"method": method, "eligible": eligible,
                        "mean_w1": float(np.mean(per_seed)), "seed_std_w1": float(np.std(per_seed)),
                        "score": float(np.mean(per_seed) + .25 * np.std(per_seed)),
                        "min_acceptance": min(r["acceptance_rate"] for r in rows),
                        "mean_samples_per_second": float(np.mean([r["samples_per_second"] for r in rows])),
                        "max_audited_copy_fraction": max(r["copy_fraction_corr_gt_099"] for r in rows)})
    eligible = [row for row in summary if row["eligible"]]
    if not eligible:
        write_json(out / "selection.json", {"summary": summary, "selected": None})
        raise RuntimeError("No method passed frozen feasibility gates; do not claim a stable winner.")
    chosen = min(eligible, key=lambda row: row["score"])["method"]
    write_json(out / "selection.json", {"summary": summary, "selected": chosen,
                                       "test_not_used_for_selection": True})
    write_csv(out / "development.csv", dev_rows)
    test_rows = []
    for seed in SEEDS:
        generator = instances[(chosen, seed)]
        for label in LABELS:
            x, _ = generator.sample(label, args.count, seed + 2000)
            real, rpm = data[("locked_test", label)]
            metrics = evaluate(x, anchors[label], real, label, rpm)
            metrics.update(method=chosen, seed=seed)
            test_rows.append(metrics)
    write_json(out / "locked_test.json", test_rows)
    write_csv(out / "locked_test.csv", test_rows)
    # Scale benchmark is explicit synthetic mass production, not more real evidence.
    generator = instances[(chosen, SEEDS[0])]
    scale_rows = []
    for label in LABELS:
        start = time.perf_counter()
        x, provenance = generator.sample(label, args.scale_count, 9001)
        elapsed = time.perf_counter() - start
        accepted = quality_mask(x, anchors[label])
        np.save(out / f"production_{label}.npy", x)
        write_json(out / f"production_{label}_provenance.json", provenance)
        hashes = [hashlib.sha256(row.tobytes()).hexdigest() for row in x]
        scale_rows.append({"method": chosen, "label": label, "attempted": len(x),
            "accepted": int(accepted.sum()), "rejected": int((~accepted).sum()),
            "seconds": elapsed, "samples_per_second": len(x) / elapsed,
            "bytes": x.nbytes, "unique": len(set(hashes)), "finite": bool(np.isfinite(x).all()),
            "array_sha256": hashlib.sha256(x.tobytes()).hexdigest()})
        np.save(out / f"production_{label}_accepted.npy", accepted)
    write_json(out / "scale.json", scale_rows)
    print("SELECTED", chosen, "SCALE", scale_rows, flush=True)


if __name__ == "__main__":
    main()