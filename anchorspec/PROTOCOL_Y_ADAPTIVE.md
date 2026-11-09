# Event-level adaptive physics: exploratory follow-up

The fixed hierarchy did not retain inner/outer performance. Changing the feature
representation alone did not solve the four-class problem. Preserve all results.
Next test a bounded, nested selection procedure instead of selecting the best
configuration using target fault labels.

For each target bearing and each event budget, compare nine candidates using ONLY
the selected donor events: representations z, delta and raw; synthetic source
mass 0, 0.1 and 0.5 within each class having both real and synthetic data.
Synthetic-only supported classes retain mass 1; unsupported ball and cage classes
receive real data only. Every class and every independent event have equal mass.

Inner validation holds out whole donor bearings, in up to four folds, stratified
by fault class. All recordings of a bearing leave the training event set together.
The objective averages per-class fault recall and held-donor healthy accuracy,
with causal five-window smoothing for fault records. Healthy calibration windows
belong to donors, not the target. Never inspect target fault or target healthy
test windows during selection. Ties prefer lower synthetic mass, then z, delta,
raw. With only one donor per class validation has no remaining real events in
that class; explicitly report this limited evidence. No validation means default
z representation and mass 0.5.

Refit the chosen configuration on all selected donor events, then evaluate the
untouched target. Compare against the old z hybrid and against a real-only model
whose representation is chosen by the SAME donor-level validation procedure.
That latter baseline is essential: a gain caused only by feature selection must
not be presented as proof that synthetic faults add value.

Reuse the 20-bearing UORED split, three seeds and nested event sets defined in
PROTOCOL_Y_LOCAL.md. Primary evaluation is all four fault classes, with early,
severe, healthy, per-class, paired bearing CI, label corruption and simulated
arrival order reported separately. This remains exploratory after several method
comparisons on UORED. A positive paired interval is NOT corrected for that search.
Freeze this algorithm before executing its target evaluations.
