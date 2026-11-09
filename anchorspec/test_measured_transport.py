import numpy as np
import pytest
from measured_transport import transfer_gain,generate,warp_speed


def test_same_healthy_spectrum_means_identity_transport():
    r=np.random.default_rng(5);x=r.normal(size=(4,4000))
    np.testing.assert_allclose(transfer_gain(x,x),1,atol=1e-14)
    np.testing.assert_array_equal(warp_speed(x[0],1),x[0])


def test_gain_is_bounded_and_does_not_invent_out_of_band_gain():
    r=np.random.default_rng(5);x=r.normal(size=(4,4000))
    gain=transfer_gain(x,x*100)
    assert gain.min()>=.5 and gain.max()<=2
    np.testing.assert_array_equal(gain[np.fft.rfftfreq(4000,1/4000)>1000],1)


def test_generation_is_deterministic_and_sensor_bounded():
    r=np.random.default_rng(1);h=r.normal(0,.01,(4,4000));f=r.normal(0,1,(4,4000))
    a,meta=generate(f,h,h*2,30,30.5,np.random.default_rng(11),count=4)
    b,_=generate(f,h,h*2,30,30.5,np.random.default_rng(11),count=4)
    for k in a:
        np.testing.assert_array_equal(a[k],b[k]);assert np.abs(a[k]).max()<=8
        assert not np.array_equal(a[k],f)
    assert len(meta['source_indices'])==4


def test_invalid_signal_and_speed_are_rejected():
    with pytest.raises(ValueError):warp_speed(np.ones(4000),0)
    with pytest.raises(ValueError):generate(np.full((2,4000),np.nan),np.ones((2,4000)),np.ones((2,4000)),30,30,np.random.default_rng(1))
