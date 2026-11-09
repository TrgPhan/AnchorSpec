# S3: CPU spectral residual augmentation

Frozen before evaluating S3 outcomes, 06 November 2026. Exploratory follow-up
on the already inspected XJTU cohort, not an independent confirmation.

Hypotheses: raw waveform PCA spends capacity on arbitrary phase; only 120
fault windows from 12 donors are available; full-rank reconstruction does not
solve conditional generation; repeating sensor clipping in demeaned coordinates
confounds reconstruction. S3 changes representation and anchoring together;
it cannot identify a single causal reason for any improvement.

Keep frozen S and S2, the RF, real training weights and held-out folds unchanged.
13 target bearings, seeds 11, 29, 47. Each target contributes only its first
five assumed-healthy windows to classifier training. No target waveform,
feature or label is supplied to generator fitting, bounds or conditions.

Use a measured source waveform as anchor. Represent changes as 24 log amplitude
gains in equal frequency bands from 0 to 1 kHz. Train on ordered pairs of
different terminal windows of the SAME source bearing, never across fault
classes or bearings. 1,080 pairs are derived observations, not independent events.
Condition on anchor spectrum, source fault class, source speed and first-five
healthy RMS. Standardizers and gain bounds use source training data only.

Learn standardized spectral residuals using two-hidden-layer width-64 MLPs,
2,000 Adam updates, batch 64, CPU one thread. Compare linear conditional flow
matching with velocity-prediction diffusion (100 cosine training steps), using
16 Euler evaluations or 16 deterministic DDIM evaluations for generation.
The diffusion model uses v parameterization; it is not a reproduction of a
specific fault diagnosis paper. No test-driven early stopping or hyperparameter
selection. Primary is spectral_flow_half, ratio 1, alpha 0.25, selective policy.

Clip residuals to source-pair per-band 2nd/98th percentiles, additionally bounded
by plus or minus log(2). Interpolate gains over FFT bins and apply to the anchor
complex spectrum, retaining its phase. Frequencies above 1 kHz are unchanged.
Use strengths 0.5 (primary) and 1.0 (sensitivity), fixed before results. Rescale
uniformly only if peak exceeds the maximum demeaned peak of that donor's ten
training windows. Do NOT clip again at 8 g or requantize: these are augmentations
of already sensed, demeaned windows, not a simulation of new raw sensor readings.
Zero residual is an identity operation, including anchors whose centered peaks
exceed 8 g. This does not certify real sensor admissibility.

Non-neural controls: empirical bootstrap residual from the same donor and a
full-covariance Gaussian residual from the same donor with 20% diagonal shrinkage.
Both use exactly the same anchoring, bounds and strengths. Include exact duplicate,
surrogate, envelope, severity, real, old PCA/flow/diffusion controls from S/S2.
Reuse S's anchor permutations so each donor contributes every source window once.
Every new arm adds 120 rows to the unchanged 125 real rows, alpha 0.25.

Report all eight new configurations, both decision policies, preterminal and
terminal class-macro recall, class recalls, healthy fault claims and paired
bearing-bootstrap intervals (5,000 resamples). Add comparisons to both residual
non-neural controls, not only the weak old DL prototypes. Do not promote a winner
by selecting the maximum outer-test score. Two cage bearings remain insufficient.

Audit old generation in training-feature space by fault class (descriptive only,
not an independent label-validity test). Record clipping, RMS/kurtosis, feature
distance, anchor correlation, source lineage, raw scores, model checkpoints,
timing and hashes. CPU profile separately measures generation and feature
extraction on fixed fold 1_1 seed 11; excludes loading and classifier inference.
Sampling-step ablation uses the same trained network and random seed, and reports
output drift as well as time, not an assumed cost-free acceleration.

References consulted:

- [Flow Matching](https://arxiv.org/abs/2210.02747)
- [DDIM](https://arxiv.org/abs/2010.02502)
- [Frequency-domain time-series diffusion](https://arxiv.org/abs/2402.05933)

Frequency-domain motivation is an inference for this task. The cited experiments
do not establish performance on XJTU or DENSO. S3 is an anchored augmentation
method and cannot create evidence for a fault absent from all source bearings.
