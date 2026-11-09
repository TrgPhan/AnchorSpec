# V external checks, frozen before external scores, 04/11/2026

Check all six generators from V without selecting a winner on external labels.
Primary classifier SVM C1, raw45 features, synthetic mass0.5, 64 synthetic windows
per class divided evenly among training recordings. RF50 and SVM C10 are fixed
secondary sensitivity checks, never substituted for primary after seeing scores.
Seeds11,29,47. Equal class/donor mass and total weight equal to real window count.
Classifier configuration and features identical across generators. Report every
method, classifier and unit assumption. Conditional fault diagnosis, causal mean
of five windows within each test recording. No claim of measured detection FPR.

## KAIST

Use the 21 files already downloaded and audited by W. Same18 splits as W:
different source and target loads among0,2,4Nm; hold one fault severity out of all
source training. Inner/outer only. Four training recordings, two test recordings.
Target normal recording provides healthy baseline, not a paired pre-fault record.
This dataset was already evaluated in W, so not untouched confirmation. This is
a new frozen V generator check. Reuse checked native-to-g conversion and sensor
cache from W. Fault signatures and normal data use nominal3010rpm from source
documentation. Retain all files and all splits, including ceiling cases.

## HUST

[Publisher V3](https://data.mendeley.com/datasets/cbv7jyx4p9/3), CC BY4.0.
[Authors' paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC10327369/).
[Extended preprint](https://arxiv.org/pdf/2302.12533v1).
48 files: N/I/O/B for6205,6206,6207,6208 at0,200,400W. Exclude6204 because no
single-ball file. All selected files verified against publisher SHA256. Full
10-second stationary `data` at51200Hz; `fs` field is shaft Hz, NOT sampling rate.
Exclude `ru_raw`. Within each bearing geometry, all six ordered load transfers;
24 transfers in total. One source recording per fault class; target fault
recordings excluded from training and generation. Source/target healthy first6s;
test fault seconds1..10 after discarding initial1s in all sensed signals.
Healthy reference and fault bearing are not confirmed the same physical bearing.
Fault recordings across loads can share the same damaged bearing. This tests
operating-condition transfer, NOT generalization to independent fault specimens.

Apply CheapSensor4kHz/1kHz/8g/20bit. Native values have no explicit unit in MAT.
Run BOTH native-as-g and native-as-m/s2 divided by9.80665; both are assumptions,
not two independent datasets. Report clipping per assumption. No sensor feasibility
claim from HUST until units confirmed. Geometry uses published ball count/diameter
and pitch diameter approximated by average inner/outer bearing diameter. Shaft
speed for target generation/features comes only from its healthy metadata;
source fault metadata used only for training feature and donor speed correction.

No window bootstrap. Summarize paired differences per transfer and by geometry/load;
repeated load transfers and random seeds are correlated, not independent trials.
External superiority requires positive primary gain against real and surrogate
without class degradation greater than5points, consistent across unit assumptions.
An isolated secondary-classifier improvement is reported as such, not overall proof.
