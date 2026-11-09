import numpy as np
from scipy.signal import hilbert
from cheap_sensor import CheapSensor
from joint_surrogate import rotate_pair,generate


def test_shared_phase_preserves_marginals_and_cross_spectrum():
    t=np.arange(4000)/4000
    x=np.stack([(1+.5*np.cos(2*np.pi*100*t))*np.cos(2*np.pi*600*t),
                (1+.2*np.cos(2*np.pi*70*t))*np.cos(2*np.pi*600*t+.8)])
    y=rotate_pair(x,.7);a=np.fft.rfft(x);b=np.fft.rfft(y)
    np.testing.assert_allclose(np.abs(hilbert(x,axis=1)),np.abs(hilbert(y,axis=1)),atol=1e-11)
    np.testing.assert_allclose(a[0]*a[1].conj(),b[0]*b[1].conj(),atol=1e-8)
    independent=rotate_pair(x,np.array([.7,-.4]));c=np.fft.rfft(independent)
    assert not np.allclose(a[0]*a[1].conj(),c[0]*c[1].conj())


def test_sensor_gate_returns_exact_measured_pair_when_proposal_exceeds_range():
    # Square waves have bounded measured values but large quadrature peaks.
    x=np.stack([np.sign(np.sin(2*np.pi*37*np.arange(4000)/4000))]*2)[None]*7.9
    arrays,meta=generate(x,np.random.default_rng(4),CheapSensor(),count=32)
    assert meta['identity_fallback']['joint_phase']>0
    for a in arrays.values():assert np.abs(a).max()<=8
    assert any(np.array_equal(a,x[0]) for a in arrays['joint_phase'])
