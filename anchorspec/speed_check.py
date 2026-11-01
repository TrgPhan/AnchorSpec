"""Kiểm tra bộ ước lượng tốc độ từ phổ rung. Khám phá; không dùng dữ liệu test."""
import sys,numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scipy import signal,stats
import warnings
from cheap_sensor import CheapSensor,simulate
import tn2b_xjtu as X
s=CheapSensor()
def spec(x,fs):
    n=len(x);return np.abs(np.fft.rfft((x-x.mean())*signal.get_window('hann',n))),np.fft.rfftfreq(n,1/fs)
def scan(sp,f,fr0,tol,H=3,local=True):
    c=np.arange(fr0*(1-tol),fr0*(1+tol),.02)
    sc=[]
    for v in c:
        t=0
        for h in range(1,H+1):
            a=np.interp(v*h,f,sp)
            t+=a/np.median(sp[(f>v*h-5)&(f<v*h+5)]+1e-15) if local else a
        sc.append(t)
    return c[int(np.argmax(sc))]
def est(x,fs,fr0,mode):
    if mode=='V0 ±10% goc':sp,f=spec(x,fs);return scan(sp,f,fr0,.1)
    if mode=='V1 ±3% nen cuc bo':sp,f=spec(x,fs);return scan(sp,f,fr0,.03)
    if mode=='V2 ±3% bien do tho':sp,f=spec(x,fs);return scan(sp,f,fr0,.03,local=False)
    if mode=='V3 ±3% bao hinh':
        e=np.abs(signal.hilbert(x-x.mean()));sp,f=spec(e,fs);return scan(sp,f,fr0,.03,local=False)
modes=['V0 ±10% goc','V1 ±3% nen cuc bo','V2 ±3% bien do tho','V3 ±3% bao hinh']
res={m:[] for m in modes}
for code in ['K001','K002','K003','K004']:
    a=np.load(Path(__file__).resolve().parent.parent/'data'/'paderborn'/'cache'/f'{code}.npz')
    for i,v in enumerate(a['vib']):
        y=simulate(v.astype(float)/9.81,64000,s,np.random.default_rng([i,1]))
        for m in modes: res[m].append(abs(est(y,4000,25.,m)-a['speed'][i]/60)/(a['speed'][i]/60)*100)
print('Paderborn K001-K004, 80 ban ghi 4 s, so kenh speed')
for m in modes: print(' ',m,'trung vi %.2f%%  p90 %.2f%%  max %.2f%%'%(np.median(res[m]),np.quantile(res[m],.9),max(res[m])))
res={m:[] for m in modes}
for n in ['1_1','2_2','3_1']:
    x=X.load(n)[:30,0]
    fr=X.fr_of(n)
    for w in x:
        for m in modes: res[m].append(abs(est(w.astype(float),4000,fr,m)-fr)/fr*100)
print('XJTU nen 3 o, cua so 1 s, so toc do danh dinh')
for m in modes: print(' ',m,'trung vi %.2f%%  p90 %.2f%%  max %.2f%%'%(np.median(res[m]),np.quantile(res[m],.9),max(res[m])))
print('V1 lay trung vi theo K ban ghi lien tiep (Paderborn K001-K004)')
for K in (1,5,10,20):
    errs=[]
    for code in ['K001','K002','K003','K004']:
        a=np.load(Path(__file__).resolve().parent.parent/'data'/'paderborn'/'cache'/f'{code}.npz')
        e=[est(simulate(v.astype(float)/9.81,64000,s,np.random.default_rng([i,1])),4000,25.,'V1 ±3% nen cuc bo') for i,v in enumerate(a['vib'])]
        tr=a['speed']/60
        for j in range(0,20-K+1,K):
            errs.append(abs(np.median(e[j:j+K])-tr[j:j+K].mean())/tr[j:j+K].mean()*100)
    print(' K=%d n=%d trung vi %.2f%% p90 %.2f%% max %.2f%%'%(K,len(errs),np.median(errs),np.quantile(errs,.9),max(errs)))
