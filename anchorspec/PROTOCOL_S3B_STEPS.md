# S3B: CPU sampling-step sensitivity

Defined after seeing S3 primary results. No retraining and no independent
confirmation claim. Keep S3's 16-step primary unchanged. Evaluate 4, 8 and 32
network evaluations for both existing residual models, strength 0.5 only,
on all 13 bearings and three seeds. Same sample seed, source anchors, 125 real
rows, 120 synthetic rows, alpha 0.25, RF and held-out scoring. Report every
configuration, both policies and paired deltas against 16 steps. Do not choose
the highest outer-test score as a new validated operating point. Eight steps
is a CPU candidate requiring independent validation if results are acceptable.

Replay 16-step decoded features from each saved checkpoint and compare with
the features originally used by S3 before evaluating any new step count.
Freeze scripts, S3 evidence, source checkpoints, codecs and residual indices.
No new independent specimens are introduced. Local timing excludes loading,
training and classifier inference; report feature extraction separately.
