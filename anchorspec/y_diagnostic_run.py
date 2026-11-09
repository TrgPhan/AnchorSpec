"""Evaluate the separately frozen conditional diagnostic selection protocol."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import hashlib
import json
import pickle
import time
import numpy as np

from diagnostic_experts import DiagnosticExperts
from y_run import load_store,synthetic,donors,OUT,ROOT,hashes


def job(row):
    target,seed=row['target'],row['seed']
    store=load_store(); item=store[target]
    syn=synthetic(target,seed,item)
    available={e.event_id:e for e in donors(store,target,seed)}
    events=[replace(available[key],label=label) for key,label in zip(row['donor_events'],row['donor_labels'])]
    refs={n:{'mu':store[n]['mu'],'sd':store[n]['sd']} for n in {target}|{e.bearing_id for e in events}}
    output={k:row[k] for k in ('target','seed','budget','label','mode','control','donor_events','donor_labels')}
    output|={'scores':{},'selection':{},'costs':{}}
    for method,real in (('diagnostic',False),('diagnostic_real',True)):
        start=time.perf_counter()
        model=DiagnosticExperts(seed,real).fit(item['base'],syn,events,target_id=target,references=refs)
        output['costs'][method]={'fit_ms':1000*(time.perf_counter()-start),'pickle_bytes':len(pickle.dumps(model))}
        output['selection'][method]={'chosen':model.selection_,'validation':model.validation_,'inner_folds':model.inner_folds_}
        output['scores'][method]={}
        for state in ('early','late'):
            pred=model.diagnose(item[state],abnormal_event=True)
            output['scores'][method][state]={'conditional_recall':float((pred==row['label']).mean()),
                'coverage':float((pred>0).mean()),'prediction_counts':{str(k):int((pred==k).sum()) for k in (-1,1,2,3,4)}}
    return output


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=('balanced','stream'),default='balanced');args=p.parse_args()
    rows=json.loads((OUT/f'adaptive_{args.mode}.json').read_text())['rows']
    frozen=hashes()|{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
        ('diagnostic_experts.py','y_diagnostic_run.py','kernel_experts.py','adaptive_experts.py','PROTOCOL_Y_DIAGNOSTIC.md')}
    result=[]
    with ProcessPoolExecutor(4) as pool:
        for i,r in enumerate(pool.map(job,rows),1):
            result.append(r)
            if i%20==0:print('diagnostic',args.mode,i,'/',len(rows),flush=True)
    if any(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h for n,h in frozen.items()):
        raise RuntimeError('Source changed during experiment')
    (OUT/f'diagnostic_{args.mode}.json').write_text(json.dumps({'conditional_on_correct_upstream_gate':True,'code_sha256':frozen,'rows':result},indent=2),encoding='utf8')


if __name__=='__main__':
    main()
