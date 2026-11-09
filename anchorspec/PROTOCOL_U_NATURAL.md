# U: natural-fault verification and duplicate-invariant learning, 05/11/2026

Written before reading XJTU fault waveforms or scores in this continuation.
This is a new generator evaluation on a dataset used by older project work,
not a claim that the dataset has never been seen in this project.

## Data and provenance

[Authors' source](https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets).
Paper DOI10.1109/TR.2018.2882682. Download a subset from the ZIP mirror used by
[rul-datasets](https://github.com/tilman151/rul-datasets/blob/master/rul_datasets/reader/xjtu_sy.py),
https://kr0k0tsch.de/rul-datasets/XJTU-SY.zip. Archive size5448862369bytes.
Check member CRC and size, record local SHA256; publisher archive SHA not available
and not verified. Included author introduction matches named bearings, counts,
sampling and geometry. Do not describe mirror CRC as publisher SHA verification.

Use13 single-fault bearings: inner2_1,3_3,3_4; cage1_4,2_3; outer1_1,1_2,1_3,
2_2,2_4,2_5,3_1,3_5. Exclude mixed teardown1_5,3_2 in advance. Geometry8 balls,
ball7.92mm, pitch34.55mm, angle0. Speeds35,37.5,40Hz by operating condition.
Two vibration axes at25600Hz, g units inferred from author introduction Fig4.
Each snapshot1.28s, separated by1min. Download first10 and last20 snapshots per
bearing. First10 are an assumed healthy reference; no per-snapshot inspection
label confirms health. Last10 are primary terminal-fault windows labeled by
teardown; previous10 are secondary pre-terminal windows, NOT confirmed early
fault onset. No RUL or lead-time claim. All windows remain grouped by bearing.

Primary horizontal axis, CheapSensor4kHz,1kHzBW,8g,20bit. Discard first140ms and
retain1s. Record native fraction at8g per file and stage. No test filtering by
clipping or correct prediction. No majority across overlapping windows; snapshots
are disjoint, causal average over5 chronological snapshots means5minutes, not5s.

## Methods and locked classifier

Primary classifier duplicate-invariant SVM C1 with weighted StandardScaler and
fixed gamma1/45. Secondary C10 and RF50, depth8, weighted leaf minimum0.01,
min_samples_leaf1, no bootstrap. Collapse exactly identical (features,label) rows
and sum weights before fitting; zero-weight rows ignored. Canonical rounding of
normalized weights to14decimals removes summation-order floating noise. Total
weight equals true training-window count and never grows with augmentation.
RF uses weighted regularization instead of raw duplicate row count.

Primary generator measured transport WITHOUT mixing (best consistent direction
in HUST development but failed6204); test directly without further tuning.
Controls real-only, exact duplicate, legacy constrained surrogate, envelope
surrogate. Additional severity-only and transport_mix retained. Fixed mass0.25,
64 generated examples per fault class divided equally among donor bearings.
No outer-label choice of mass, classifier or feature representation. Raw45
features for every method; primary horizontal channel only. Preserve old frozen
V code. New model has separate source and tests for exact duplication invariance.

For each target use every OTHER single-fault bearing as donor. Training class
balance and equal donor mass within class; healthy class0 comes from target
initial reference. All donor terminal10 snapshots used; every generator derives
only from training donors and target healthy. No target fault in fit/generation.
Three generation seeds11,29,47. 13bearing tasks per seed,39total. Additional
classifier scores are sensitivity, not candidates to pick on test outcomes.
Classifier and generator source hashes frozen before run. The counts per class
are unequal; report macro per class after averaging seeds per bearing.

## Reporting and decisions

Conditional diagnosis assuming a correct upstream abnormal flag. Report terminal
and pre-terminal separately, per-class recall, paired bearing-level differences,
duplicate-control equality and clipping. Bootstrap5000 stratified by3classes,
but only2cage bearings and overlapping training sets: exploratory uncertainty,
not independent confirmatory inference. No windows/seeds as independent trials.
Success for this experiment requires primary transport terminal macro gain at
least5points over real AND legacy surrogate, no class loss over5points versus
real, and positive exploratory CI versus real. Pre-terminal cannot lose over
2points. Real/duplicate predictions must match exactly for all classifiers.
Never tune on these scores and still describe the run as frozen verification.

Separately re-evaluate cached UORED V and KAIST/HUST generators under the new
duplicate-invariant classifier if needed; these are retrospective audit, not
new independent evidence. Do not compare changed-classifier scores to old scores
as if the entire gain came from generation.
