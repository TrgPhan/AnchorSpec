import numpy as np
import pytest

from diagnostic_experts import DiagnosticExperts, fault_labels
from event_experts import Event


def test_healthy_winner_does_not_mask_conditional_fault_hypothesis():
    p=np.array([[.9,.01,.08,.005,.005],[1.,0.,0.,0.,0.]])
    np.testing.assert_array_equal(fault_labels(p),[2,-1])


def test_upstream_gate_and_empty_real_library():
    rng=np.random.default_rng(9)
    h=rng.normal(0,.1,(12,3))
    refs={'t':{'mu':np.zeros(3),'sd':np.ones(3)}}
    model=DiagnosticExperts(real_only=True).fit(h,{1:h+1,2:h+2},[],target_id='t',references=refs)
    assert (model.diagnose(h,abnormal_event=False)==0).all()
    assert (model.diagnose(h,abnormal_event=True)==-1).all()


def test_fault_target_cannot_enter_diagnostic_model():
    h=np.ones((12,3))
    with pytest.raises(ValueError,match='leakage'):
        DiagnosticExperts().fit(h,{1:h,2:h},[Event('e','t',1,h)],target_id='t',references={})
