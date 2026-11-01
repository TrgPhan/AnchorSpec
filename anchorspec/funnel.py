"""Phễu v1.5, tầng 3: bộ riêng cho từng loại lỗi, có "chưa rõ", đối chiếu vật lý.

Không dùng nhãn thật khi huấn luyện: chỉ nền của chính máy + lỗi cấy tiên nghiệm rộng.
Cột đặc trưng theo features.extract (45 cột mỗi trục).
"""
from dataclasses import dataclass, replace

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from cheap_sensor import fault_path, output_stage
from features import extract
from injection import FS_SIM, Prior, _draw, component, quality_gate

ENV = {'ftf': (31, 34), 'bpfo': (34, 37), 'bpfi': (37, 40)}
KEY = {'inner': 'bpfi', 'outer': 'bpfo', 'cage': 'ftf'}
SMALL = dict(n_estimators=50, max_depth=8, min_samples_leaf=2, max_features='sqrt', bootstrap=False, class_weight='balanced', n_jobs=1)
N_COLS = 45


def inject_multi(bg, kind, fr, orders, sensor, fs, prior, rng, sigma=.5):
    """bg (trục, N). Cùng dạng sóng lỗi, biên độ theo nền từng trục, tỉ lệ ngẫu nhiên giữa trục."""
    n = bg.shape[1]
    raw, _ = component(kind, int(np.ceil(n*FS_SIM/fs))+int(.05*FS_SIM), FS_SIM, fr, orders, prior, rng)
    x = fault_path(raw, FS_SIM, sensor)[-n:]
    x = (x-x.mean())/np.sqrt(np.mean((x-x.mean())**2))
    amp = _draw(rng, prior.amp_rel, log=True)
    return np.stack([output_stage(b+x*amp*np.exp(rng.normal(0, sigma) if i else 0.)*np.sqrt(np.mean(b**2)), sensor) for i, b in enumerate(bg)])


def injected(base, kind, n, fr, orders, sensor, fs, rng, prior=None):
    prior = prior or Prior()
    rows, tries = [], 0
    while len(rows) < n:
        tries += 1
        if tries > 6*n:
            raise RuntimeError(f'Quota {kind}')
        b = base[int(rng.integers(len(base)))]
        y = inject_multi(b, kind, fr, orders, sensor, fs, prior, rng)
        # Nền đã bão hòa sẵn thì không tính bão hòa là lỗi của mẫu cấy; các kiểm tra khác giữ nguyên.
        no_range = replace(sensor, range_g=None, bits=None)
        chk = lambda ax: sensor if np.mean(np.abs(b[ax]) >= (sensor.range_g or np.inf)) <= .001 else no_range
        if all(quality_gate(y[a], b[a], chk(a)) is None for a in range(len(b))):
            rows.append(y)
    return np.array(rows)


def feats(x, fs, fr, orders, max_hz=1000.):
    return np.column_stack([extract(x[:, a], fs, fr, orders, max_hz) for a in range(x.shape[1])])


@dataclass
class MachineFunnel:
    kinds: tuple
    mu: np.ndarray
    sd: np.ndarray
    multi: object
    ovr: dict
    tau: dict

    def z(self, f):
        return (f-self.mu)/self.sd

    def physics(self, z):
        """z từng loại: trung bình 3 hài bao hình, lấy trục mạnh hơn."""
        n_ax = z.shape[1]//N_COLS
        out = []
        for k in self.kinds:
            lo, hi = ENV[KEY[k]]
            out.append(np.max([z[:, lo+a*N_COLS:hi+a*N_COLS].mean(1) for a in range(n_ax)], axis=0))
        return np.column_stack(out)

    def scores(self, z):
        return np.column_stack([self.ovr[k].predict_proba(z)[:, 1] for k in self.kinds])

    def multi_prob(self, z):
        p = np.zeros((len(z), len(self.kinds)+1))
        p[:, self.multi.classes_] = self.multi.predict_proba(z)
        return p


def fit_funnel(base_x, fr, orders, sensor, fs, seed, kinds=('inner', 'outer'), n_inject=150, holdout=40, max_hz=1000., small=True, rng=None, prior=None):
    """Mỗi lớp một bộ một-chống-phần-còn-lại, ngưỡng hiệu chuẩn trên lỗi cấy giữ riêng."""
    rng = rng or np.random.default_rng(seed)
    f0 = feats(base_x, fs, fr, orders, max_hz)
    mu, sd = f0.mean(0), f0.std(0)+1e-9
    z0 = (f0-mu)/sd
    F, H = {}, {}
    for k in kinds:
        f = (feats(injected(base_x, k, n_inject+holdout, fr, orders, sensor, fs, rng, prior), fs, fr, orders, max_hz)-mu)/sd
        F[k], H[k] = f[:n_inject], f[n_inject:]
    cfg = SMALL if small else dict(n_estimators=200, max_features='sqrt', bootstrap=False, class_weight='balanced', n_jobs=1)
    X = np.concatenate([z0]+[F[k] for k in kinds])
    y = np.concatenate([np.zeros(len(z0), int)]+[np.full(n_inject, i+1) for i in range(len(kinds))])
    multi = RandomForestClassifier(random_state=seed, **cfg).fit(X, y)
    ovr, tau = {}, {}
    for i, k in enumerate(kinds):
        ovr[k] = RandomForestClassifier(random_state=seed, **cfg).fit(X, y == i+1)
        s = ovr[k].predict_proba(H[k])[:, 1]
        tau[k] = float(np.quantile(s, .1))  # 90% lỗi cấy giữ riêng được trả lời
    return MachineFunnel(kinds, mu, sd, multi, ovr, tau)


def decide(s, e, tau, margin=.1, phys=None):
    """Trả lớp (0 = chưa rõ, 1.. = theo kinds). tau: mảng ngưỡng; phys: z tối thiểu nếu cần vật lý đồng ý."""
    best = s.argmax(1)
    idx = np.arange(len(s))
    top = s[idx, best]
    sec = np.sort(s, axis=1)[:, -2] if s.shape[1] > 1 else np.zeros(len(s))
    ok = (top >= tau[best]) & (top-sec >= margin)
    if phys is not None:
        ok &= (e.argmax(1) == best) & (e[idx, best] >= phys)
    return np.where(ok, best+1, 0)
