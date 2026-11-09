# Small-data kernel control, exploratory

After the RF adaptive run, no four-class superiority over equally tuned real-only
was established. Keep that result. Add one bounded classifier-family control:
RBF SVM, C in {1, 10}, gamma='scale', representations z/delta/raw and synthetic
mass {0, 0.1, 0.5}. Select exclusively on the same whole-donor-bearing folds and
objective as PROTOCOL_Y_ADAPTIVE. A real-only SVM receives the same C and feature
selection. This does not use target fault labels for fitting or parameter selection.

StandardScaler fits with class/source/event-balanced training weights only.
SVM sample weights have mean one so C is comparable across event budgets.
Decision scores are softmax-normalized only to reuse causal score aggregation;
they are NOT calibrated fault probabilities and must not be shown as confidence.
Single-class training yields that class only. No unknown detection is claimed.

Evaluate balanced budgets and simulated arrival, plus label corruption for the
one-per-class condition. Retain all models, including negative results. This
additional family was motivated after seeing reused-dataset results; even a
positive result needs independent confirmation before claims of superiority.
