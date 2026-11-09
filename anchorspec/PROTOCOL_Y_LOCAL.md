# Y local: event learning and protected fault families

Protocol written before loading the raw UORED files in this continuation. UORED
has already been used in earlier X experiments; this is exploratory development,
not a fresh-dataset confirmation. No factory data are used.

## Fixed comparison

Reuse the published UORED v5 accelerometer recordings and the existing cheap
sensor simulation (4 kHz sampling, 1 kHz bandwidth). Keep the existing healthy
baseline, feature extractor, RF size and physical injection prior unchanged.
Each target bearing is excluded from every donor event, including its early
fault recording. Normalize each bearing using only its own healthy baseline.

Seeds 11, 29, 47. Use one, two and four independently damaged donor bearings per
fault class, with nested donor sets and the same events for all alternatives.
One event contains all windows of one severe recording. Do not describe five
overlapping windows as five independent failures. No target fault labels select
features, weights, thresholds or donor sets.

Compare injection only, real only, the existing equal-source hybrid, and a new
hierarchical candidate, **AnchorSpec-E (Event-guided Physics Experts)**. Its root
classifier learns healthy, ring damage, ball damage and cage damage from real
events and the target healthy baseline. Only the ring specialist receives
synthetic inner/outer faults. The root thus prevents unvalidated synthetic
fault families from directly dominating the ball/cage decision. Root probabilities
are expanded using conditional inner/outer probabilities from the specialist.
This design is a hypothesis, not a guaranteed improvement or novelty claim.

Evaluate every early and severe target recording, with causal five-window
probability averaging, and the held-out healthy segment. Primary metric is
macro recall over four fault classes, averaged per bearing and then per class;
healthy remains an available output. Also report inner/outer recall, each class,
healthy false-positive rate, event majority correctness, paired stratified
bearing bootstrap intervals (5,000 resamples), model bytes and local latency.
Repeated seeds and overlapping windows do not increase the bearing sample size.
No abstention is used to inflate accuracy. No result establishes unknown-fault
detection. The healthy control comes from the same file, not long-term operation.

Practical success screen: four-class gain at least 0.10 over equal-source hybrid,
95% paired CI lower bound above zero; inner/outer loss no worse than 0.05;
healthy false-positive increase no more than 0.02. Report each gate independently.
Comparison to real-only is also mandatory. These are screening thresholds on a
reused dataset; passing them is not permission to claim factory superiority.

## Controls

Y1: cyclically corrupt all donor labels while keeping signals and donor events
identical, for the one-event condition. Measure loss of correct recall and rate
of copying the wrong donor label. This is a stress test, not a claim that label
errors are identifiable without an independent source of evidence.

Y4: permute a shared global stream of donor events, exclude the target bearing,
and train using only previous events at budgets 0, 2, 4, 8, 12. Early streams may
lack entire classes. This is simulated arrival order, not measured chronology.
Freeze all method parameters before examining these curves.

Y2 remains blocked by the lack of independent healthy sessions on the same
bearing. Never substitute healthy recordings from different bearings and call
that a measurement of long-term same-machine false alarms.

The final shortlist requires a new dataset, independent review, real cheap
sensor captures and physical edge-device timing before deployment claims.

## Exploratory extension after the first balanced run

The protected hierarchy failed the ring-retention screen (all three budgets),
although its four-event overall gain over hybrid was positive. Retain that
negative result. Before further evaluation, add three fixed feature controls:
`delta` is the existing feature vector minus its own healthy mean, without
dividing by the noisy within-machine standard deviation; `raw` uses the existing
amplitude-invariant features directly; `both` concatenates raw and delta.
The original `z` remains the baseline. No bandwidth, feature frequencies, RF
size, injection prior or donor labels change. This is a bounded exploratory
search, not a confirmatory test. Shared rotation speed on UORED limits external
validity. The minimum comparison includes real-only under the same representation.
