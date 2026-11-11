import sys; sys.path.insert(0,'.')
import json, numpy as np
from concurrent.futures import ProcessPoolExecutor
import s3_curve as C, s3_spectral as SP
orig=SP.ResidualGenerator.sample
def patched(self,cond,seed,evaluations=16): return orig(self,cond,seed-20261111+20261106,evaluations)
def job(t):
    SP.ResidualGenerator.sample=patched; C.ResidualGenerator.sample=patched
    return C.job(t)
if __name__=='__main__':
    tasks=[(t,s,10) for t in C.LABEL for s in C.SEEDS]
    with ProcessPoolExecutor(6) as p: rows=list(p.map(job,tasks))
    for m in ('real','flow'):
        mt=C.metrics(rows,m); print(m,'P %.4f R %.4f A %.4f'%(mt['avg_precision'],mt['avg_recall'],mt['accuracy']))
    old=[json.loads(open(f'results/s3_curve/tasks/{t}_{s}_k10.json').read())['row'] for t,s,_ in tasks]
    same=sum(a['scores']['flow']==b['scores']['flow'] for a,b in zip(rows,old)); print('tasks giong ban curve:',same,'/39')
