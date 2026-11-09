# Z: public-data acquisition and new-domain screening

Use official, openly licensed sources instead of waiting for factory data.
This does not turn public data into factory validation.

## DLR oscillating needle bearings, Zenodo 20742913

Acquire tests 4, 6, 7, 8: all are unlubricated, but their load, frequency and
oscillation amplitude differ. Select acceleration at both bearing positions,
angle and temperature using ZIP byte ranges. Verify every extracted member's
CRC and store SHA256. Do not claim the entire ZIP checksum was verified.

This subset cannot train or evaluate a lubricated versus unlubricated classifier:
there is no lubricated run in it. It can exercise monitoring of degradation and
sensor limits on actual unlubricated tests. The two bearing channels are grouped
within a test; they are not two independent test conditions. These are oscillating
needle bearings, so a continuous-rotation BPFO/BPFI injection model is inapplicable.

Before reading feature values, fix the exploratory replay: first 5 snapshots as
reference, next 5 as calibration, all later snapshots held out in time. Compare
RMS with a multifeature baseline-deviation score. Both methods use only vibration.
Evaluate the existing 4 kHz, 1 kHz, 8 g sensor simulation, and retain native data
as a sensor-control analysis. Angle and temperature are descriptive context only,
never hidden classifier inputs. Report clipping, score trajectories and first
three consecutive exceedances of the calibration maximum. Do not report those
exceedances as labelled fault detection accuracy: the exact onset is unknown.
Do not convert final-run proximity into a validated RUL prediction.

## Additional lubrication records

Inspect official records 7589904 and 17530066, their documentation, physical
bearing type, label definitions, grouping and raw-versus-aggregated signals.
Do not train until the admissible split and features are identified. Never mix
tabular sensor summaries with raw waveform injection or claim one validates the
other. Preserve provenance, licenses and any missing event identifiers.

## Contamination

NLN-EMP DOI 10.4121/2b61183e-c14f-4131-829b-cc4822c369d0.v4 is relevant to grease
contamination. The official host timed out in this environment. A discovered
third-party subset excludes contamination and inner/ball defects, so it cannot
serve as their validation. Record this gap instead of relabelling another fault.

## Fixed pilot for record 7589904, after reading the official schema only

The labels are recommended grease with seal, no grease without seal, and excess
grease without seal. Seal status is therefore confounded with lubrication. There
are no published machine, event or timestamp columns in the CSV. This is a pilot
on observed operating states, not independent bearing or pure-lubrication proof.

Before calculating feature distributions or test scores: within each label, use
the first 60% of rows for training, leave the middle 20% unused as a gap, and the
last 20% for testing. This is row-order blocking, not a verified chronological
split. No random row shuffle. Fixed RF50 with existing SMALL settings, seed 11;
compare four vibration summary metrics with those metrics plus temperature and
with a majority dummy. Do not tune on this test. Report macro recall, class recall,
confusion matrices, exact cross-split feature duplicate count and missingness.
No raw-waveform reconstruction or 4 kHz sensor simulation is possible here.
