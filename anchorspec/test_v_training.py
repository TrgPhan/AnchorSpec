import numpy as np
import pytest
import v_transport_run as V
from event_experts import Event


@pytest.fixture
def training_case(monkeypatch):
    refs={n:dict(base=np.full((3,2),int(n)),mu=np.zeros(2),sd=np.ones(2)) for n in ('1','2','3')}
    events=[Event('e2','2',1,np.full((5,2),2.)),Event('e3','3',2,np.full((7,2),3.))]
    monkeypatch.setattr(V,'store',lambda:refs)
    def generated(target,seed):
        # Access to any unrelated cached bearing is an error.
        return {f'{e.bearing_id}_{m}':np.full((64,2),int(e.bearing_id)+.1)
                for e in events for m in ('surrogate','severity','transport','transport_mix')}
    monkeypatch.setattr(V,'generated',generated)
    return events


def test_target_fault_rejected_before_cache_access(training_case,monkeypatch):
    monkeypatch.setattr(V,'generated',lambda *args:pytest.fail('Cache accessed before lineage validation'))
    with pytest.raises(ValueError,match='leakage'):
        V.training('2',training_case,'transport_mix','raw',.5,11)


def test_only_supplied_donors_can_enter_training(training_case):
    x,y,w=V.training('1',training_case[:1],'transport_mix','raw',.5,11)
    assert set(y)=={0,1}
    assert np.max(x)<3


def test_class_weight_and_total_penalty_do_not_grow_with_synthetic_count(training_case):
    expected=None
    for method in V.METHODS:
        x,y,w=V.training('1',training_case,method,'raw',.5,11)
        assert np.isfinite(x).all() and np.isfinite(w).all()
        assert w.sum()==pytest.approx(15.)
        totals=[w[y==c].sum() for c in (0,1,2)]
        if expected is None:expected=totals
        np.testing.assert_allclose(totals,expected)


def test_duplicate_control_preserves_weighted_training_distribution(training_case):
    xr,yr,wr=V.training('1',training_case,'real','raw',0,11)
    xd,yd,wd=V.training('1',training_case,'duplicate','raw',.5,11)
    for c in (0,1,2):
        np.testing.assert_allclose(np.average(xr[yr==c],axis=0,weights=wr[yr==c]),
                                   np.average(xd[yd==c],axis=0,weights=wd[yd==c]))


def test_validation_excludes_held_bearing_and_all_its_derivatives(monkeypatch):
    events=[Event(f'e{i}',str(i),1 if i<4 else 2,np.ones((2,2))) for i in (2,3,4,5)]
    calls=[]
    def training(target,train,*args):
        assert target not in {e.bearing_id for e in train}
        calls.append(target)
        return np.ones((2,2)),np.array([1,2]),np.ones(2)
    class Dummy:
        def __init__(self,*args):pass
        def fit(self,*args):return self
    monkeypatch.setattr(V,'training',training);monkeypatch.setattr(V,'FaultModel',Dummy)
    monkeypatch.setattr(V,'predict',lambda model,target,*args:np.array([1 if int(target)<4 else 2]))
    assert V.validation(events,'transport_mix','rf','raw',.5,11)==1.
    assert set(calls)=={'2','3','4','5'}
