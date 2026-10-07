"""Development revision: add bounded-phase surrogate after unconstrained failure.

This is exploratory V2, not a preregistered confirmatory independent-bearing test.
Reuse V1 development results; never rank by test results. Gate waveform fidelity
using anchors only, then measure selected candidate on heldout-load data.
"""
from pathlib import Path
import argparse
import json
import time
import hashlib
import numpy as np
from generators import Generator, LABELS, features
from benchmark import (load_split, evaluate, quality_mask, cyclic_copy_correlations,
                       write_json, write_csv, SEEDS)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results_v2"


def fidelity_mask(x, anchor, label):
    mask = quality_mask(x, anchor)
    # Do not send invalid candidates to Hilbert/Welch or let NaNs propagate.
    g = features(x[mask], label) if mask.any() else np.empty((0, 18))
    a = features(anchor, label)
    low = a[:, 15:].min(0) - np.log(4)
    high = a[:, 15:].max(0) + np.log(4)
    mask[mask] = ((g[:, 15:] >= low) & (g[:, 15:] <= high)).all(1)
    return mask


def produce(generator, anchors, label, quota, seed, max_multiplier=4):
    """Bounded retries; failure explicit, no hidden fallback to copied anchors."""
    if quota < 1 or max_multiplier < 1:
        raise ValueError("Positive quota and retry multiplier required")
    accepted, metadata, attempted, rejects, copy_rejects = [], [], 0, 0, 0
    t0 = time.perf_counter()
    while sum(len(a) for a in accepted) < quota and attempted < quota * max_multiplier:
        remaining = quota - sum(len(a) for a in accepted)
        n = min(256, remaining, quota * max_multiplier - attempted)
        x, provenance = generator.sample(label, n, seed + attempted)
        mask = fidelity_mask(x, anchors[label], label)
        correlations = np.zeros(n)
        if mask.any():
            correlations[mask] = cyclic_copy_correlations(x[mask], anchors[label])
        copies = mask & (correlations > .99)
        copy_rejects += int(copies.sum())
        mask &= ~copies
        attempted += n
        rejects += int((~mask).sum())
        accepted.append(x[mask])
        metadata.extend([dict(p, batch_seed=seed + attempted - n) for p, ok in zip(provenance, mask) if ok])
    waves = np.concatenate(accepted)
    if len(waves) != quota:
        raise RuntimeError(f"Quota not met: {label}: {len(waves)}/{quota}, attempted {attempted}")
    hashes = [hashlib.sha256(x.tobytes()).hexdigest() for x in waves]
    if len(set(hashes)) != quota:
        raise RuntimeError("Duplicate waveform detected; do not export silently")
    for i, p in enumerate(metadata):
        p.update(global_sample_index=i, waveform_sha256=hashes[i], label_status="synthetic_anchor_variation")
    audit = {"label": label, "quota": quota, "attempted": attempted, "accepted": quota,
             "rejected": rejects, "seconds": time.perf_counter() - t0,
             "finite": bool(np.isfinite(waves).all()), "unique": len(set(hashes)),
              "copy_rejected": copy_rejects, "anchor_corr_audited_count": len(waves),
              "max_cyclic_anchor_corr": float(cyclic_copy_correlations(waves, anchors[label]).max()),
             "array_sha256": hashlib.sha256(waves.tobytes()).hexdigest()}
    audit["accepted_per_second"] = quota / audit["seconds"]
    return waves, metadata, audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--previous-results", type=Path, default=ROOT / "results")
    parser.add_argument("--quota", type=int, default=10000)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or args.quota < 1:
        parser.error("New output directory and positive quota required")
    out.mkdir(parents=True)
    # Keep OUT local to the run instead of overwriting the original V2 evidence.
    run_finalization(out, args.previous_results.resolve(), args.quota)


