"""Small CPU generators learn spectral changes around measured fault anchors."""
import time
import numpy as np
import torch
from torch import nn
from sklearn.preprocessing import StandardScaler
from s_latent import schedule


class SpectralResidual:
    def __init__(self, samples=4000, fs=4000, bands=24):
        self.samples,self.fs,self.bands=samples,fs,bands
        self.freq=np.fft.rfftfreq(samples,1/fs)
        self.edges=np.linspace(0,1000,bands+1)
        self.centers=(self.edges[:-1]+self.edges[1:])/2
        self.masks=[(self.freq>=lo)&(self.freq<hi)&(self.freq>0)
                    for lo,hi in zip(self.edges[:-1],self.edges[1:])]
        if not all(m.any() for m in self.masks):raise ValueError('Empty spectral band')
        self.interpolation=np.stack([np.interp(self.freq,np.r_[0,self.centers,1000,self.fs/2],
            np.r_[np.eye(bands)[j,0],np.eye(bands)[j],0,0]) for j in range(bands)])

    def describe(self,waves):
        x=np.asarray(waves,float)
        if x.ndim!=2 or x.shape[1]!=self.samples or not np.isfinite(x).all():raise ValueError('Invalid waves')
        power=np.abs(np.fft.rfft(x-x.mean(1,keepdims=True),axis=1))**2/self.samples**2
        return np.column_stack([.5*np.log(power[:,m].mean(1)+1e-15) for m in self.masks])

    def fit(self,waves,groups,conditions):
        self.description=self.describe(waves)
        groups=np.asarray(groups)
        if len(groups)!=len(waves) or len(conditions)!=len(waves):raise ValueError('Invalid lineage')
        self.condition_scaler=StandardScaler().fit(np.column_stack((self.description,conditions)))
        self.conditions=self.condition_scaler.transform(np.column_stack((self.description,conditions))).astype(np.float32)
        self.pairs=np.array([(i,j) for i in range(len(waves)) for j in range(len(waves)) if i!=j and groups[i]==groups[j]])
        self.residuals=self.description[self.pairs[:,1]]-self.description[self.pairs[:,0]]
        self.scale=np.maximum(self.residuals.std(0),.05)
        self.z=(self.residuals/self.scale).astype(np.float32)
        self.lo=np.maximum(np.quantile(self.residuals,.02,axis=0),-np.log(2))
        self.hi=np.minimum(np.quantile(self.residuals,.98,axis=0),np.log(2))
        return self

    def apply(self,anchors,residuals,strength,peak_limits):
        x=np.asarray(anchors,float);r=np.asarray(residuals,float)
        if r.shape!=(len(x),self.bands) or not np.isfinite(r).all():raise ValueError('Invalid residual')
        if not np.isfinite(x).all() or strength<0 or strength>1:raise ValueError('Invalid anchor or strength')
        bounded=np.clip(r,self.lo,self.hi)*strength
        gains=np.exp(bounded@self.interpolation)
        y=np.fft.irfft(np.fft.rfft(x,axis=1)*gains,n=self.samples,axis=1)
        y-=y.mean(1,keepdims=True)
        limits=np.asarray(peak_limits,float)
        if limits.shape!=(len(x),) or np.any(limits<=0):raise ValueError('Invalid peak limits')
        scale=np.minimum(1,limits/(np.abs(y).max(1)+1e-15));y*=scale[:,None]
        return y,dict(residual_clamp_fraction=float((r!=np.clip(r,self.lo,self.hi)).mean()),
                      peak_rescale_fraction=float((scale<1-1e-12).mean()))


class SmallNetwork(nn.Module):
    def __init__(self,dimensions,conditions):
        super().__init__()
        self.register_buffer('frequencies',2**torch.arange(4,dtype=torch.float32)*torch.pi)
        self.net=nn.Sequential(nn.Linear(dimensions+conditions+8,64),nn.SiLU(),
                               nn.Linear(64,64),nn.SiLU(),nn.Linear(64,dimensions))

    def forward(self,x,t,c):
        phase=t[:,None]*self.frequencies
        return self.net(torch.cat((x,c,phase.sin(),phase.cos()),1))


class ResidualGenerator:
    def __init__(self,kind,seed=11,steps=2000):
        if kind not in ('flow','diffusion'):raise ValueError('Unknown objective')
        self.kind,self.seed,self.steps=kind,seed,steps

    def fit(self,z,conditions,weights):
        torch.set_num_threads(1);torch.manual_seed(self.seed);torch.use_deterministic_algorithms(True)
        start=time.perf_counter();x=torch.as_tensor(z,dtype=torch.float32)
        c=torch.as_tensor(conditions,dtype=torch.float32);w=torch.as_tensor(weights,dtype=torch.float32)
        if len(x)!=len(c) or w.shape!=(len(x),) or not torch.isfinite(x).all() or not torch.isfinite(c).all() or not torch.isfinite(w).all() or torch.any(w<=0):raise ValueError('Invalid training arrays')
        self.model=SmallNetwork(x.shape[1],c.shape[1]);self.beta,self.bar=schedule()
        self.lo=x.min(0).values;self.hi=x.max(0).values;self.losses=[]
        optimizer=torch.optim.Adam(self.model.parameters(),lr=1e-3)
        for step in range(self.steps):
            ix=torch.multinomial(w,64,replacement=True);clean=x[ix];noise=torch.randn_like(clean)
            if self.kind=='flow':
                t=torch.rand(len(ix));xt=(1-t[:,None])*noise+t[:,None]*clean;target=clean-noise
            else:
                indices=torch.randint(100,(len(ix),));a=self.bar[indices,None]
                xt=a.sqrt()*clean+(1-a).sqrt()*noise;t=indices.float()/99
                target=a.sqrt()*noise-(1-a).sqrt()*clean
            loss=(self.model(xt,t,c[ix])-target).square().mean()
            if not torch.isfinite(loss):raise ValueError('Non-finite loss')
            optimizer.zero_grad();loss.backward();nn.utils.clip_grad_norm_(self.model.parameters(),1.);optimizer.step()
            if step==0 or (step+1)%250==0 or step==self.steps-1:self.losses.append(dict(step=step+1,loss=float(loss.detach())))
        self.model.eval();self.training_seconds=time.perf_counter()-start
        return self

    @torch.inference_mode()
    def sample(self,conditions,seed,evaluations=16):
        if evaluations<2 or evaluations>100:raise ValueError('Unsupported step count')
        torch.manual_seed(seed);c=torch.as_tensor(conditions,dtype=torch.float32)
        x=torch.randn(len(c),len(self.lo))
        if self.kind=='flow':
            for i in range(evaluations):x+=self.model(x,torch.full((len(x),),i/evaluations),c)/evaluations
        else:
            grid=np.linspace(99,0,evaluations).round().astype(int)
            for k,i in enumerate(grid):
                a=self.bar[i];ap=self.bar[grid[k+1]] if k+1<len(grid) else torch.tensor(1.)
                v=self.model(x,torch.full((len(x),),i/99),c)
                clean=(a.sqrt()*x-(1-a).sqrt()*v).clamp(self.lo,self.hi)
                noise=(x-a.sqrt()*clean)/(1-a).sqrt()
                x=ap.sqrt()*clean+(1-ap).sqrt()*noise
        if not torch.isfinite(x).all():raise ValueError('Non-finite generated residual')
        return x.numpy()
