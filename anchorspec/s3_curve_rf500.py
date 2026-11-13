"""Post-hoc (12/11): the S3 data-efficiency curve (real vs real + Flow, k real windows per bearing) rerun with RF 500 trees.
Everything else is s3_curve.py unchanged. Output: results/s3_curve_rf500/."""
import sys
from sklearn.ensemble import RandomForestClassifier as _RFC
import invariant_classifier as IC
IC.RandomForestClassifier = lambda **kw: _RFC(**{**kw, 'n_estimators': 500})
import s3_curve as C
C.OUT = C.ROOT / 'results/s3_curve_rf500'
if __name__ == '__main__':
    C.main()
