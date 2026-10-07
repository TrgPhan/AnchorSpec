# A2 — generation-first executable experiment

> **MVP update 07/10/2026:** the end-to-end weekly pipeline, downstream evaluation,
> audited sharded export and offline report are documented in
> `C:\Users\Ad\Downloads\DENSO\generator_benchmark\MVP_README.md`.
> The commands below describe the historical generator-only experiments.

Workspace: `C:\Users\Ad\Downloads\DENSO\generator_benchmark`.

Goal: many reproducible **fault waveform variations**, not selecting the best detector. NumPy/SciPy production path; PyTorch only for small GAN/DDPM comparators. Tested environment torch `2.7.1+cu118`; requirements do not force a CUDA index/build. Do not overwrite your environment merely to run old paper repositories.

## Commands (PowerShell, absolute paths)

```powershell
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\download_data.py'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\test_generators.py'
$env:CUBLAS_WORKSPACE_CONFIG=':4096:8'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\benchmark.py'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\finalize_generation.py'
python 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\generate.py' --label inner --count 1000 --seed 901 --output 'C:\Users\Ad\Downloads\DENSO\generator_benchmark\new_run'
```

Results from the original experiments remain in `results` (V1) and `results_v2` (V2). Revised benchmark/finalizer now **refuse existing output directories**; use `--output` with a new absolute path. Never overwrite prior evidence. Read `C:\Users\Ad\Downloads\DENSO\docs\reviews\REVIEW_IMPLEMENTATION_A2.md` for the reviewed results and implementation limits.

For authorized DENSO inputs use `--anchors 'C:\absolute\path\anchors.npy' --fs 12000`, shape `(>=2,2048)`. This asserts the label declared by the user, not automatic fault verification. Only known inner/outer/ball mechanisms and the tested sample rate are supported. Obtain metadata/units/sensor/permissions first; do not silently assign CWRU geometry or sample rate to other machinery.

## Selected generator

Phase-regularized IAAFT variant: randomize Fourier phase locally (±0.65 radians), alternate spectral and amplitude-rank projections 30 times. **The bound applies to intermediate spectral projections, NOT final output phases.** Final value histogram equals the source anchor histogram; spectrum is approximate, not exact. Final phase/spectrum residuals are exported per sample. This is **constrained augmentation**, not learning all possible faults. Preserve provenance and synthetic labels.

Train-only gate checks finite values, RMS/crest range and envelope fault-harmonic energy within anchor range expanded by factor four. `produce` has a finite retry budget (4× quota), rejects **all** candidates with maximum absolute cyclic anchor correlation >0.99, checks exact duplicates, and throws on failure instead of silently exporting copied/fallback samples. Correlation audit now includes every row, not the first 24. Quality gate is an engineering sanity screen, not a guarantee of physical fault correctness. Seed identity is tested in the same environment; cross-version bitwise identity is not promised. The gate uses fixed CWRU SKF6205 orders at nominal RPM; external anchors do not establish geometry/condition validity.

## Protocol caveats

- Official source: CWRU bearing data center; single-point EDM faults, 0.007 inch. Download URLs and SHA-256 in `data_manifest.json`. No redistribution/commercial license confirmed.
- 0HP anchors, 1HP development, 2HP heldout-load. These are **not confirmed independent physical bearings**. Eight non-overlap anchor windows = ~1.365 s of one fault recording/class; NOT eight independent fault shots.
- Explicit `X099_DE_time` extraction matters: `99.mat` also embeds `X098` data. Code refuses hash mismatch and avoids selecting the wrong embedded channel.
- Normal 48kHz downsample to 12kHz is documented as a working assumption, with low-frequency sanity audit; official normal table omits per-file fs. Background not used by final surrogate path.
- V2 follows development discovery that unrestricted IAAFT weakens fault envelope. V1 automated test was already evaluated; V2 heldout results remain exploratory, not a fresh confirmatory test. Final direction chosen using development only.
- Original GAN/DDPM results used 300 steps. Review additionally runs 1500 steps/seed, repairs the DDPM terminal-noise mismatch and uses a residual multiscale 1D U-Net with train-only amplitude support clipping. They are **not TimeGAN, not the Thompson model, not reproductions**, and cannot invalidate entire literature families. Quotas are matched, compute and tuning budgets are not; no convergence claim.
- `physics_calibrated` adds train-only band-kurtosis search, envelope peaks/decay/jitter/amplitude estimates, diagnostic fallbacks, RPM-dependent timing, and train-feature refinement. It is NOT fast kurtogram, a full aligned-transient estimator, 3D contact dynamics or a validated uncertainty posterior. `physics_unanchored` means parameters uncalibrated: even that baseline uses anchor RMS. All physics paths export background and amplitude-anchor provenance.
- Feature W1 uses frozen anchor scaling and same diagnostics for every method; engineered diagnostic distance can be gamed and is not class-label proof.
- Windows exported separately, no claim they concatenate into physically continuous records. Increasing count increases Monte Carlo variations, NOT independent physical evidence. Exact amplitudes/near-anchor correlations reveal a limited support region.

Production should not claim new fault classes, severity extrapolation, RUL or DENSO deployment efficacy based on this public-load experiment.
