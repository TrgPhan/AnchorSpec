import numpy as np
import pytest
from research_runtime import SignalContract,check_window,replay
from w_kaist_eval import split_files


def test_bad_signal_and_external_gate_prevent_model_calls():
    class Never:
        def diagnose(self,*a,**kw):raise AssertionError('Model must not be called')
    valid=.1*np.sin(np.arange(4000))
    frames=np.stack([np.full(4000,np.nan),np.full(4000,8.),np.zeros(4000),valid])
    out=replay(Never(),frames,abnormal_flags=np.array([True,True,True,False]),fs=4000,fr=30,orders={})
    assert [w['status'] for w in out['windows']]==['needs_signal_check']*3+['no_upstream_alarm']
    assert all(w['label'] is None for w in out['windows'])
    assert out['rul_hours'] is None


def test_wrong_fs_or_non_boolean_flags_fail():
    with pytest.raises(ValueError,match='Sampling'):
        replay(None,np.ones((1,4000)),abnormal_flags=np.array([True]),fs=8000,fr=30,orders={})
    with pytest.raises(ValueError,match='Boolean'):
        replay(None,np.ones((1,4000)),abnormal_flags=np.array([1]),fs=4000,fr=30,orders={})


def test_clipping_threshold_and_valid_window():
    a=np.sin(np.arange(4000));assert check_window(a,SignalContract())['ok']
    a[:5]=8;assert not check_window(a,SignalContract())['ok']


def test_model_contract_is_required_before_diagnosis():
    class NoContract:
        def diagnose(self,*args,**kwargs):raise AssertionError('Wrong model contract')
    with pytest.raises(ValueError,match='acquisition contract'):
        replay(NoContract(),np.sin(np.arange(4000))[None],abnormal_flags=np.array([True]),fs=4000,fr=30,orders={})


def test_fresh_dataset_excludes_same_severity_in_every_training_load():
    for s in (0,2,4):
        for t in (0,2,4):
            if s==t:continue
            for severity in ('03','10','30'):
                train,test=split_files(s,t,severity)
                assert len(train)==4 and len(test)==2
                assert all(n.startswith(f'{s}Nm_') and not n.endswith('_'+severity) for n in train)
                assert all(n.startswith(f'{t}Nm_') and n.endswith('_'+severity) for n in test)
