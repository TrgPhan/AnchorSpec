"""Small conditional GAN/DDPM prototypes; NOT TimeGAN or paper reproductions."""
import os
# Must be configured before the first CUDA context, including direct CLI/tests.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import numpy as np
import torch
from torch import nn
from generators import LABELS, N, rms


def cosine_schedule(steps=128):
    """Cosine cumulative noise schedule with near-normal terminal marginal."""
    if steps < 2:
        raise ValueError("At least two diffusion steps required")
    t = torch.linspace(0, 1, steps + 1, dtype=torch.float64)
    bar = torch.cos((t + .008) / 1.008 * np.pi / 2).square()
    bar = bar / bar[0]
    return (1 - bar[1:] / bar[:-1]).clamp(max=.999).float()


class Decoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(35, 32 * 128)
        self.net = nn.Sequential(
            nn.ConvTranspose1d(32, 24, 4, 2, 1), nn.LeakyReLU(.2),
            nn.ConvTranspose1d(24, 16, 4, 2, 1), nn.LeakyReLU(.2),
            nn.ConvTranspose1d(16, 8, 4, 2, 1), nn.LeakyReLU(.2),
            nn.ConvTranspose1d(8, 1, 4, 2, 1))

    def forward(self, z, c):
        return self.net(self.fc(torch.cat([z, c], 1)).view(-1, 32, 128))


class Discriminator(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Conv1d(4, 8, 9, 4, 4), nn.LeakyReLU(.2),
            nn.Conv1d(8, 16, 9, 4, 4), nn.LeakyReLU(.2),
            nn.Conv1d(16, 32, 9, 4, 4), nn.LeakyReLU(.2),
            nn.AdaptiveAvgPool1d(1), nn.Flatten(), nn.Linear(32, 1))

    def forward(self, x, c):
        return self.net(torch.cat([x, c[:, :, None].expand(-1, -1, N)], 1))


class ResidualBlock(nn.Module):
    def __init__(self, channels, dilation=1):
        super().__init__()
        self.net = nn.Sequential(nn.GroupNorm(4, channels), nn.SiLU(),
            nn.Conv1d(channels, channels, 5, padding=2*dilation, dilation=dilation),
            nn.GroupNorm(4, channels), nn.SiLU(), nn.Conv1d(channels, channels, 3, padding=1))
        self.condition = nn.Linear(64, channels)

    def forward(self, x, context):
        return x + self.net(x + self.condition(context)[:, :, None])


class Denoiser(nn.Module):
    def __init__(self):
        super().__init__()
        self.context = nn.Sequential(nn.Linear(19, 64), nn.SiLU(), nn.Linear(64, 64))
        self.input = nn.Conv1d(1, 16, 5, padding=2)
        channels = (16, 24, 32, 48, 64)
        self.down = nn.ModuleList([nn.Conv1d(a, b, 4, 2, 1) for a, b in zip(channels[:-1], channels[1:])])
        self.enc = nn.ModuleList([ResidualBlock(c) for c in channels[:-1]])
        self.bottom = nn.ModuleList([ResidualBlock(64, d) for d in (1, 2, 4, 8)])
        self.up = nn.ModuleList([nn.Conv1d(a+b, b, 3, padding=1) for a, b in zip(channels[:0:-1], channels[-2::-1])])
        self.dec = nn.ModuleList([ResidualBlock(c) for c in channels[-2::-1]])
        self.output = nn.Sequential(nn.GroupNorm(4, 16), nn.SiLU(), nn.Conv1d(16, 1, 3, padding=1))

    def forward(self, x, c, t):
        freq = 2 ** torch.arange(8, device=x.device, dtype=x.dtype) * np.pi
        time = t[:, None] * freq[None]
        context = self.context(torch.cat([c, time.sin(), time.cos()], 1))
        x = self.input(x)
        skips = []
        for block, down in zip(self.enc, self.down):
            x = block(x, context)
            skips.append(x)
            x = down(x)
        for block in self.bottom:
            x = block(x, context)
        for up, block, skip in zip(self.up, self.dec, reversed(skips)):
            x = nn.functional.interpolate(x, size=skip.shape[-1], mode='nearest')
            x = block(up(torch.cat([x, skip], 1)), context)
        return self.output(x)


