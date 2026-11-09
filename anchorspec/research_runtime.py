"""Read-only diagnostic replay with explicit external gate and signal checks.

This is an offline research interface, not an industrial monitoring service.
The quality check cannot recover out-of-band information or detect all faults.
"""
from dataclasses import dataclass
import numpy as np
from funnel import feats


@dataclass(frozen=True)
class SignalContract:
    fs: int = 4000
    bandwidth_hz: float = 1000.
    range_g: float = 8.
    bits: int = 20
    max_clipped_fraction: float = .001

    def validate(self):
        if self.fs<=0 or not 0<self.bandwidth_hz<self.fs/2 or self.range_g<=0 or not 2<=self.bits<=32:
            raise ValueError('Invalid sensor contract')
        if not 0<=self.max_clipped_fraction<1:
            raise ValueError('Invalid clipping limit')


def check_window(x, contract):
    contract.validate()
    a=np.asarray(x,float)
    if a.ndim!=1 or len(a)!=contract.fs:
        return dict(ok=False,reason='wrong_window_shape')
    if not np.isfinite(a).all():
        return dict(ok=False,reason='nonfinite_signal')
    if np.max(np.abs(a))>contract.range_g+2*contract.range_g/2**contract.bits:
        return dict(ok=False,reason='outside_declared_range')
    lsb=2*contract.range_g/2**contract.bits
    clipped=float((np.abs(a)>=contract.range_g-lsb).mean())
    if clipped>contract.max_clipped_fraction:
        return dict(ok=False,reason='sensor_saturation',clipped_fraction=clipped)
    if np.ptp(a)<=lsb:
        return dict(ok=False,reason='flat_signal',clipped_fraction=clipped)
    return dict(ok=True,reason='accepted',clipped_fraction=clipped)


def replay(model, frames, *, abnormal_flags, fs, fr, orders, contract=None):
    """Require one real upstream flag per window; never infer a perfect gate."""
    contract=contract or SignalContract()
    contract.validate()
    if fs!=contract.fs:raise ValueError('Sampling rate differs from training contract')
    if not np.isfinite(fr) or fr<=0:raise ValueError('Invalid shaft speed')
    a=np.asarray(frames,float)
    flags=np.asarray(abnormal_flags)
    if a.ndim!=2 or a.shape[1]!=fs or flags.shape!=(len(a),) or flags.dtype!=bool:
        raise ValueError('Need one-second windows and one Boolean flag per window')
    quality=[check_window(row,contract) for row in a]
    result=[dict(index=i,status='needs_signal_check' if not q['ok'] else
                 ('pending_diagnosis' if flags[i] else 'no_upstream_alarm'),label=None,quality=q)
            for i,q in enumerate(quality)]
    i=0
    while i<len(a):
        if result[i]['status']!='pending_diagnosis':i+=1;continue
        end=i+1
        while end<len(a) and result[end]['status']=='pending_diagnosis':end+=1
        training=getattr(model,'signal_contract_',None)
        if training is None or any(training.get(k)!=getattr(contract,k) for k in ('fs','bandwidth_hz','range_g','bits')):
            raise ValueError('Model has no matching acquisition contract')
        f=feats(a[i:end,None,:],fs,fr,orders,contract.bandwidth_hz)
        reference=model.reference_
        z=(f-reference['mu'])/reference['sd']
        pred=model.diagnose(z,abnormal_event=True)
        for j,c in enumerate(pred,i):
            result[j]['status']='diagnostic_hypothesis' if c>0 else 'insufficient_support'
            result[j]['label']=int(c) if c>0 else None
        i=end
    return dict(mode='offline_replay',upstream_gate='provided_by_caller',
                confidence_calibrated=False,rul_hours=None,windows=result)
