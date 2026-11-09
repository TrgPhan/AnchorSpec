"""Frozen public-data pilots. No row-shuffle accuracy or factory claims."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal, stats
from scipy.io import loadmat
from sklearn.covariance import LedoitWolf
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import recall_score, confusion_matrix

from cheap_sensor import CheapSensor, simulate
from funnel import SMALL

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent/'data'/'open_sources'
OUT = ROOT/'results'/'z'


def provenance():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            for name in ('z_screen.py','z_open_data.py','PROTOCOL_Z_PUBLIC.md','cheap_sensor.py')}


def blocked_split(labels):
    train, gap, test = [], [], []
    for label in np.unique(labels):
        indices = np.flatnonzero(labels == label)
        a, b = int(.6*len(indices)), int(.8*len(indices))
        train.extend(indices[:a]); gap.extend(indices[a:b]); test.extend(indices[b:])
    return np.asarray(train), np.asarray(gap), np.asarray(test)


def table_pilot():
    source = DATA/'7589904'/'bearing_vibration_metrics.csv'
    df = pd.read_csv(source)
    y = df['Bearing State'].to_numpy()
    train, gap, test = blocked_split(y)
    result = {'source':'https://zenodo.org/records/7589904', 'code_sha256':provenance(),
        'file_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'rows':len(df), 'classes':{str(k):int(v) for k,v in df['Bearing State'].value_counts().items()},
        'missing':{k:int(v) for k,v in df.isna().sum().items()},
        'label_transitions_in_row_order':int(np.sum(y[1:] != y[:-1])),
        'split':{'train':train.tolist(),'gap':gap.tolist(),'test':test.tolist()},
        'event_ids_available':False, 'chronology_verified':False,
        'seal_status_confounded_with_label':True, 'models':{}}
    groups = {'vibration':['V-RMS','a-RMS','a-Peak','Crest'],
              'vibration_temperature':['V-RMS','a-RMS','a-Peak','Crest','Temperature']}
    for name, columns in groups.items():
        x = df[columns].to_numpy(float)
        if not np.isfinite(x).all(): raise ValueError('Missing/nonfinite values require a new documented preprocessing decision')
        for kind in ('RF50','majority'):
            model = (RandomForestClassifier(random_state=11, **SMALL) if kind == 'RF50'
                     else DummyClassifier(strategy='most_frequent'))
            model.fit(x[train],y[train])
            prediction=model.predict(x[test])
            hashes=pd.util.hash_pandas_object(df[columns],index=False).to_numpy()
            result['models'][f'{name}_{kind}']={'features':columns,
                'macro_recall':float(recall_score(y[test],prediction,average='macro',zero_division=0)),
                'per_class_recall':recall_score(y[test],prediction,labels=[1,2,3],average=None,zero_division=0).tolist(),
                'confusion_matrix':confusion_matrix(y[test],prediction,labels=[1,2,3]).tolist(),
                'test_rows_with_exact_training_feature_match':int(np.isin(hashes[test],hashes[train]).sum())}
    (OUT/'grease_states_pilot.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print('grease states', {m:round(v['macro_recall'],4) for m,v in result['models'].items()},flush=True)


def snapshot_bounds(time):
    # Scan in chunks to avoid a large temporary time-difference vector.
    starts=[0]
    for first in range(0,len(time)-1,1000000):
        end=min(first+1000001,len(time))
        starts.extend((np.flatnonzero(np.diff(time[first:end])>1)+first+1).tolist())
    return list(zip(starts,starts[1:]+[len(time)]))


def snapshot_features(x,fs):
    # One-second non-overlapping windows; leave the first second to settling.
    x=x[fs:len(x)//fs*fs].reshape(-1,fs)
    x=x-x.mean(1,keepdims=True)
    rms=np.sqrt(np.mean(x*x,axis=1))+1e-12
    crest=np.max(np.abs(x),axis=1)/rms
    kurt=stats.kurtosis(x,axis=1,fisher=False)
    f,p=signal.welch(x,fs,nperseg=min(1024,fs),axis=1)
    edges=np.linspace(0,fs/2,7)
    total=p.sum(1)+1e-20
    bands=[np.log((p[:,(f>=a)&(f<b)].sum(1)+1e-20)/total) for a,b in zip(edges[:-1],edges[1:])]
    features=np.column_stack([np.log(rms),np.log(crest),np.log(np.maximum(kurt,.01))]+bands)
    return np.median(features,axis=0)


def baseline_deviation(features):
    if len(features)<13: raise ValueError('Need 5 reference, 5 calibration, and 3 held-out snapshots')
    reference=features[:5]
    mu=reference.mean(0)
    scale=np.maximum(reference.std(0),.05)
    z=(features-mu)/scale
    model=LedoitWolf().fit(z[:5])
    return np.sqrt(np.maximum(model.mahalanobis(z),0)/features.shape[1])


def first_sustained(exceed,start=10,width=3):
    streak=0
    for i in range(start,len(exceed)):
        streak=streak+1 if exceed[i] else 0
        if streak>=width:return i
    return None


def dlr_pilot():
    result={'source':'https://zenodo.org/records/20742913','code_sha256':provenance(),
        'fault_onset_labels_available':False,'rul_model_evaluated':False,
        'all_selected_runs_unlubricated':True,'rows':[]}
    folder=DATA/'20742913'
    for test in (4,6,7,8):
        manifest_path=folder/f'Test_{test}'/'manifest.json'
        manifest=json.loads(manifest_path.read_text())
        for channel in (1,2):
            entry=next(e for e in manifest['members'] if e['member'].endswith(f'_Acc_Sensor_{channel}.mat'))
            path=manifest_path.parent/entry['local_file']
            with path.open('rb') as f:
                if hashlib.file_digest(f,'sha256').hexdigest()!=entry['sha256']: raise ValueError('Local source changed')
            mat=loadmat(path)
            values=[v for k,v in mat.items() if not k.startswith('__') and isinstance(v,np.ndarray)]
            if len(values)!=1 or values[0].shape[1]!=2: raise ValueError('Unexpected MAT schema')
            a=values[0]
            bounds=snapshot_bounds(a[:,0])
            step=float(np.median(np.diff(a[:1000,0])))
            if not np.isclose(step,.0001,rtol=.01): raise ValueError('Unexpected sampling frequency')
            t=[]; native=[]; cheap=[]; clipping=[]
            for index,(s,e) in enumerate(bounds):
                x=np.asarray(a[s:e,1],float)
                if not np.isfinite(x).all(): raise ValueError('Nonfinite vibration')
                t.append(float(a[s,0]))
                clipping.append(float(np.mean(np.abs(x)>=8)))
                native.append(snapshot_features(x,10000))
                reduced=simulate(x,10000,CheapSensor(),np.random.default_rng([test,channel,index,20261103]))
                cheap.append(snapshot_features(reduced,4000))
            for mode,features in (('native',native),('cheap',cheap)):
                features=np.asarray(features)
                scores={'RMS':features[:,0], 'multifeature':baseline_deviation(features)}
                methods={}
                for name,score in scores.items():
                    threshold=float(np.max(score[5:10]))
                    alarm=first_sustained(score>threshold)
                    methods[name]={'score':score.tolist(),'threshold':threshold,
                        'alarm_snapshot':None if alarm is None else alarm+1,
                        'alarm_hours':None if alarm is None else (t[alarm]-t[0])/3600,
                        'post_calibration_exceedance_fraction':float(np.mean(score[10:]>threshold))}
                result['rows'].append({'test':test,'channel':channel,'mode':mode,'n_snapshots':len(t),
                    'source_file':entry['local_file'],'time_hours':((np.asarray(t)-t[0])/3600).tolist(),
                    'raw_fraction_over_8g':clipping,'methods':methods})
            print('DLR',test,channel,'snapshots',len(t),flush=True)
            del a,values,mat
    (OUT/'dlr_monitoring_pilot.json').write_text(json.dumps(result,indent=2),encoding='utf8')


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('tables','dlr'));a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    table_pilot() if a.mode=='tables' else dlr_pilot()


if __name__=='__main__':main()
