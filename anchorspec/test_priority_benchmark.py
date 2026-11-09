"""Independent checks of derived diagnostics, denominators and signal fidelity."""
import json
import numpy as np
import pytest
from sklearn.metrics import precision_recall_fscore_support
from priority_benchmark import OUT,PRIMARY,LABELS,class_metrics,signal_metrics


def test_confusion_metrics_agree_with_sklearn_and_undefined_is_not_perfect():
    truth=np.array([0,0,1,1,2,2,4,4]);pred=np.array([0,1,1,2,2,2,0,2]);m=np.zeros((6,6),int)
    for a,b in zip(truth,pred):m[LABELS.index(a),LABELS.index(b)]+=1
    precision,recall,f1,support=precision_recall_fscore_support(truth,pred,labels=[0,1,2,4],zero_division=0)
    for i,label in enumerate((0,1,2,4)):
        r=class_metrics(m,label)
        assert (r['precision'] or 0)==pytest.approx(precision[i]);assert r['recall']==pytest.approx(recall[i])
        assert r['f1']==pytest.approx(f1[i]);assert r['support_evaluations']==support[i]
    assert class_metrics(m,4)['precision'] is None


def test_physical_identity_and_amplitude_change_are_distinguished():
    x=np.random.default_rng(5).normal(size=(4,4000));same=signal_metrics(x,x)
    for name in ('psd_cosine','envelope_psd_cosine','anchor_correlation','rms_ratio'):np.testing.assert_allclose(same[name],1,atol=1e-12)
    for name in ('rms_absolute_relative_error','normalized_log_psd_rmse_db','excess_kurtosis_absolute_error'):np.testing.assert_allclose(same[name],0,atol=1e-12)
    scaled=signal_metrics(x,2*x);np.testing.assert_allclose(scaled['rms_absolute_relative_error'],1,atol=1e-12)
    np.testing.assert_allclose(scaled['psd_cosine'],1,atol=1e-12)


def test_frozen_predictions_support_class_counts_and_bearing_misses():
    if not (OUT/'diagnostics.json').exists():pytest.skip('Metrics not generated')
    d=json.loads((OUT/'diagnostics.json').read_text())
    for method in {r['method'] for r in d['totals']}:
        rows=[r for r in d['per_class'] if r['method']==method and r['stage']=='healthy_terminal']
        assert sum(r['support_evaluations'] for r in rows)==585
        faults=[r for r in rows if r['label']!=0];expected=np.mean([r['recall'] for r in faults])
        existing=next(r['macro_recall'] for r in d['totals'] if r['method']==method and r['stage']=='terminal')
        assert expected==pytest.approx(existing)
        for r in rows:assert r['tp']+r['fn']==r['support_evaluations'] and r['tp']+r['fp']==r['predicted_evaluations']
    missed=[r['target'] for r in d['per_bearing'] if r['method']==PRIMARY and r['stage']=='terminal' and r['missed_all_three_seeds']]
    assert missed==['2_3']
    r=next(r for r in d['regimes'] if r['method']==PRIMARY and r['stage']=='terminal' and r['condition']=='3')
    assert r['cage_recall'] is None


def test_isolated_diagnostic_process_replays_without_generator():
    path=OUT/'runtime.json'
    if not path.exists():pytest.skip('Runtime not profiled')
    r=json.loads(path.read_text());assert not r['torch_loaded'] and not r['includes_generator'] and r['raw_score_replay_exact']
    assert len(r['measurements'])==100 and r['sampled_peak_rss_bytes']>=r['rss_after_model_load_bytes']
    assert r['total_seconds_p95']>=r['total_seconds_median']>0
