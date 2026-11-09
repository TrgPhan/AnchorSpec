import numpy as np
from scipy.signal import hilbert
from envelope_surrogate import rotate,generate


def test_common_phase_preserves_spectrum_and_analytic_envelope():
    t=np.arange(4000)/4000
    x=(1+.5*np.cos(2*np.pi*100*t))*np.cos(2*np.pi*600*t)
    y=rotate(x,1.3)
    np.testing.assert_allclose(np.abs(np.fft.rfft(x)),np.abs(np.fft.rfft(y)),atol=1e-11)
    np.testing.assert_allclose(np.abs(hilbert(x)),np.abs(hilbert(y)),atol=1e-11)
    assert not np.allclose(x,y)


def test_output_clipping_is_reported_and_bounded():
    t=np.arange(4000)/4000;x=20*np.cos(2*np.pi*100*t)
    y,meta=generate(x[None],np.random.default_rng(3),count=4)
    assert meta['clipping_fraction']>0 and np.max(np.abs(y))<=8
