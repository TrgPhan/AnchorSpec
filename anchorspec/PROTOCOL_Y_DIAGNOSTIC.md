# Diagnosis after an existing anomaly detector

This is a separate task definition, motivated by the intended interface, not a
replacement for the end-to-end results. For a known abnormal input, select among
fault hypotheses; retain healthy in training, but do not let it win the fault
type decision. An absent fault library gives an unsupported answer (-1).

Select configuration on whole donor-bearing folds using macro fault-type recall
conditioned on the record being faulty. Candidate set is fixed: RF50 or RBF SVM
with C 1/10; z/delta/raw representation; synthetic mass 0/0.1/0.5. The real-only
control has the identical classifier and representation candidates. No healthy
test windows are needed for this conditional selection. Target fault labels
remain entirely outside fitting and selection.

Reuse the exact saved donor sets and evaluate all four classes, all budgets and
all seeds. Explicitly report that the upstream gate is assumed correct for this
benchmark. Its misses, false alarms and unknown faults are NOT solved by a high
conditional diagnosis score. Compare also to the original hybrid under the SAME
fault-only decision rule; never compare conditional new scores with the old
healthy-included metric and call that a method improvement.

This is exploratory on reused UORED. It requires real upstream detector outputs
and independent data to measure an actual integrated pipeline. Do not claim that
this experiment establishes general superiority or recognizes lubrication and
contamination faults that are absent from the data.
