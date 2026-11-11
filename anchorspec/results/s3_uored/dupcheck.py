import sys; sys.path.insert(0,'.')
import json, numpy as np
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import s3_delta as D, s3_uored as UO
from u_natural import LABEL, bearing, training
from invariant_classifier import InvariantClassifier
ALPHA,SYN=.25,10
def dup_rows(x,y,w,donor_feats,counts):
    xs,ys,ws=[x],[y],[w]; scale=len(x)/(1+len(counts))
    for lab,f in donor_feats:
        xs.append(f); ys.append(np.full(len(f),lab,int)); ws.append(np.full(len(f),ALPHA*scale/(counts[lab]*SYN)))
    return np.concatenate(xs),np.concatenate(ys),np.concatenate(ws)
def xjtu(task):
    target,seed=task; t=bearing(target); donors=[n for n in LABEL if n!=target]; counts=Counter(LABEL[n] for n in donors)
    events=[(n,LABEL[n],bearing(n)['terminal_features']) for n in donors]
    x,y,w=training(t['healthy_features'][:5],events,{},'real')
    m=InvariantClassifier('rf',seed).fit(*dup_rows(x,y,w,[(LABEL[n],bearing(n)['terminal_features']) for n in donors],counts))
    return dict(target=target,seed=seed,label=LABEL[target],scores={'dup_raw':D.predict(m,t,0.)})
def uored(task):
    target,seed,mm=task; t=UO.item(target); donors=UO.chosen(target,seed,mm); counts=Counter(UO.item(n)['label'] for n in donors)
    events=[(n,UO.item(n)['label'],UO.item(n)['donor']) for n in donors]
    x,y,w=training(t['base'],events,{},'real')
    m=InvariantClassifier('rf',seed).fit(*dup_rows(x,y,w,[(UO.item(n)['label'],UO.item(n)['donor']) for n in donors],counts))
    return dict(target=target,seed=seed,budget=mm,label=t['label'],scores={'dup_raw@0':UO.predict(m,t,0.)})
if __name__=='__main__':
    # 1) code-path check: delta flow_raw@20261111 vs curve flow k=10
    same=0
    for p in Path('results/s3_delta/tasks').glob('*.json'):
        r=json.loads(p.read_text())['row']; c=json.loads(Path(f"results/s3_curve/tasks/{r['target']}_{r['seed']}_k10.json").read_text())['row']
        same+=r['scores']['flow_raw@20261111']==c['scores']['flow'] and r['scores']['real_raw']==c['scores']['real']
    print('delta vs curve k10 trung khit:',same,'/39')
    with ProcessPoolExecutor(8) as p:
        xr=list(p.map(xjtu,[(t,s) for t in LABEL for s in D.SEEDS]))
        ur=list(p.map(uored,[(t,s,m) for m in UO.BUDGETS for t in UO.NAMES for s in UO.SEEDS]))
    # XJTU merge
    rows=[json.loads(p.read_text())['row'] for p in sorted(Path('results/s3_delta/tasks').glob('*.json'))]
    d={(r['target'],r['seed']):r for r in xr}
    for r in rows: r['scores']['dup_raw']=d[(r['target'],r['seed'])]['scores']['dup_raw']
    lab={r['target']:r['label'] for r in rows}
    def bs(name):
        keys=[name] if '@' in name or not name.startswith('flow') else [f'{name}@{o}' for o in D.OFFSETS]
        return {n:np.mean([D.terminal(rows,k)[3][(n,lab[n])] for k in keys]) for n in lab}
    rng=np.random.default_rng(1); G={c:[n for n in lab if lab[n]==c] for c in (1,2,4)}
    def comp(a,b,cl=(1,2,4)):
        A,B=bs(a),bs(b); f=lambda ns: np.mean([np.mean([A[n]-B[n] for n in ns if lab[n]==c]) for c in cl])
        v=[f([x for g in G.values() for x in rng.choice(g,len(g))]) for _ in range(5000)]
        return f(list(lab)),np.percentile(v,2.5),np.percentile(v,97.5)
    m,cls,hf,_=D.terminal(rows,'dup_raw'); print('XJTU dup_raw: macro %.2f cach %.2f gan_loi_khoe %.2f'%(m*100,cls[4]*100,hf*100))
    for a,b in (('dup_raw','real_raw'),('flow_raw','dup_raw')):
        x=comp(a,b); print(f'XJTU {a} - {b}: {x[0]*100:+.2f} [{x[1]*100:+.2f}; {x[2]*100:+.2f}]')
    # UORED merge
    urows=[json.loads(p.read_text())['row'] for p in sorted(Path('results/s3_uored/tasks').glob('*.json'))]
    du={(r['target'],r['seed'],r['budget']):r for r in ur}
    for r in urows: r['scores']['dup_raw@0']=du[(r['target'],r['seed'],r['budget'])]['scores']['dup_raw@0']
    G2={c:[n for n in UO.U.LAB if UO.CODE[UO.U.LAB[n]]==c] for c in (1,2,3,4)}
    for mm in UO.BUDGETS:
        sub=[r for r in urows if r['budget']==mm]
        B={k:UO.per_bearing(sub,k,'severe') for k in ('real_raw','dup_raw@0','flow_raw')}
        def c2(a,b):
            f=lambda ns: np.mean([np.mean([B[a][n]-B[b][n] for n in ns if UO.CODE[UO.U.LAB[n]]==c]) for c in (1,2,3,4)])
            v=[f([x for g in G2.values() for x in rng.choice(g,len(g))]) for _ in range(5000)]
            return f(list(UO.U.LAB))*100,np.percentile(v,2.5)*100,np.percentile(v,97.5)*100
        hf=np.mean([np.mean(np.asarray(r['scores']['dup_raw@0']['hold'])>0) for r in sub])
        print(f"UORED m={mm}: real {UO.macro(B['real_raw'])*100:.1f} dup {UO.macro(B['dup_raw@0'])*100:.1f} flow {UO.macro(B['flow_raw'])*100:.1f} | dup-real %+.1f [%+.1f;%+.1f] | flow-dup %+.1f [%+.1f;%+.1f] | dup gan loi khoe %.1f"%(*c2('dup_raw@0','real_raw'),*c2('flow_raw','dup_raw@0'),hf*100))
