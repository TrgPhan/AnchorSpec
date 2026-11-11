"""Kham pha sau khi da xem ket qua: nguon ngau nhien va RF lon hon. Khong ghi vao results/."""
import sys; sys.path.insert(0,'.')
import os; os.environ.setdefault('OMP_NUM_THREADS','1')
import json, numpy as np
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import invariant_classifier as IC
from sklearn.ensemble import RandomForestClassifier as RFC
import s3_dose as D
from u_natural import LABEL
from event_experts import causal_average
from t_readiness import selective
from diagnostic_experts import fault_labels
SEEDS=(11,29,47,101,202)
ARMS=('real','dup_add_0.25','flow_mix_0.25_30','flow_add_0.25_30')
def job(task):
    target,seed,ntree=task
    IC.RandomForestClassifier=lambda **kw: RFC(**{**kw,'n_estimators':ntree})
    t=D.item('xjtu',target); donors=D.donors_for('xjtu',target,seed,'natural')
    counts=Counter(D.item('xjtu',n)['label'] for n in donors)
    events=[(n,D.item('xjtu',n)['label'],D.item('xjtu',n)['donor']) for n in donors]
    base=D.training(t['base'],events,{},'real')
    arms={k:v for k,v in D.fixed_arms(base,counts).items() if k in ARMS}
    (gens,),_=D.generate('xjtu',donors,seed,(20261106,),prop=False)
    arms.update(D.flow_arms(base,counts,gens[0],None,[a for a in ARMS if a.startswith('flow')]))
    out={}
    for a,xyw in arms.items():
        m=IC.InvariantClassifier('rf',seed).fit(*xyw)
        p=causal_average(m.predict_proba(t['severe']))
        out[a]=dict(sel=float(np.mean(selective(p,0)==t['label'])),cond=float(np.mean(fault_labels(p)==t['label'])),
                    hf=float(np.mean(selective(causal_average(m.predict_proba(t['hold'])),0)>0)))
    return target,seed,ntree,t['label'],out
def macro(per,lab):
    return np.mean([np.mean([v for n,v in per.items() if lab[n]==c]) for c in (1,2,4)])
if __name__=='__main__':
    tasks=[(t,s,n) for n in (50,500) for t in LABEL for s in SEEDS]
    with ProcessPoolExecutor(12) as p: rows=list(p.map(job,tasks))
    lab={r[0]:r[3] for r in rows}
    res={}
    for ntree in (50,500):
        print(f'\n=== RF {ntree} cay, XJTU 13 o, 5 seed (macro recall cuoi doi) ===')
        for pol in ('sel','cond'):
            for a in ARMS:
                byseed=[macro({r[0]:r[4][a][pol] for r in rows if r[2]==ntree and r[1]==s},lab) for s in SEEDS]
                mean=macro({t:np.mean([r[4][a][pol] for r in rows if r[2]==ntree and r[0]==t]) for t in lab},lab)
                res[(ntree,pol,a)]=mean
                print(f'  {pol:4s} {a:18s} TB {mean*100:6.2f} | theo seed {min(byseed)*100:5.1f}-{max(byseed)*100:5.1f} (do rong {(max(byseed)-min(byseed))*100:4.1f})')
    # paired bootstrap at 500 trees
    rng=np.random.default_rng(7); G={c:[t for t in lab if lab[t]==c] for c in (1,2,4)}
    def per(ntree,pol,a): return {t:np.mean([r[4][a][pol] for r in rows if r[2]==ntree and r[0]==t]) for t in lab}
    print('\n=== 500 cay: chenh lech, CI 95% theo o ===')
    for pol in ('sel','cond'):
        for a,b in (('flow_mix_0.25_30','real'),('flow_mix_0.25_30','dup_add_0.25'),('dup_add_0.25','real'),('flow_add_0.25_30','dup_add_0.25')):
            A,B=per(500,pol,a),per(500,pol,b)
            f=lambda ts: np.mean([np.mean([A[t]-B[t] for t in ts if lab[t]==c]) for c in (1,2,4)])
            bs=[f([x for g in G.values() for x in rng.choice(g,len(g))]) for _ in range(5000)]
            print(f'  {pol:4s} {a} - {b}: {f(list(lab))*100:+.2f} [{np.percentile(bs,2.5)*100:+.2f}; {np.percentile(bs,97.5)*100:+.2f}]')
    json.dump([list(r[:4])+[r[4]] for r in rows],open(sys.argv[1],'w'))
