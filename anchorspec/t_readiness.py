"""Diagnostic stress test; no factory alarm rates or independent confirmation claim."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import numpy as np
from u_natural import ROOT, CACHE, LABEL, ORDERS, bearing, training
from invariant_classifier import InvariantClassifier
from measured_transport import generate
from event_experts import causal_average
from diagnostic_experts import fault_labels
from y_metrics import macro, paired_delta
import funnel as Fu

OUT=ROOT/'results/t'
METHODS=('real','duplicate','surrogate','severity','transport')
FAMILIES=('rf','svm1')
THRESHOLDS=(0.,.5,.7,.9)
SEEDS=(11,29,47)


def selective(scores, threshold):
    p=np.asarray(scores,float)
    if p.ndim!=2 or p.shape[1]!=5 or not np.isfinite(p).all() or np.any(p<0) or not np.allclose(p.sum(1),1):
        raise ValueError('Expected finite normalized five-class scores')
    if not 0<=threshold<=1: raise ValueError('Invalid threshold')
    labels=p.argmax(1)
    return np.where(p.max(1)>=threshold,labels,-1)


def measurements(pred,label):
    pred=np.asarray(pred,int)
    if not len(pred): raise ValueError('Empty evaluation')
    issued=pred>0; correct=pred==label
    return dict(recall=float(correct.mean()),fault_claim=float(issued.mean()),
        abstain=float((pred<0).mean()),healthy_choice=float((pred==0).mean()),
        correct_fault=float((correct & issued).mean()),
        prediction_counts={str(c):int((pred==c).sum()) for c in (-1,0,1,2,3,4)})


def digest():
    files=[ROOT/n for n in ('t_readiness.py','PROTOCOL_T_READINESS.md','u_natural.py',
        'u_download.py','invariant_classifier.py','measured_transport.py','cheap_sensor.py',
        'features.py','funnel.py','bearing.py','event_experts.py','diagnostic_experts.py','y_metrics.py')]
    files += [CACHE/f'{n}.npz' for n in LABEL]
    files += [CACHE/f'{n}_{seed}_aug.npz' for n in LABEL for seed in SEEDS]
    return {str(p.relative_to(ROOT.parent)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def job(task):
    target,seed=task;t=bearing(target);events=[];der={}
    for name in LABEL:
        if name==target:continue
        s=bearing(name);events.append((name,LABEL[name],s['terminal_features']))
        rng=np.random.default_rng([seed,int(target[0]),int(target[-1]),int(name[0]),int(name[-1]),10])
        waves,_=generate(s['terminal'],s['healthy'],t['healthy'][:5],float(s['fr']),float(t['fr']),rng)
        der[name]={m:Fu.feats(waves[m][:,None,:],4000,float(s['fr']) if m=='severity' else float(t['fr']),ORDERS)
                   for m in ('severity','transport')}
        with np.load(CACHE/f'{name}_{seed}_aug.npz') as f:der[name]['surrogate']=f['surrogate']
    row=dict(target=target,seed=seed,label=LABEL[target],reference_indices=list(range(1,6)),
        healthy_test_indices=list(range(6,11)),libraries={})
    for library in ('closed','missing_cage'):
        selected=[e for e in events if library=='closed' or e[1]!=4]
        result=dict(donors=[n for n,c,x in selected],models={});row['libraries'][library]=result
        for family in FAMILIES:
            reference={}
            for method in METHODS:
                model=InvariantClassifier(family,seed).fit(*training(t['healthy_features'][:5],selected,der,method))
                record={};result['models'][f'{family}:{method}']=record
                for stage,x in (('healthy',t['healthy_features'][5:]),('preterminal',t['preterminal_features']),('terminal',t['terminal_features'])):
                    raw=model.predict_proba(x)
                    if method=='real':reference[stage]=raw
                    if method=='duplicate':np.testing.assert_array_equal(raw,reference[stage])
                    scores=causal_average(raw);label=0 if stage=='healthy' else LABEL[target]
                    policies={'conditional':fault_labels(scores)}
                    policies.update({f'selective_{v:g}':selective(scores,v) for v in THRESHOLDS})
                    record[stage]=dict(raw_scores=raw.tolist(),scores=scores.tolist(),
                        policies={k:dict(predictions=p.tolist(),**measurements(p,label)) for k,p in policies.items()})
    return row


def values(rows,library,model,stage,policy,metric,labels=None):
    groups={}
    for r in rows:
        if labels is not None and r['label'] not in labels:continue
        groups.setdefault((r['target'],r['label']),[]).append(r['libraries'][library]['models'][model][stage]['policies'][policy][metric])
    return {k:float(np.mean(v)) for k,v in groups.items()}


def aggregate(rows):
    out={}
    for library in ('closed','missing_cage'):
        out[library]={}
        for family in FAMILIES:
            for method in METHODS:
                model=f'{family}:{method}';out[library][model]={}
                for policy in ('conditional',*(f'selective_{v:g}' for v in THRESHOLDS)):
                    result={};out[library][model][policy]=result
                    for stage in ('healthy','preterminal','terminal'):
                        val=lambda metric,labels=None:values(rows,library,model,stage,policy,metric,labels)
                        # Healthy diagnostic stress: equal bearing weight, not future fault-class balancing.
                        avg=(lambda v:float(np.mean(list(v.values())))) if stage=='healthy' else macro
                        claim=avg(val('fault_claim'));correct=avg(val('correct_fault'))
                        result[stage]=dict(recall=avg(val('recall')),fault_claim=claim,
                            accuracy_among_fault_claims=correct/claim if claim else None,
                            abstain=avg(val('abstain')),healthy_choice=avg(val('healthy_choice')),
                            per_class={str(c):macro(val('recall',[c])) for c in (1,2,4)} if stage!='healthy' else {})
                        if stage!='healthy':
                            result[stage]['vs_real']=paired_delta(val('recall'),values(rows,library,f'{family}:real',stage,policy,'recall'))
                    if library=='missing_cage':
                        result['unknown_cage']={m:macro(values(rows,library,model,'terminal',policy,m,[4]))
                            for m in ('fault_claim','abstain','healthy_choice')}
    primary=out['closed']['rf:severity']['selective_0.5']
    real=out['closed']['rf:real']['selective_0.5'];old=out['closed']['rf:surrogate']['selective_0.5']
    checks=dict(terminal_macro80=primary['terminal']['recall']>=.8,
        each_class70=min(primary['terminal']['per_class'].values())>=.7,
        healthy_false_fault5=primary['healthy']['fault_claim']<=.05,
        gain5pp=primary['terminal']['vs_real']['delta']>=.05,
        positive_exploratory_ci=primary['terminal']['vs_real']['ci95'][0]>0,
        no_loss_to_surrogate=primary['terminal']['recall']>=old['terminal']['recall'],
        preterminal_noninferiority=primary['preterminal']['recall']>=real['preterminal']['recall']-.02,
        unknown_fault_claim10=out['missing_cage']['rf:severity']['selective_0.5']['unknown_cage']['fault_claim']<=.1)
    return out,dict(checks=checks,passed=all(checks.values()),factory_ready=False)


def main():
    OUT.mkdir(parents=True,exist_ok=True);frozen=digest();rows=[]
    # Persist before execution so later reports cannot retroactively redefine the protocol.
    (OUT/'prerun.json').write_text(json.dumps(dict(sha256=frozen,primary='rf:severity:selective_0.5',confirmatory=False),indent=2))
    with ProcessPoolExecutor(4) as pool:
        for row in pool.map(job,[(n,s) for n in LABEL for s in SEEDS]):
            rows.append(row);print('Readiness',len(rows),'/39',row['target'],row['seed'],flush=True)
    summary,gate=aggregate(rows)
    if frozen!=digest():raise ValueError('Source or prepared data changed during evaluation')
    result=dict(rows=rows,summary=summary,research_gate=gate,sha256=frozen,
        duplicate_identical=True,confirmatory=False,upstream_flags='forced true stress test',
        independent_bearings=13,healthy_snapshots_assumed=True)
    (OUT/'readiness.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(gate),flush=True)


if __name__=='__main__':main()
