import numpy as np
import pytest
from invariant_classifier import canonicalize,InvariantClassifier


@pytest.mark.parametrize('family',['svm1','svm10','rf'])
@pytest.mark.parametrize('mass',[.25,.5,.7])
def test_replicating_rows_cannot_change_predictions(family,mass):
    rng=np.random.default_rng(9);x=rng.normal(size=(23,5));y=np.arange(23)%3;w=rng.uniform(.1,2,23);test=rng.normal(size=(15,5))
    a=InvariantClassifier(family).fit(x,y,w)
    xx=np.concatenate((x,x));yy=np.tile(y,2);ww=np.concatenate((w*(1-mass),w*mass))
    order=rng.permutation(len(yy));b=InvariantClassifier(family).fit(xx[order],yy[order],ww[order])
    np.testing.assert_array_equal(a.predict_proba(test),b.predict_proba(test))
    assert a.unique_rows_==b.unique_rows_ and a.total_weight_==b.total_weight_


def test_conflicting_labels_remain_distinct_and_zero_mass_is_ignored():
    x,y,w=canonicalize(np.array([[1.,2.],[1.,2.],[9.,8.]]),np.array([1,2,0]),np.array([1.,1.,0.]))
    assert len(x)==2 and set(y)=={1,2} and w.sum()==2


def test_negative_weights_are_invalid():
    with pytest.raises(ValueError):canonicalize(np.ones((2,2)),np.array([1,2]),np.array([-1.,1.]))
