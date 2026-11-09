# S3 CPU handoff — 06 November 2026

Latest user request: diagnose weak DL augmentation, improve it, optimize for
CPU only; user said continue while the work was running. Work completed locally,
not committed or pushed. Frozen S, S2 and prior experimental sources unchanged.

## New method and protocol

Read PROTOCOL_S3_CPU_RESIDUAL.md. Spectral residual flow keeps a measured source
waveform as carrier and learns 24 log amplitude band changes. All ordered pairs
of different terminal snapshots of the same source bearing give 1,080 derived
pairs from 120 windows, still only 12 source bearings. Conditions: anchor
spectrum, class, speed, healthy-first-five RMS. MLP 64 by 64, 9,688 parameters,
2,000 steps. Linear CFM and v-prediction diffusion with 16 DDIM steps. CPU only,
one thread per worker, three workers. Bounds come only from source data.

Keep phase, no second 8 g clipping in demeaned coordinates, limit centered peak
by the maximum source-donor peak. This is augmentation of processed signals,
not a validated new raw sensor simulation. Mean anchor correlation about 0.994.
Does not create an unseen mechanical failure or independent fault event.

S3: 78 networks, 312 RF fits, 39 outer tasks. Eight new configurations: flow,
diffusion, empirical residual bootstrap, Gaussian residual with covariance
shrinkage; strengths 0.5 and 1.0. Every arm keeps 125 real rows and weights and
adds 120 synthetic rows at alpha 0.25. Same donor permutations as S. Primary
spectral_flow_half:r1:a0.25, selective. Sources and results frozen by hashes.

## Main results, selective policy

| Method | Preterminal | Terminal | Cage | Healthy fault claim |
|---|---:|---:|---:|---:|
| Real | 58.75 | 68.33 | 11.67 | 0 |
| Duplicate | 68.06 | 72.64 | 31.67 | 0 |
| Old surrogate | 64.17 | 74.26 | 31.67 | 0 |
| Severity | 69.91 | 77.22 | 48.33 | 1.03 |
| Old full-rank flow | 59.68 | 64.81 | 0 | 0 |
| Old full-rank diffusion | 59.86 | 66.30 | 0 | 0 |
| Residual bootstrap half | 60.79 | 65.74 | 15.00 | 0 |
| Residual Gaussian half | 70.88 | 74.21 | 38.33 | 0 |
| Residual flow half | 70.42 | 77.22 | 41.67 | 0 |
| Residual diffusion half | 67.31 | 72.82 | 33.33 | 0 |

Flow primary vs old full-rank flow +12.41 pp, CI [-5.93,30.74]; vs duplicate
+4.58 [-0.60,9.77]; vs surrogate +2.96 [-4.44,10.37]; vs Gaussian +3.01
[-4.03,11.11]. Only two cage bearings. No certain superiority or factory claim.
Changing representation, conditioning, anchoring and output processing together
prevents attributing the result to one isolated mechanism.

S3B uses the SAME checkpoints, no retraining: 4, 8, 32 evaluations for both
methods at strength 0.5, 234 RF fits. Replayed 16-step features before testing
other counts. Flow terminal 75.42, 74.44, 76.85 respectively; diffusion 71.16,
72.08, 74.86. Keep the predeclared 16-step primary, not maximum test selection.
Full-strength flow is 71.11, worse than half strength.

## Failure audit

PCA32 explains 45.66% variance; lossless train PCA did not fix generalization.
Old full-rank diffusion has 13.76% of waveform values outside 8 g before final
clipping. Source-space cage kurtosis: real 0.384, old full diffusion -0.609.
Nearest source-centroid agreement: 95.38% real, 47.95% old full diffusion.
These are descriptive, overlapping training-source checks, NOT independently
verified label fidelity. Do not say generator loss proves correct fault physics.

## CPU optimization and validation

Training averages: flow 1.89 s, diffusion 1.82 s per model in the three-worker
run. Existing S/S2 already ran on CPU, so do not claim GPU-to-CPU migration.
New network has 9,688 parameters vs full-rank predecessor 66,680.

First optimization, s3_fast_cpu.py: sparse interpolation plus grouped feature
extraction preserved all scores but ran slower. Keep cpu_optimized.json as a
negative result; do not recommend its optimized branch.

Second optimization: s3_cached_features.py caches anchor FFT and fixed filter
constants. s3_cached_profile.py verified waveform, features and all RF raw scores
EXACTLY on 78 model folds. Paired local timings (120 windows, one warmup, ten
repeats): flow original total median 449.64 ms, cached 319.04 ms; diffusion
559.08 vs 401.90 ms, roughly 29% reduction. Cache setup is separately measured
42.14 and 24.25 ms. Local load varied considerably: earlier timing runs had
~170 ms totals, and the CLI export had 11.77 ms generation plus 131.87 ms
features. Do not compare unmatched absolute timings as a speedup claim or
promise stable factory latency. Profile is NOT target hardware or Pi evidence.

