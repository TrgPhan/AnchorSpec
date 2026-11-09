"""Train-only waveform PCA prototypes: conditional linear flow matching and DDPM."""
import time
import numpy as np
import torch
from torch import nn
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from cheap_sensor import CheapSensor,output_stage


class WaveCodec:
    def fit(self,waves,components=32):
        x=np.asarray(waves,float)
        if x.ndim!=2 or len(x)<3 or not np.isfinite(x).all():raise ValueError('Invalid training waves')
        x=x-x.mean(1,keepdims=True);rms=np.sqrt(np.mean(x*x,axis=1))
        if np.any(rms<=1e-12):raise ValueError('Flat training waveform')
        self.pca=PCA(n_components=min(components,len(x)-1,x.shape[1]),svd_solver='randomized',random_state=20261106)
        coefficients=self.pca.fit_transform(x/rms[:,None])
        raw=np.column_stack((coefficients,np.log(rms)))
        self.scaler=StandardScaler().fit(raw);z=self.scaler.transform(raw)
        self.lo=z.min(0);self.hi=z.max(0)
        reconstruction=self.pca.inverse_transform(coefficients)*rms[:,None]
        self.diagnostics=dict(explained_variance=float(self.pca.explained_variance_ratio_.sum()),
            relative_reconstruction_l2=float(np.linalg.norm(x-reconstruction)/np.linalg.norm(x)),
            dimensions=z.shape[1],training_waveforms=len(x))
        self.train_z=z.astype(np.float32)
        return self

    def decode(self,z):
        z=np.asarray(z,float)
        if z.ndim!=2 or z.shape[1]!=len(self.lo) or not np.isfinite(z).all():raise ValueError('Invalid latent')
        clipped=np.clip(z,self.lo,self.hi);raw=self.scaler.inverse_transform(clipped)
        waves=self.pca.inverse_transform(raw[:,:-1])*np.exp(raw[:,-1,None])
        info=dict(latent_clamp_fraction=float((z!=clipped).mean()),sensor_clip_fraction=float((np.abs(waves)>=8).mean()))
        return output_stage(waves,CheapSensor()),info


class Network(nn.Module):
    def __init__(self,dimensions,conditions):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(dimensions+conditions+16,128),nn.SiLU(),
            nn.Linear(128,128),nn.SiLU(),nn.Linear(128,128),nn.SiLU(),nn.Linear(128,dimensions))

    def forward(self,x,t,c):
        frequencies=2**torch.arange(8,dtype=x.dtype,device=x.device)*torch.pi
        phase=t[:,None]*frequencies
        return self.net(torch.cat((x,c,phase.sin(),phase.cos()),dim=1))


def schedule(steps=100):
    t=torch.linspace(0,1,steps+1,dtype=torch.float64)
    cumulative=torch.cos((t+.008)/1.008*torch.pi/2).square()
    cumulative=cumulative/cumulative[0]
    beta=(1-cumulative[1:]/cumulative[:-1]).clamp(.00001,.999).float()
    return beta,torch.cumprod(1-beta,0)


class LatentGenerator:
    def __init__(self,kind,seed=11,steps=1500):
        if kind not in ('flow','diffusion'):raise ValueError('Unknown generative objective')
        self.kind,self.seed,self.steps=kind,seed,steps

    def fit(self,z,conditions,weights):
        start=time.perf_counter();torch.set_num_threads(1);torch.manual_seed(self.seed)
        torch.use_deterministic_algorithms(True)
        x=torch.tensor(z,dtype=torch.float32);c=torch.tensor(conditions,dtype=torch.float32)
        w=torch.tensor(weights,dtype=torch.float32)
        if len(x)!=len(c) or w.shape!=(len(x),) or not torch.isfinite(x).all() or not torch.isfinite(c).all() or not torch.isfinite(w).all() or torch.any(w<=0):raise ValueError('Invalid training data')
        self.model=Network(x.shape[1],c.shape[1]);optimizer=torch.optim.Adam(self.model.parameters(),lr=1e-3)
        self.beta,self.bar=schedule();self.losses=[]
        self.lo=x.min(0).values;self.hi=x.max(0).values
        for step in range(self.steps):
            idx=torch.multinomial(w,32,replacement=True);clean=x[idx];condition=c[idx];noise=torch.randn_like(clean)
            if self.kind=='flow':
                t=torch.rand(len(idx));xt=(1-t[:,None])*noise+t[:,None]*clean
                target=clean-noise
            else:
                indices=torch.randint(100,(len(idx),));a=self.bar[indices,None]
                xt=a.sqrt()*clean+(1-a).sqrt()*noise;t=indices.float()/99;target=noise
            loss=(self.model(xt,t,condition)-target).square().mean()
            if not torch.isfinite(loss):raise ValueError('Non-finite generative loss')
            optimizer.zero_grad();loss.backward();nn.utils.clip_grad_norm_(self.model.parameters(),1.);optimizer.step()
            if step==0 or (step+1)%250==0 or step==self.steps-1:self.losses.append(dict(step=step+1,loss=float(loss.detach())))
        self.model.eval();self.training_seconds=time.perf_counter()-start
        return self

    @torch.no_grad()
    def sample(self,conditions,seed):
        torch.manual_seed(seed);c=torch.tensor(conditions,dtype=torch.float32);x=torch.randn(len(c),len(self.lo))
        if self.kind=='flow':
            for i in range(50):x=x+self.model(x,torch.full((len(x),),i/50),c)/50
        else:
            for i in range(99,-1,-1):
                b=self.beta[i];a=self.bar[i];aprev=self.bar[i-1] if i else torch.tensor(1.)
                eps=self.model(x,torch.full((len(x),),i/99),c)
                clean=(x-(1-a).sqrt()*eps)/a.sqrt();clean=clean.clamp(self.lo,self.hi)
                x=b*aprev.sqrt()/(1-a)*clean+(1-b).sqrt()*(1-aprev)/(1-a)*x
                if i:x=x+(b*(1-aprev)/(1-a)).sqrt()*torch.randn_like(x)
        if not torch.isfinite(x).all():raise ValueError('Non-finite generated latent')
        return x.numpy()
