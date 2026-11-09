import numpy as np
import pytest
from event_experts import Event
from source_select import SourceSelector, training_arrays


def test_validation_derivative_is_never_read():
    class Protected(dict):
        def __getitem__(self,key):
            if key=='held': raise AssertionError('Validation derivative leaked')
            return super().__getitem__(key)
    events=[Event('train','a',1,np.ones((4,2)))]
    der=Protected(train=np.ones((150,2))*2,held=np.ones((150,2))*999)
    x,y,w=training_arrays(events,der,{},'surrogate_all')
    assert x.max()==2
    assert w.sum()==pytest.approx(4)
    assert w[:4].sum()==pytest.approx(w[4:].sum())


def test_same_svm_weight_budget_across_sources():
    events=[Event('a','a',1,np.ones((10,2))),Event('b','b',2,np.ones((20,2))*2)]
    der={e.event_id:np.ones((150,2))*e.label for e in events}
    phy={1:np.ones((150,2)),2:np.ones((150,2))*2}
    for source in ('real','surrogate_ring','surrogate_all','physics'):
        x,y,w=training_arrays(events,der,phy,source)
        assert w.sum()==pytest.approx(30)
        assert w[y==1].sum()==pytest.approx(w[y==2].sum())


def test_one_event_per_class_has_no_fake_validation_and_gate_is_respected():
    rng=np.random.default_rng(3)
    ev=[Event(str(c),str(c),c,rng.normal(c*5,.1,(8,3))) for c in (1,2)]
    refs={n:dict(mu=np.zeros(3),sd=np.ones(3)) for n in ('t','1','2')}
    der={e.event_id:np.repeat(e.features,20,axis=0) for e in ev}
    m=SourceSelector().fit(ev,der,{},target_id='t',references=refs)
    assert m.inner_folds_==[] and m.validation_==[]
    assert m.choices_['select']['source']=='real'
    assert (m.predict(ev[0].features,abnormal_event=False)==0).all()
    assert (m.predict(ev[0].features)==1).all()


def test_target_faults_are_rejected_before_reading_features():
    with pytest.raises(ValueError,match='leakage'):
        SourceSelector().fit([Event('e','t',1,np.ones((4,2)))],{}, {},target_id='t',references={})