`python s3_generate_cpu.py --target 1_1 --seed 11 --kind flow` successfully
exported 120 waveform/feature/label/lineage records to data/s3_cpu_export and
verified exact feature equality. It reuses existing local public-data checkpoints.
Data, networks and residual caches remain ignored under data/s3_generation.
This is a research CLI; default production runtime unchanged.

Full pytest: 136 passed in 38.65 seconds after final changes. Earlier 135 passed
before the cached-feature test was added. Workbook row counts and local report
links checked; figure inspected. Source hashes and exact score replays passed.
No background jobs remain.

## Deliverables and next work

- CAI_TIEN_DL_CPU_20261106.md: Vietnamese findings and all sensitivity results.
- results/s3/AnchorSpec_CPU_Benchmark_20261106.xlsx: 25 configurations, two
  policies, 650 bearing rows, diagnostics, successful and failed CPU timings.
- results/s3/spectral.json, steps.json: raw per-fold scores and hashes.
- results/s3/failure_audit.json, cpu_profile.json, cpu_optimized.json,
  cpu_cached.json: detailed audits and raw timings.
- results/s3/comparisons.csv, per_bearing.csv, quality.csv, comparison PNG/SVG.
- PROTOCOL_S3_CPU_RESIDUAL.md, PROTOCOL_S3B_STEPS.md and test_s3_cpu.py.

Next defensible research step: lock the primary and test new independent events
or a separately specified dataset. More outer-test tuning on the same 13 bearings
does not strengthen the superiority claim. Lubrication, contamination, unknown
faults, target sensor conditions and real DENSO operating benefit remain open.
Do not alter frozen experimental code. Use a new protocol and output directory.

## Seven-priority derived benchmark, same day

User requested quantitative benchmarks for the seven factory priorities.
Completed `priority_benchmark.py`, `priority_runtime_worker.py` and
`priority_report.py`. No generator retraining or configuration selection.
Read `BENCHMARK_7_UU_TIEN_20261106.md` and
`results/priorities/AnchorSpec_7_Priorities_20261106.xlsx` (14 sheets).

Primary per-class precision: inner 98.78%, outer 86.02%, cage 100%; recall
90%, 100%, 41.67%. Healthy plus terminal pooled confusion: 195 healthy correct;
inner 81 correct and 9 outer; outer 240 correct; cage 25 correct, 30 outer,
1 inner, 4 healthy. These 585 prediction evaluations represent 195 unique
snapshots repeated across three seeds, still only 13 independent bearings.
Bearing 2_3 has zero correct terminal diagnosis in all ten windows at all
three seeds. This is diagnostic event-proxy failure, not upstream alarm miss.

Regime class-macro recalls: 2100 rpm/12 kN 91.67% (outer and cage only),
2250 rpm/11 kN 56.67% (all three classes, cage 0%), 2400 rpm/10 kN 100%
(inner and outer only). Cannot compare class composition as identical or
claim held-out-regime generalization: training includes other same-regime donors.

Physical metrics vs actual source anchors: PSD cosine .982592, envelope PSD
cosine .989164, normalized log PSD RMSE 1.1142 dB, mean RMS ratio .980048,
mean absolute relative RMS drift 5.9864%, absolute excess-kurtosis error .06749,
waveform correlation .994213. 84.1026% have nearest-source zero-lag correlation
above .99; exact-copy check at 1e-10 found 0%. Peak rescaling 11.453%, residual
coordinate clamp 9.3625%. Source observations overlap heavily across folds;
similarity is not independent proof of fault physics. No second pointwise clip
does not establish absence of saturation already in source measurements.

New isolated diagnostic process (no Torch/generator), fixed fold 1_1 seed11,
one terminal waveform, one warmup and 100 repeats: feature median 6.949 ms,
RF plus history median 2.470 ms, total median 9.5755 ms, total p95 10.6292 ms.
Observed peak process RSS 167657472 bytes (about 159.89 MiB), RF pickle
128576 bytes (125.56 KiB). RSS includes Python and libraries, sampled every5ms;
not a precise model-only peak. Excludes acquisition, transmission and loading.
No DENSO hardware measurement. Exact frozen RF scores replayed.

Unknown S3, inspections per shift, downtime and maintenance costs remain
unmeasured. Historical T unknown stress is explicitly a separate workbook sheet.
Four new metric tests passed in 6.26s; the earlier full 136 tests were not rerun.
Workbook row counts, report links, manifests and git diff whitespace checked.
