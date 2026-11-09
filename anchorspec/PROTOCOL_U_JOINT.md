# U2: joint phase surrogate and sensor-range sensitivity, 05/11/2026

Written after U natural single-axis scores. This is exploratory development on
the same13XJTU bearings, NOT a fresh confirmation. U primary transport gained
4.21pp with SVM C1 but cage recall remained0; RF transport declined. Independently,
the native-signal audit found up to35.57% terminal samples outside8g on a bearing.
These observations motivate using both measured axes and testing assumed range.

## Joint envelope-preserving surrogate (JEPS, working name)

Draw a real paired terminal snapshot and one global positive-frequency phase
angle. Apply that SAME angle to both axes; each analytic envelope and Fourier
magnitude is preserved before output conditioning except unrotated DC/Nyquist.
The complete cross-spectrum is also preserved. Independent per-axis angles are
a separate ablation; they preserve marginal envelopes but alter cross phase.
This is an existing analytic-signal operation extended coherently across axes,
not a claim of inventing the Hilbert transform or a proven physical digital twin.
Only actual donor fault labels.64generated pairs per donor, equal quota perclass.

Output uses the declared sensor range and20bit quantization. If ANY value of the
proposed demeaned phase-rotated pair exceeds the declared range, use the original
measured pair instead. This identity fallback is label-free and audited; no
test-guided rejection or nearest-label selection. Source digital pairs must be
finite and within their declared range. A fallback is not a new independent sample.
Legacy constrained surrogate runs separately peraxis and preserves peraxis
histograms but not cross phase. Compare real, duplicate, legacy, independent_phase,
joint_phase. Fixed synthetic weight0.25; no model or mass tuning.

## Representation and sensor experiment

Features96: same45features on each of2axes plus existing six cross-axis features
from tn2b_xjtu.cross_features (logRMSratio, correlation, coherence in3bands, peak
coincidence). All methods and controls use the same features. Primary classifier
duplicate-invariant RF (it was the stronger model on single-axis natural data);
secondary SVM C1,C10. Do not attribute the gain from the second axis or changing
classifier to generation. Within each group compare only matched real-only.

Repeat exactly the13heldout-bearing splits, three seeds and both temporal stages
from U. Source windows retain their speed, features use their known shaft speed.
No test fault in any generated example. One paired digital snapshot per raw file,
seconds0.14..1.14 after sensor processing. Noise streams deterministic perfile.

Primary sensor range8g; additional16g and64g sensitivity. Same4kHz,1kHzbandwidth,
20bits and assumed noise density25ug/sqrtHz. These are hypothetical specifications,
NOT named hardware or proven low-cost devices. Evaluate all ranges, not only the
one producing the best score. A later range experiment is not evidence that the
original8g pipeline works.39tasks perrange,117total, repeated seeds not trials.

## Criteria

Primary JEPS must improve terminal RF macro at8g by5pp versus real and legacy,
no class loss over5pp, positive exploratory bootstrap CI vsreal, no preterminal
loss over2pp. Both mixed-fault specimens remain excluded. Cage has only2bearings;
report each and do not overstate bootstrap certainty. Also report classwise
effects and accepted/fallback fractions. Real/duplicate predictions exactly equal.
All outcomes retained. Any positive secondary-range or secondary-classifier result
is a scoped finding requiring further verification, not a primary success.
