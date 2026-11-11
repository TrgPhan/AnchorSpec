"""Kham pha sau khi da xem ket qua: UORED 5 bo su co, RF 50 vs 500 cay, selective vs conditional, cham theo su co."""
import sys; sys.path.insert(0,'.')
import os; os.environ.setdefault('OMP_NUM_THREADS','1')
import json, numpy as np
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import invariant_classifier as IC
from sklearn.ensemble import RandomForestClassifier as RFC
import s3_dose as D
from event_experts import causal_average
from t_readiness import selective
from diagnostic_experts import fault_labels
ARMS=('real','dup_add_0.25','flow_mix_0.25_30','flow_add_0.25_30')
def job(task):
    ds,target,seed,prof=task
    t=D.item(ds,target); donors=D.donors_for(ds,target,seed,prof)
    counts=Counter(D.item(ds,n)['label'] for n in donors)
    events=[(n,D.item(ds,n)['label'],D.item(ds,n)['donor']) for n in donors]
    base=D.training(t['base'],events,{},'real')
    arms={k:v for k,v in D.fixed_arms(base,counts).items() if k in ARMS}
    (gens,),_=D.generate(ds,donors,seed,(20261106,),prop=False)
    arms.update(D.flow_arms(base,counts,gens[0],None,[a for a in ARMS if a.startswith('flow')]))
    out={}
    for ntree in (50,500):
        IC.RandomForestClassifier=lambda **kw: RFC(**{**kw,'n_estimators':ntree})
        for a,xyw in arms.items():
            m=IC.InvariantClassifier('rf',seed).fit(*xyw)
            p=causal_average(m.predict_proba(t['severe']))
            out[f'{ntree}:{a}']=dict(sel=float(np.mean(selective(p,0)==t['label'])),cond=float(np.mean(fault_labels(p)==t['label'])))
    return dict(ds=ds,target=str(target),seed=seed,profile=prof,label=t['label'],out=out)
def macro(per,lab): return float(np.mean([np.mean([v for n,v in per.items() if lab[n]==c]) for c in (1,2,4)]))
if __name__=='__main__':
    tasks=[('uored',n,s,p) for p in D.PROFILES for n in D.UNAMES for s in D.SEEDS]
    with ProcessPoolExecutor(12) as pool: rows=list(pool.map(job,tasks))
    json.dump(rows,open(sys.argv[1],'w'))
    rng=np.random.default_rng(11)
    print('Bo     | RF  | chinh sach | real (do rong seed) | dup | flow_mix_25_30 | flow_add_25_30 || flow_mix - real [CI] | dup - real [CI] | flow_add - dup [CI] | su co dung (real/dup/mix, tren 45)')
    for prof in D.PROFILES:
        sub=[r for r in rows if r['profile']==prof]; lab={r['target']:r['label'] for r in sub}; G={c:[t for t in lab if lab[t]==c] for c in (1,2,4)}
        for ntree in (50,500):
            for pol in ('sel','cond'):
                per=lambda a:{t:np.mean([r['out'][f'{ntree}:{a}'][pol] for r in sub if r['target']==t]) for t in lab}
                byseed=lambda a:[macro({r['target']:r['out'][f'{ntree}:{a}'][pol] for r in sub if r['seed']==s},lab) for s in D.SEEDS]
                def comp(a,b):
                    A,B=per(a),per(b); f=lambda ts: np.mean([np.mean([A[t]-B[t] for t in ts if lab[t]==c]) for c in (1,2,4)])
                    bs=[f([x for g in G.values() for x in rng.choice(g,len(g))]) for _ in range(3000)]
                    return f'{f(list(lab))*100:+5.1f} [{np.percentile(bs,2.5)*100:+5.1f};{np.percentile(bs,97.5)*100:+5.1f}]'
                ev=[sum(r['out'][f'{ntree}:{a}'][pol]>0.5 for r in sub) for a in ('real','dup_add_0.25','flow_mix_0.25_30')]
                bs=byseed('real')
                print(f"{prof:6s} | {ntree:3d} | {pol:4s} | {macro(per('real'),lab)*100:5.1f} ({(max(bs)-min(bs))*100:4.1f}) | {macro(per('dup_add_0.25'),lab)*100:5.1f} | {macro(per('flow_mix_0.25_30'),lab)*100:5.1f} | {macro(per('flow_add_0.25_30'),lab)*100:5.1f} || {comp('flow_mix_0.25_30','real')} | {comp('dup_add_0.25','real')} | {comp('flow_add_0.25_30','dup_add_0.25')} | {ev}")
