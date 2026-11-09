import io
import zipfile
from pathlib import Path

import numpy as np
import pytest

import z_open_data as D
from z_screen import blocked_split, first_sustained, snapshot_bounds, baseline_deviation


def test_member_paths_cannot_escape_workspace():
    for name in ('../secret','/absolute','C:/absolute','a/../../secret'):
        with pytest.raises(ValueError):D.safe_name(name)
    assert D.safe_name('Test_7/sample.mat')=='sample.mat'


def test_range_member_download_crc_and_cache(tmp_path,monkeypatch):
    buf=io.BytesIO()
    payload=b'public measured data\0'*1000
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('test/acc.mat',payload)
    raw=buf.getvalue()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:info=z.getinfo('test/acc.mat')
    class Response:
        def __init__(self,content):self.content=content
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def iter_content(self,n):yield self.content
    monkeypatch.setattr(D,'range_response',lambda url,start,end:Response(raw[start:end+1]))
    result=D.member_download('local-test',info,tmp_path)
    assert (tmp_path/'acc.mat').read_bytes()==payload
    assert result['crc_verified']
    assert D.member_download('local-test',info,tmp_path)==result


def test_blocked_split_keeps_gaps_and_never_shuffles_each_class():
    labels=np.repeat([1,2,3],100)
    train,gap,test=blocked_split(labels)
    assert len(train)==180 and len(gap)==60 and len(test)==60
    assert not set(train)&set(test)
    for c in (1,2,3):
        assert train[labels[train]==c].max()<gap[labels[gap]==c].min()<test[labels[test]==c].min()


def test_alarm_is_emitted_at_third_observation_without_future():
    mask=np.array([False]*10+[True,True,True,False])
    assert first_sustained(mask)==12
    assert first_sustained(mask[:12]) is None


def test_snapshot_gaps_and_reference_only_scoring():
    t=np.r_[np.arange(10)/10000,900+np.arange(10)/10000]
    assert snapshot_bounds(t)==[(0,10),(10,20)]
    rng=np.random.default_rng(1)
    x=rng.normal(size=(20,9))
    expected=baseline_deviation(x)
    x[-1]*=100
    actual=baseline_deviation(x)
    np.testing.assert_allclose(expected[:-1],actual[:-1])
