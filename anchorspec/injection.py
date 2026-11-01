"""Công thức cấy lỗi: tạo thành phần lỗi vật lý rồi cộng vào nền bình thường THẬT.

Không dùng nhãn hoặc dữ liệu kiểm tra. Mỗi mẫu có sổ ghi tham số + hash nguồn.
outer/inner kiểm chứng được trên Paderborn. cage/foreign/lube CHƯA có dữ liệu thật
để kiểm chứng (Paderborn không có các nhãn đó): chỉ là công thức.
"""
from dataclasses import dataclass, field, asdict
import hashlib

import numpy as np

from cheap_sensor import fault_path, output_stage, resample

FS_SIM = 16000  # mô phỏng ở tần số cao hơn fs cảm biến rồi đi qua fault_path


@dataclass(frozen=True)
class Prior:
    """Khoảng tham số (log-đều cho biên độ). Mặc định: tiên nghiệm rộng, chưa hiệu chỉnh."""
    amp_rel: tuple = (.2, 3.)         # RMS thành phần lỗi / RMS nền, sau đường truyền
    fn_low_hz: tuple = (150., 950.)   # mode trong băng thông cảm biến
    fn_high_hz: tuple = (1500., 7000.)  # mode ngoài băng thông, chỉ rò xuống
    high_ratio: tuple = (0., 2.)      # biên độ mode cao/mode thấp
    zeta: tuple = (.02, .15)
    slip: tuple = (.01, .02)
    jitter: tuple = (.002, .02)       # lệch chuẩn thời điểm xung, theo tỉ lệ chu kỳ
    amp_scatter: tuple = (.1, .5)     # log-lệch chuẩn biên độ từng xung
    am_depth: tuple = (.3, 1.)        # điều biến vùng tải với vòng trong

    def as_dict(self):
        return asdict(self)


def _draw(rng, r, log=False):
    return float(np.exp(rng.uniform(np.log(r[0]), np.log(r[1]))) if log else rng.uniform(*r))


def _pulse(rng, prior, fs):
    fl, fh = _draw(rng, prior.fn_low_hz), _draw(rng, prior.fn_high_hz)
    zeta, ratio = _draw(rng, prior.zeta), _draw(rng, prior.high_ratio)
    t = np.arange(int(.03*fs))/fs
    h = (np.exp(-zeta*2*np.pi*fl*t)*np.sin(2*np.pi*fl*t)
         + ratio*np.exp(-zeta*2*np.pi*fh*t)*np.sin(2*np.pi*fh*t))
    return h, {'fn_low_hz': fl, 'fn_high_hz': fh, 'zeta': zeta, 'high_ratio': ratio}


def _train(times, amps, h, n):
    x = np.zeros(n)
    index = np.round(times).astype(int)
    keep = (index >= 0) & (index < n)
    np.add.at(x, index[keep], amps[keep])
    return np.convolve(x, h)[:n]


def component(kind, n, fs, fr, orders, prior, rng):
    """Thành phần lỗi chưa chuẩn hóa biên độ, độ dài n mẫu ở fs. Trả (x, tham số)."""
    h, meta = _pulse(rng, prior, fs)
    t0 = rng.uniform(0, 1)
    if kind in ('outer', 'inner'):
        slip = _draw(rng, prior.slip)
        rate = (orders['bpfo'] if kind == 'outer' else orders['bpfi'])*fr*(1-slip)
        count = int(n/fs*rate)+2
        jitter, scatter = _draw(rng, prior.jitter), _draw(rng, prior.amp_scatter)
        pos = (np.arange(count)+t0+rng.normal(0, jitter, count))/rate
        amps = rng.lognormal(0, scatter, count)
        meta |= {'slip': slip, 'rate_hz': rate, 'jitter': jitter, 'amp_scatter': scatter}
        if kind == 'inner':
            depth = _draw(rng, prior.am_depth)
            amps = amps*(1+depth*np.cos(2*np.pi*fr*pos+rng.uniform(0, 2*np.pi)))
            meta['am_depth'] = depth
        return _train(pos*fs, np.maximum(amps, 0), h, n), meta
    if kind == 'cage':  # vỡ vòng cách: xung không đều, điều biến ở FTF
        slip = _draw(rng, prior.slip)
        ftf = orders['ftf']*fr*(1-slip)
        rate = (orders['bpfo'])*fr*(1-slip)
        count = int(n/fs*rate)+2
        pos = (np.arange(count)+t0+rng.normal(0, .15, count))/rate
        amps = rng.lognormal(0, .5, count)*(1+np.cos(2*np.pi*ftf*pos))
        return _train(pos*fs, amps, h, n), meta | {'slip': slip, 'ftf_hz': ftf}
    if kind == 'foreign':  # dị vật: xung Poisson, biên độ ngẫu nhiên
        rate = rng.uniform(.5, 3.)*orders['bpfo']*fr
        pos = np.cumsum(rng.exponential(1/rate, int(n/fs*rate*2)+4))
        return _train(pos*fs, rng.lognormal(0, 1., len(pos)), h, n), meta | {'rate_hz': rate}
    if kind == 'lube':  # hết dầu: nhiễu băng rộng
        return rng.normal(0, 1, n), {'broadband': True}
    raise ValueError(f'Unknown fault kind {kind}')


def inject(background, kind, fr, orders, sensor, prior, rng, source_id=None):
    """Cộng lỗi vào nền đã số hóa bởi cảm biến; trả (mẫu, sổ ghi).

    Thành phần đi qua đường truyền + lọc cảm biến, KHÔNG thêm nhiễu lần hai, rồi qua
    lại tầng số hóa. amp_rel định nghĩa SAU bộ lọc nên có nghĩa trong băng thông thật.
    """
    bg = np.asarray(background, float)
    n_sim = int(np.ceil(len(bg)*FS_SIM/sensor.fs_out))+int(.05*FS_SIM)
    raw, meta = component(kind, n_sim, FS_SIM, fr, orders, prior, rng)
    x = fault_path(raw, FS_SIM, sensor)[-len(bg):]
    x = x-x.mean()
    power = np.sqrt(np.mean(x**2))
    if not np.isfinite(power) or power <= 0:
        raise ValueError('Fault component has no energy inside sensor band')
    amp = _draw(rng, prior.amp_rel, log=True)
    out = output_stage(bg+x/power*amp*np.sqrt(np.mean(bg**2)), sensor)
    return out, meta | {'kind': kind, 'amp_rel': amp, 'source_id': source_id,
        'sample_sha256': hashlib.sha256(out.astype(np.float32).tobytes()).hexdigest(),
        'background_sha256': hashlib.sha256(bg.astype(np.float32).tobytes()).hexdigest()}


def quality_gate(sample, background, sensor, max_rel=8., corr_max=.999):
    """Cổng chất lượng: hữu hạn, không bão hòa, có đổi so với nền, biên độ hợp lý."""
    if not np.isfinite(sample).all():
        return 'nonfinite'
    if sensor.range_g is not None and np.mean(np.abs(sample) >= sensor.range_g) > .001:
        return 'saturated'
    a, b = sample-sample.mean(), background-background.mean()
    if np.sqrt(np.mean(a**2)) > max_rel*np.sqrt(np.mean(b**2)):
        return 'too_large'
    if abs(np.dot(a, b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-15)) > corr_max:
        return 'near_copy'
    return None
