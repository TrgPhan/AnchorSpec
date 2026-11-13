"""Sim-to-real flow matching (S2R): a conditional flow (Truong's S3 SmallNetwork, flow-matching objective) transports the
distribution of PHYSICS-SIMULATED feature deltas to the distribution of REAL fault feature deltas (per class, inner/outer),
learned on library machines where both exist. On the target machine, physics samples are pushed through the flow."""
import numpy as np
import torch
from torch import nn
from s3_spectral import SmallNetwork
import funnel as Fu
import router_common as R
from flowfeat import source_healthy_f

SIM_PER_EVENT = 30


class TransportFlow:
    def __init__(self, x0, x1, c0, c1, seed, steps=2000):
        torch.set_num_threads(1); torch.manual_seed(seed); torch.use_deterministic_algorithms(True)
        self.mu = np.concatenate([x0, x1]).mean(0); self.sd = np.maximum(np.concatenate([x0, x1]).std(0), 1e-6)
        z0 = torch.as_tensor((x0 - self.mu) / self.sd, dtype=torch.float32); z1 = torch.as_tensor((x1 - self.mu) / self.sd, dtype=torch.float32)
        oh = lambda c: torch.as_tensor(np.eye(2)[np.asarray(c) - 1], dtype=torch.float32)
        k0, k1 = oh(c0), oh(c1); c0, c1 = np.asarray(c0), np.asarray(c1)
        self.net = SmallNetwork(x0.shape[1], 2); opt = torch.optim.Adam(self.net.parameters(), lr=1e-3)
        g = torch.Generator().manual_seed(seed)
        for _ in range(steps):
            cls = 1 + int(torch.randint(2, (1,), generator=g)) if len(set(c0)) > 1 else int(c0[0])
            i0 = torch.as_tensor(np.flatnonzero(c0 == cls)); i1 = torch.as_tensor(np.flatnonzero(c1 == cls))
            a = z0[i0[torch.randint(len(i0), (64,), generator=g)]]; b = z1[i1[torch.randint(len(i1), (64,), generator=g)]]
            t = torch.rand(64, generator=g); xt = (1 - t[:, None]) * a + t[:, None] * b
            cond = k0[i0[:1]].repeat(64, 1)
            loss = (self.net(xt, t, cond) - (b - a)).square().mean()
            opt.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(self.net.parameters(), 1.); opt.step()
        self.net.eval(); self.oh = oh

    @torch.inference_mode()
    def push(self, x0, c, evaluations=16):
        x = torch.as_tensor((x0 - self.mu) / self.sd, dtype=torch.float32); cond = self.oh(np.full(len(x), c))
        for i in range(evaluations):
            x = x + self.net(x, torch.full((len(x),), i / evaluations), cond) / evaluations
        return x.numpy() * self.sd + self.mu


def library_pairs(ds, target, seed, lib):
    """Real and simulated feature deltas on the library machines (inner/outer only)."""
    X0, C0, X1, C1 = [], [], [], []
    rng = np.random.default_rng([seed, 5150, sum(map(ord, str(target)))])
    for c, kind in ((1, 'inner'), (2, 'outer')):
        for k in lib.get(c, []):
            rec = R.record(ds, k); hf = source_healthy_f(ds, k, seed); hw, hfr = R.source_healthy(ds, k, seed)
            X1.append(rec['donor_f'] - hf.mean(0)); C1 += [c] * len(rec['donor_f'])
            sim = Fu.injected(np.asarray(hw)[:, None, :], kind, SIM_PER_EVENT, hfr, rec['feat_orders'], R.SENSOR, 4000, rng)
            X0.append(Fu.feats(sim, 4000, hfr, rec['feat_orders']) - hf.mean(0)); C0 += [c] * SIM_PER_EVENT
    return np.concatenate(X0), np.asarray(C0), np.concatenate(X1), np.asarray(C1)


def s2r_rows(ds, target, seed, lib, inj_f):
    X0, C0, X1, C1 = library_pairs(ds, target, seed, lib)
    tf = TransportFlow(X0, X1, C0, C1, seed)
    hmean = R.target_healthy(ds, target, seed)['healthy_f'].mean(0)
    rows = {c: inj_f[c] + (tf.push(inj_f[c] - hmean, c) - (inj_f[c] - hmean)) for c in (1, 2)}
    # control: transplant real library deltas onto the target canvas (no flow)
    rng = np.random.default_rng([seed, 6160]); h = R.target_healthy(ds, target, seed)['healthy_f']
    ctrl = {c: h[rng.integers(len(h), size=150)] + X1[C1 == c][rng.integers((C1 == c).sum(), size=150)] for c in (1, 2)}
    return rows, ctrl
