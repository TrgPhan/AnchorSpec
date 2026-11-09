"""Frozen new-geometry test using HUST6204 files excluded from V development."""
import argparse
from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor
from functools import lru_cache
import hashlib
import json
import requests
import numpy as np
from scipy.io import loadmat
import v_external as E

DATA=E.ROOT.parent/'data/hust_v6204'
CACHE=E.ROOT.parent/'data/v_hust6204'


def acquire():
    DATA.mkdir(exist_ok=True)
    inventory=json.loads((E.ROOT.parent/'data/hust_v/publisher.json').read_text())
    names={f'{c}40{load}.mat' for c in 'NIO' for load in (0,2,4)}
    selected=[r for r in inventory if r['filename'] in names]
    if len(selected)!=9:raise ValueError('Publisher inventory incomplete')
    def one(row):
        path=DATA/row['filename'];details=row['content_details']
        if not path.exists():
            r=requests.get(details['download_url'],timeout=60);r.raise_for_status();payload=r.content
            if hashlib.sha256(payload).hexdigest()!=details['sha256_hash']:raise ValueError('SHA256 mismatch')
            path.write_bytes(payload)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=details['sha256_hash'] or path.stat().st_size!=row['size']:raise ValueError('Integrity mismatch')
        return dict(name=path.name,sha256=digest,publisher_verified=True,bytes=path.stat().st_size)
    with ThreadPoolExecutor(3) as pool:rows=list(pool.map(one,selected))
    (DATA/'manifest.json').write_text(json.dumps(dict(source='https://data.mendeley.com/datasets/cbv7jyx4p9/3',license='CC BY 4.0',files=rows),indent=2),encoding='utf8')
    print('Verified9 new files',flush=True)


@lru_cache(None)
def signals(dataset,unit):
    out={};meta={};orders=E.Bearing(8,7.6,33.5,0).orders()
    for p in sorted(DATA.glob('*.mat')):
        d=loadmat(p,simplify_cells=True);x=np.asarray(d['data'],float)
        if x.ndim!=1 or len(x)<4*51200:raise ValueError('Unexpected waveform')
        x=x[:512000]/(9.80665 if unit=='mks' else 1.)
        seed=int(hashlib.sha256(p.name.encode()).hexdigest()[:8],16)
        y=E.simulate(x,51200,E.CheapSensor(),np.random.default_rng(seed))
        y=y[4000:24000] if p.stem.startswith('N') else y[4000:]
        w=E.windows(y,4000);w=w-w.mean(1,keepdims=True)
        out[p.stem]=dict(w=w,f=E.Fu.feats(w[:,None,:],4000,float(d['fs']),orders),fr=float(d['fs']),orders=orders)
        meta[p.stem]=dict(native_clip8_fraction=float((np.abs(x)>=8).mean()),windows=len(w))
    return out,meta


def job(task):
    # Reuse frozen generic job with two labels by giving a filtered dict/list view.
    # Its HUST schema expects I/O/B; a dedicated split below prevents phantom B.
    dataset,unit,geometry,source,target,severity,seed=task
    data,meta=signals(dataset,unit);train=[f'{c}40{source}' for c in 'IO'];test=[f'{c}40{target}' for c in 'IO'];hn=f'N40{target}'
    ht=data[hn];real=[];aug=[];lineage=[]
    for name in train:
        item=data[name];hs=data[E.healthy_name('hust',name)]
        rng=np.random.default_rng([seed,int(hashlib.sha256((name+hn+unit).encode()).hexdigest()[:8],16)])
        waves,audit=E.generate(item['w'],hs['w'],ht['w'],item['fr'],ht['fr'],rng)
        feat={m:E.Fu.feats(w[:,None,:],4000,item['fr'] if m=='severity' else ht['fr'],item['orders']) for m,w in waves.items()}
        feat['surrogate']=E.surrogate('hust',unit,name,seed)
        real.append(('NIO'.index(name[0]),item['f']));aug.append(feat)
        lineage.append(dict(donor=name,target_healthy=hn,clipping=audit['clipping']))
    row=dict(unit=unit,source=source,target=target,seed=seed,train=train,test=test,target_healthy=hn,lineage=lineage,scores={})
    for family in E.FAMILIES:
        row['scores'][family]={}
        for method in E.METHODS:
            model=E.FaultModel(family,seed).fit(*E.arrays(ht['f'],real,aug,method));scores={}
            for name in test:
                x=E.Fu.feats(data[name]['w'][:,None,:],4000,ht['fr'],data[name]['orders'])
                pred=E.fault_labels(E.causal_average(model.predict_proba(x)));c='NIO'.index(name[0])
                scores[str(c)]=dict(recall=float((pred==c).mean()),counts=np.bincount(pred.clip(0),minlength=5).tolist())
            row['scores'][family][method]=scores
    return row


E.signals=signals
E.CACHE=CACHE


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('download','run'));a=p.parse_args()
    if a.action=='download':acquire();return
    CACHE.mkdir(exist_ok=True)
    frozen=E.hashes()
    for n in ('v_holdout6204.py','PROTOCOL_V_HOLDOUT6204.md'):frozen[n]=hashlib.sha256((E.ROOT/n).read_bytes()).hexdigest()
    (CACHE/'hashes.json').write_text(json.dumps(frozen),encoding='utf8')
    tasks=[('hust',u,4,s,t,None,seed) for u in ('g','mks') for s in (0,2,4) for t in (0,2,4) if s!=t for seed in (11,29,47)]
    rows=[]
    with ProcessPoolExecutor(3) as pool:
        for i,r in enumerate(pool.map(job,tasks),1):rows.append(r);print('6204',i,'/36',flush=True)
    summary={}
    for unit in ('g','mks'):
        part=[r for r in rows if r['unit']==unit];summary[unit]={}
        for family in E.FAMILIES:
            summary[unit][family]={}
            for method in E.METHODS:
                cls={c:float(np.mean([r['scores'][family][method][c]['recall'] for r in part])) for c in ('1','2')}
                summary[unit][family][method]=dict(macro_recall=float(np.mean(list(cls.values()))),per_class=cls)
            print(unit,family,{m:round(v['macro_recall'],4) for m,v in summary[unit][family].items()},flush=True)
    checks={}
    for unit,families in summary.items():
        methods=families['svm1'];m=methods['transport']
        checks[unit]=dict(beats_controls=all(m['macro_recall']>methods[c]['macro_recall'] for c in ('real','duplicate','surrogate')),
            no_class_harm_over5pp=min(m['per_class'][c]-methods['real']['per_class'][c] for c in ('1','2'))>=-.05)
    (E.OUT/'holdout6204.json').write_text(json.dumps(dict(code_sha256=frozen,rows=rows,summary=summary,checks=checks,independent_bearing_claim=False),indent=2),encoding='utf8')


if __name__=='__main__':main()
