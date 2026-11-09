"""Exercise the current real-event champion through the signal-quality interface."""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import hashlib
import json
import pickle
import time
import numpy as np
from diagnostic_experts import DiagnosticExperts
from research_runtime import replay,SignalContract
from y_run import load_store,donors,synthetic,ROOT
import e8_uored as U

OUT=ROOT/'results'/'w'
MODELS=ROOT.parent/'data'/'w_models'


def job(name):
    seed=11;store=load_store();item=store[name];stream=donors(store,name,seed)
    ev=[e for c in range(1,5) for e in [v for v in stream if v.label==c][:4]]
    refs={n:dict(mu=v['mu'],sd=v['sd']) for n,v in store.items()}
    start=time.perf_counter()
    model=DiagnosticExperts(seed,real_only=True).fit(item['base'],synthetic(name,seed,item),ev,target_id=name,references=refs)
    fit_seconds=time.perf_counter()-start
    model.signal_contract_=asdict(SignalContract())
    frozen=pickle.dumps(model)
    (MODELS/f'uored_{name}.pkl').write_bytes(frozen)
    U.ALLOW_FAULT['on']=True
    i=int(name)
    def digital_windows(x):
        # Inspect original sensor samples before per-window mean removal.
        return np.stack([x[j:j+4000] for j in range(0,len(x)-3999,2000)])
    healthy=digital_windows(U.sensed(i,0,U.SENSORS['1k']))[12:]
    fault=digital_windows(U.sensed(i,2,U.SENSORS['1k']))
    frames=np.concatenate([healthy,fault])
    # Deliberately label-derived for a controlled interface demo, never claimed measured gate.
    flags=np.r_[np.zeros(len(healthy),bool),np.ones(len(fault),bool)]
    start=time.perf_counter()
    out=replay(model,frames,abnormal_flags=flags,fs=4000,fr=item['fr'],orders=U.ORDERS)
    elapsed=time.perf_counter()-start
    truth=('healthy','inner','outer','ball','cage').index(item['lab'])
    for idx,row in enumerate(out['windows']):row['truth_for_offline_audit']=0 if idx<len(healthy) else truth
    return dict(target=name,truth=truth,donor_events=[e.event_id for e in ev],choice=model.selection_,
        model_sha256=hashlib.sha256(frozen).hexdigest(),model_bytes=len(frozen),fit_seconds=fit_seconds,
        batch_replay_ms=1000*elapsed,amortized_ms_per_window=1000*elapsed/len(frames),
        gate_warning='label-derived flags for interface replay, not measured detector',result=out)


def main():
    MODELS.mkdir(parents=True,exist_ok=True)
    rows=[]
    with ProcessPoolExecutor(4) as pool:
        for i,r in enumerate(pool.map(job,[str(i) for i in range(1,21)]),1):
            rows.append(r);print('replay',i,'/20',flush=True)
    (OUT/'runtime_replay.json').write_text(json.dumps(dict(contract=asdict(SignalContract()),rows=rows,
        hardware='local Windows computer, not Raspberry Pi',gate_is_label_derived=True),indent=2),encoding='utf8')


if __name__=='__main__':main()