def run_finalization(OUT, previous_results, quota):
    anchors, bg, data, metadata = load_split()
    old = json.loads((previous_results / "development.json").read_text(encoding="utf-8"))
    protocol = {"version": "exploratory_v2", "reason": "unbounded IAAFT weakens fault envelope; bounded-phase revision based ONLY on development and anchors",
        "new_method": "constrained_surrogate", "phase_bound": .65, "iterations": 30,
        "new_gate": "Anchor-only envelope harmonic energy within observed min/max expanded factor 4; >=95% across each label/seed",
        "prior_test": "V1 IAAFT test arrays already evaluated automatically; V2 heldout-load results are exploratory, not fresh confirmatory evidence",
        "fidelity_limit": "Preserves known-fault marginal distribution and approximate spectrum; high correlation ~0.94 expected; NOT independent physical failures or novel mechanisms",
        "production_quota": quota, "max_attempt_multiplier": 4, "training_records_per_fault": 1,
        "review_revision": "full copy audit and rejection; all old-array metrics recomputed",
        "seeds": SEEDS, "ranking": "same development feature W1 + 0.25 seed std; no test used"}
    write_json(OUT / "protocol.json", protocol)
    rows = []
    for row in old:
        if row["method"] == "constrained_surrogate":
            continue
        x = np.load(previous_results / f"dev_{row['method']}_{row['seed']}_{row['label']}.npy")
        real, rpm = data[("development", row["label"])]
        row.update(evaluate(x, anchors[row["label"]], real, row["label"], rpm))
        row["fidelity_acceptance"] = float(fidelity_mask(x, anchors[row["label"]], row["label"]).mean())
        rows.append(row)
    for seed in SEEDS:
        g = Generator("constrained_surrogate", anchors, bg, seed)
        for label in LABELS:
            t0 = time.perf_counter()
            x, provenance = g.sample(label, 256, seed + 1000)
            elapsed = time.perf_counter() - t0
            real, rpm = data[("development", label)]
            row = evaluate(x, anchors[label], real, label, rpm)
            row.update(method="constrained_surrogate", seed=seed, fit_seconds=0,
                generation_seconds=elapsed, samples_per_second=256/elapsed,
                fidelity_acceptance=float(fidelity_mask(x, anchors[label], label).mean()))
            a, _ = g.sample(label, 8, 99); b, _ = g.sample(label, 8, 99)
            row["repeat_seed_identical"] = bool(np.array_equal(a, b))
            rows.append(row)
            np.save(OUT / f"dev_constrained_surrogate_{seed}_{label}.npy", x)
            write_json(OUT / f"dev_constrained_surrogate_{seed}_{label}_provenance.json", provenance)
    summary = []
    for method in sorted({r["method"] for r in rows}):
        values = [r for r in rows if r["method"] == method]
        seed_w1 = [np.mean([r["feature_w1"] for r in values if r["seed"] == seed]) for seed in SEEDS]
        eligible = all(r["acceptance_rate"] >= .95 and r["fidelity_acceptance"] >= .95 and
                       r["copy_fraction_corr_gt_099"] == 0 and r["unique_waveform_fraction"] == 1 and
                       r["repeat_seed_identical"] and r["finite"] for r in values)
        summary.append({"method": method, "eligible": eligible,
            "mean_w1": float(np.mean(seed_w1)), "seed_std_w1": float(np.std(seed_w1)),
            "score": float(np.mean(seed_w1)+.25*np.std(seed_w1)),
            "min_sanity_acceptance": min(r["acceptance_rate"] for r in values),
            "min_fidelity_acceptance": min(r["fidelity_acceptance"] for r in values),
            "max_copy_fraction": max(r["copy_fraction_corr_gt_099"] for r in values),
            "mean_generation_per_second": float(np.mean([r["samples_per_second"] for r in values])),
            "total_fit_seconds_3_seeds": sum(next(r["fit_seconds"] for r in values if r["seed"]==s) for s in SEEDS)})
    eligible = [s for s in summary if s["eligible"]]
    chosen = min(eligible, key=lambda s: s["score"])["method"] if eligible else None
    write_json(OUT / "development.json", rows)
    write_csv(OUT / "development.csv", rows)
    write_json(OUT / "selection.json", {"selected": chosen, "summary": summary})
    if chosen is None:
        raise RuntimeError("No stable fidelity-preserving generator passed V2 gates")
    if chosen != "constrained_surrogate":
        raise RuntimeError(f"Review unexpected selection before deployment: {chosen}")
    print("V2 SELECTED", chosen, flush=True)
    tests = []
    for seed in SEEDS:
        g = Generator(chosen, anchors, bg, seed)
        for label in LABELS:
            x, _ = g.sample(label, 256, seed + 2000)
            real, rpm = data[("locked_test", label)]
            row = evaluate(x, anchors[label], real, label, rpm)
            row.update(method=chosen, seed=seed,
                fidelity_acceptance=float(fidelity_mask(x, anchors[label], label).mean()))
            tests.append(row)
    write_json(OUT / "heldout_load_exploratory.json", tests)
    write_csv(OUT / "heldout_load_exploratory.csv", tests)
    audits = []
    g = Generator(chosen, anchors, bg, 11)
    for label in LABELS:
        x, provenance, audit = produce(g, anchors, label, quota, 9001)
        np.save(OUT / f"production_{label}.npy", x)
        write_json(OUT / f"production_{label}_provenance.json", provenance)
        audits.append(audit)
        write_json(OUT / "scale.json", audits)
        print("PRODUCTION", audit, flush=True)
    # Additional independent generation seeds, fixed selected configuration.
    stress = []
    for seed in (101, 202, 303, 404, 505):
        for label in LABELS:
            x, _, audit = produce(g, anchors, label, 64, seed)
            again, _, _ = produce(g, anchors, label, 64, seed)
            audit.update(seed=seed, repeat_identical=bool(np.array_equal(x, again)))
            stress.append(audit)
    write_json(OUT / "stress.json", stress)
    print("COMPLETE: production and 5-seed stress", flush=True)


if __name__ == "__main__":
    main()