class DeepGenerator:
    def __init__(self, method, anchors, seed, steps=300, device=None, progress=False):
        if method not in ("gan_prototype", "ddpm_prototype") or steps < 1:
            raise ValueError("Unknown deep method or nonpositive training steps")
        self.method = method
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        torch.manual_seed(seed)
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        self.scales = {label: float(np.median(rms(anchors[label]))) for label in LABELS}
        self.support = {label: float(np.max(np.abs(anchors[label])) / self.scales[label]) for label in LABELS}
        x = np.concatenate([anchors[label] / self.scales[label] for label in LABELS])
        y = np.repeat(np.arange(3), [len(anchors[label]) for label in LABELS])
        data = torch.tensor(x[:, None, :], dtype=torch.float32, device=self.device)
        labels = torch.nn.functional.one_hot(torch.tensor(y, device=self.device), 3).float()
        losses = []
        if method == "gan_prototype":
            self.model = Decoder().to(self.device)
            critic = Discriminator().to(self.device)
            opt = torch.optim.Adam(self.model.parameters(), lr=2e-4, betas=(.5, .9))
            dopt = torch.optim.Adam(critic.parameters(), lr=2e-4, betas=(.5, .9))
            criterion = nn.BCEWithLogitsLoss()
            for step in range(steps):
                idx = torch.randint(len(data), (16,), device=self.device)
                real, c = data[idx], labels[idx]
                fake = self.model(torch.randn(16, 32, device=self.device), c)
                dloss = criterion(critic(real, c), torch.ones(16, 1, device=self.device))
                dloss += criterion(critic(fake.detach(), c), torch.zeros(16, 1, device=self.device))
                dopt.zero_grad(); dloss.backward(); dopt.step()
                gloss = criterion(critic(fake, c), torch.ones(16, 1, device=self.device))
                opt.zero_grad(); gloss.backward(); opt.step()
                if step % 50 == 0 or step == steps - 1:
                    losses.append({"step": step, "g": float(gloss.detach()), "d": float(dloss.detach())})
        elif method == "ddpm_prototype":
            self.model = Denoiser().to(self.device)
            self.beta = cosine_schedule().to(self.device)
            self.alpha = 1 - self.beta
            self.bar = self.alpha.cumprod(0)
            opt = torch.optim.Adam(self.model.parameters(), lr=1e-3)
            for step in range(steps):
                idx = torch.randint(len(data), (16,), device=self.device)
                real, c = data[idx], labels[idx]
                ts = torch.randint(len(self.beta), (16,), device=self.device)
                noise = torch.randn_like(real)
                a = self.bar[ts, None, None]
                noisy = a.sqrt() * real + (1 - a).sqrt() * noise
                loss = (self.model(noisy, c, ts / (len(self.beta) - 1)) - noise).square().mean()
                opt.zero_grad(); loss.backward(); opt.step()
                if step % 50 == 0 or step == steps - 1:
                    losses.append({"step": step, "noise_mse": float(loss.detach())})
                    if progress:
                        print('DDPM',seed,str(self.device),'step',step,'loss',losses[-1]['noise_mse'],flush=True)
        else:
            raise ValueError(method)
        self.model.eval()
        self.fit_log = {"steps": steps, "device": str(self.device), "losses": losses,
                        "scope": "small original prototype, not original paper model"}
        if method == "ddpm_prototype":
            self.fit_log.update(diffusion_steps=len(self.beta), schedule="cosine",
                                terminal_alpha_bar=float(self.bar[-1].cpu()),
                                denoiser="four-level residual 1D U-Net, dilated bottleneck, sinusoidal time embedding",
                                sampler="DDPM posterior mean/variance; x0 clipped to train-only class support",
                                train_support=self.support,
                                limitation="original model, not Thompson/TimeGAN/few-shot paper reproduction")

    @torch.no_grad()
    def sample(self, label, count, seed):
        if label not in LABELS or count < 1:
            raise ValueError("Known label and positive count required")
        torch.manual_seed(seed)
        generated = []
        for start in range(0, count, 32):
            b = min(32, count - start)
            c = torch.zeros(b, 3, device=self.device)
            c[:, LABELS.index(label)] = 1
            if self.method == "gan_prototype":
                x = self.model(torch.randn(b, 32, device=self.device), c)
            else:
                x = torch.randn(b, 1, N, device=self.device)
                for t in reversed(range(len(self.beta))):
                    noise = self.model(x, c, torch.full((b,), t / (len(self.beta) - 1), device=self.device))
                    x0 = (x - (1 - self.bar[t]).sqrt() * noise) / self.bar[t].sqrt()
                    x0 = x0.clamp(-self.support[label], self.support[label])
                    previous = self.bar[t - 1] if t else torch.ones((), device=self.device)
                    x = (self.beta[t] * previous.sqrt() * x0 +
                         self.alpha[t].sqrt() * (1 - previous) * x) / (1 - self.bar[t])
                    if t:
                        variance = self.beta[t] * (1 - self.bar[t - 1]) / (1 - self.bar[t])
                        x += variance.sqrt() * torch.randn_like(x)
            generated.append(x[:, 0].cpu().numpy() * self.scales[label])
        provenance = [{"method": self.method, "label": label, "seed": seed,
                       "sample_index": i, "training_steps": self.fit_log['steps'],
                       "sampler": self.fit_log.get('sampler', 'conditional GAN')} for i in range(count)]
        return np.concatenate(generated).astype(np.float32), provenance