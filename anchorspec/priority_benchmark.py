"""Seven factory priorities quantified from frozen S/S2/S3 results and signals."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ.setdefault(key,'1')
from collections import defaultdict
import hashlib
import json
import pickle
import subprocess
import sys
import time
import numpy as np
from scipy import signal,stats
from s3_cpu_benchmark import ROOT,DATA,prepare
from s3_cached_features import CachedDecoder
from s_additive import additive_training
from invariant_classifier import InvariantClassifier
from event_experts import causal_average
from u_natural import LABEL,ORDERS,bearing
from y_metrics import paired_delta,macro

OUT=ROOT/'results/priorities';PRIMARY='spectral_flow_half:r1:a0.25'
METHODS=('real','duplicate:r1:a0.25','surrogate:r1:a0.25','severity:r1:a0.25','flow_full:r1:a0.25',
         'diffusion_full:r1:a0.25',PRIMARY,'spectral_diffusion_half:r1:a0.25')
LABELS=(-1,0,1,2,3,4)


def confusion(rows,key,stage):
    matrix=np.zeros((6,6),int)
    for row in rows:
        stages=('healthy','terminal') if stage=='healthy_terminal' else (stage,)
        for st in stages:
            truth=0 if st=='healthy' else row['label']
            for predicted in row['scores'][key][st]['policies']['selective']['predictions']:
                matrix[LABELS.index(truth),LABELS.index(predicted)]+=1
    return matrix


def class_metrics(matrix,label):
    i=LABELS.index(label);tp=int(matrix[i,i]);support=int(matrix[i].sum());issued=int(matrix[:,i].sum())
    fp=issued-tp;fn=support-tp
    return dict(label=label,tp=tp,fp=fp,fn=fn,support_evaluations=support,predicted_evaluations=issued,
                precision=tp/issued if issued else None,recall=tp/support if support else None,
                f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)


def signal_metrics(real,generated):
    """Paired source-anchor similarity; not independent physical label validation."""
    rms=lambda x:np.sqrt(np.mean(x*x,axis=1))
    ratio=rms(generated)/rms(real)
    f,p=signal.welch(real,4000,nperseg=1024,axis=1);_,q=signal.welch(generated,4000,nperseg=1024,axis=1)
    mask=(f>0)&(f<=1000)
    cosine=lambda a,b:np.sum(a*b,axis=1)/np.sqrt(np.sum(a*a,axis=1)*np.sum(b*b,axis=1))
    psd=cosine(p[:,mask],q[:,mask])
    # Relative spectral shape only: separately report RMS amplitude drift.
    p=p[:,mask]/p[:,mask].sum(1,keepdims=True);q=q[:,mask]/q[:,mask].sum(1,keepdims=True)
    floor=1e-12
    lsd=np.sqrt(np.mean((10*np.log10(np.maximum(q,floor))-10*np.log10(np.maximum(p,floor)))**2,axis=1))
    filt=signal.butter(4,(10,1000),'bandpass',fs=4000,output='sos')
    envelopes=[]
    for x in (real,generated):
        e=np.abs(signal.hilbert(signal.sosfiltfilt(filt,x,axis=1),axis=1));e-=e.mean(1,keepdims=True)
        ff,ee=signal.welch(e,4000,nperseg=1024,axis=1);envelopes.append(ee[:,(ff>0)&(ff<=500)])
    return dict(rms_ratio=ratio,rms_absolute_relative_error=np.abs(ratio-1),psd_cosine=psd,
                normalized_log_psd_rmse_db=lsd,envelope_psd_cosine=cosine(*envelopes),
                excess_kurtosis_absolute_error=np.abs(stats.kurtosis(generated,axis=1)-stats.kurtosis(real,axis=1)),
                anchor_correlation=cosine(real,generated))


def main():
    OUT.mkdir(exist_ok=True);hashes={}
    def read(name):
        p=ROOT/name;hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
    s=read('results/s/additive.json');s2=read('results/s2/fullrank.json');s3=read('results/s3/spectral.json')
    lookup2={(r['target'],r['seed']):r for r in s2['rows']};lookup3={(r['target'],r['seed']):r for r in s3['rows']}
    rows=[dict(target=r['target'],seed=r['seed'],label=r['label'],scores=r['scores']|lookup2[r['target'],r['seed']]['scores']|lookup3[r['target'],r['seed']]['scores']) for r in s['rows']]
    per_class=[];totals=[];matrices=[];by_bearing=[];regimes=[];event_counts=[];deltas=[]
    for key in METHODS:
        for stage in ('preterminal','terminal','healthy_terminal'):
            matrix=confusion(rows,key,stage)
            assert matrix.sum()==(585 if stage=='healthy_terminal' else 390)
            classes=[class_metrics(matrix,c) for c in ((0,1,2,4) if stage=='healthy_terminal' else (1,2,4))]
            for r in classes:per_class.append(dict(method=key,stage=stage,**r))
            for i,truth in enumerate(LABELS):
                for j,predicted in enumerate(LABELS):matrices.append(dict(method=key,stage=stage,true_label=truth,predicted_label=predicted,count=int(matrix[i,j])))
            totals.append(dict(method=key,stage=stage,accuracy=float(np.trace(matrix)/matrix.sum()),
                               macro_recall=float(np.mean([r['recall'] for r in classes])),
                               macro_precision_zero_for_undefined=float(np.mean([r['precision'] if r['precision'] is not None else 0. for r in classes])),
                               classes_with_defined_precision=sum(r['precision'] is not None for r in classes),
                               macro_f1=float(np.mean([r['f1'] for r in classes])),
                               predictions=int(matrix.sum()),abstentions=int(matrix[:,0].sum())))
        for stage in ('preterminal','terminal'):
            grouped=defaultdict(list)
            for row in rows:
                pred=np.asarray(row['scores'][key][stage]['policies']['selective']['predictions']);correct=int((pred==row['label']).sum())
                grouped[row['target']].append(correct/len(pred))
                event_counts.append(dict(method=key,stage=stage,target=row['target'],label=row['label'],seed=row['seed'],
                    correct_windows=correct,windows=len(pred),entire_stage_wrong=correct==0,
                    wrong_fault_windows=int(((pred>0)&(pred!=row['label'])).sum()),healthy_choices=int((pred==0).sum()),abstentions=int((pred<0).sum())))
            for n,v in grouped.items():
                by_bearing.append(dict(method=key,stage=stage,target=n,label=LABEL[n],recall=float(np.mean(v)),
                    seed_min=float(min(v)),seed_max=float(max(v)),missed_all_three_seeds=all(a==0 for a in v),
                    missed_at_least_one_seed=any(a==0 for a in v)))
            for condition,(rpm,load) in {'1':(2100,12),'2':(2250,11),'3':(2400,10)}.items():
                selected={n:v for n,v in grouped.items() if n.startswith(condition)}
                present=sorted(set(LABEL[n] for n in selected));vals={(n,LABEL[n]):float(np.mean(v)) for n,v in selected.items()}
                regimes.append(dict(method=key,stage=stage,condition=condition,rpm=rpm,load_kn=load,bearings=len(selected),
                    classes=','.join(map(str,present)),macro_recall_present_classes=macro(vals),
                    inner_recall=float(np.mean([v for (n,c),v in vals.items() if c==1])) if 1 in present else None,
                    outer_recall=float(np.mean([v for (n,c),v in vals.items() if c==2])) if 2 in present else None,
                    cage_recall=float(np.mean([v for (n,c),v in vals.items() if c==4])) if 4 in present else None))
    for stage in ('preterminal','terminal'):
        vals=lambda key:{(r['target'],r['label']):r['recall'] for r in by_bearing if r['method']==key and r['stage']==stage}
        for base in METHODS:
            deltas.append(dict(stage=stage,method=PRIMARY,baseline=base,**paired_delta(vals(PRIMARY),vals(base))))
    result=dict(scope='Frozen selective policy, no classifier or generator configuration changes',primary=PRIMARY,
                independent_bearings=13,seeds=[11,29,47],unique_healthy_snapshots=65,unique_terminal_snapshots=130,
                per_class=per_class,totals=totals,confusion=matrices,per_bearing=by_bearing,regimes=regimes,
                event_counts=event_counts,deltas=deltas,sha256=hashes,
                unknown_S3_measured=False,false_inspections_per_shift_measured=False,downtime_measured=False)
    (OUT/'diagnostics.json').write_text(json.dumps(result,indent=2));print('Diagnostic metrics reconstructed',flush=True)
    # Signal fidelity on the primary, paired with its actual measured anchors.
    physical=[];signal_hashes={}
    for row in s3['rows']:
        target,seed=row['target'],row['seed'];sources,waves,codec,indices,limits,_=prepare(target,seed)
        path=DATA/f'{target}_{seed}'/'residuals.npz';signal_hashes[path.relative_to(ROOT.parent).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        with np.load(path) as f:r=f['flow']
        anchors=waves[indices];generated=CachedDecoder(codec,anchors,limits)(r)
        measured=signal_metrics(anchors,generated)
        normalized=waves/np.linalg.norm(waves,axis=1)[:,None]
        correlations=generated@normalized.T/np.linalg.norm(generated,axis=1)[:,None]
        nearest=correlations.argmax(1);maximum=correlations[np.arange(len(generated)),nearest]
        copies=np.max(np.abs(generated-waves[nearest]),axis=1)<1e-10
        for i,n in enumerate(sources):
            sl=slice(i*10,(i+1)*10);record=dict(target=target,seed=seed,source=n,fault_class=LABEL[n])
            for metric,values in measured.items():record[metric]=float(np.mean(values[sl]))
            record.update(nearest_source_zero_lag_correlation=float(maximum[sl].mean()),
                          near_source_correlation_gt_099_fraction=float((maximum[sl]>.99).mean()),
                          exact_source_copy_fraction=float(copies[sl].mean()))
            physical.append(record)
    keys=list(physical[0])[4:];physical_summary=[]
    for c in (None,1,2,4):
        selected=physical if c is None else [r for r in physical if r['fault_class']==c]
        physical_summary.append(dict(fault_class='all' if c is None else c,donor_fold_seed_rows=len(selected),
                                     **{k:float(np.mean([r[k] for r in selected])) for k in keys}))
    q=[r['generation']['quality']['spectral_flow_half'] for r in s3['rows']]
    physical_result=dict(scope='Paired to source anchors; overlapping training donors; not independent validation of fault physics',
        summary=physical_summary,rows=physical,sha256=signal_hashes,
        mean_residual_clamp_fraction=float(np.mean([r['residual_clamp_fraction'] for r in q])),
        mean_peak_rescale_fraction=float(np.mean([r['peak_rescale_fraction'] for r in q])),
        new_pointwise_sensor_clipping_applied=False,original_sensor_saturation_unresolved=True)
    (OUT/'physical.json').write_text(json.dumps(physical_result,indent=2));print('Signal fidelity measured',flush=True)
    # Refit the frozen RF once, assert exact score replay, then profile in a clean child.
    target,seed='1_1',11;sources=[n for n in LABEL if n!=target];t=bearing(target)
    with np.load(DATA/f'{target}_{seed}'/'features.npz') as f:
        derived={n:{'flow':f[n+':spectral_flow_half']} for n in sources}
    events=[(n,LABEL[n],bearing(n)['terminal_features']) for n in sources]
    x,y,w,_=additive_training(t['healthy_features'][:5],events,derived,'flow',1.,.25)
    begin=time.perf_counter();model=InvariantClassifier('rf',seed).fit(x,y,w);fit_seconds=time.perf_counter()-begin
    record=lookup3[target,seed]['scores'][PRIMARY]['terminal'];raw=np.asarray(record['raw_scores'])
    np.testing.assert_array_equal(model.predict_proba(t['terminal_features']),raw)
    folder=ROOT.parent/'data/priority_runtime';folder.mkdir(exist_ok=True)
    with (folder/'rf.pkl').open('wb') as f:pickle.dump(model,f,protocol=pickle.HIGHEST_PROTOCOL)
    np.savez_compressed(folder/'query.npz',wave=t['terminal'][4],fr=t['fr'],orders=list(ORDERS.values()),
                        history=raw[:4],expected_raw=raw[4],expected_prediction=record['policies']['selective']['predictions'][4])
    child=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'priority_runtime_worker.py'),str(folder)],capture_output=True,text=True,check=True)
    runtime=json.loads(child.stdout);assert runtime['raw_score_replay_exact'] and not runtime['torch_loaded']
    runtime['rf_refit_seconds_parent_process']=fit_seconds
    runtime['rf_refit_scope']='Exact frozen fold replay, no new configuration; parent process includes research imports'
    (OUT/'runtime.json').write_text(json.dumps(runtime,indent=2));print('Isolated online diagnostic profile measured',flush=True)
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in hashes.items())


if __name__=='__main__':main()
