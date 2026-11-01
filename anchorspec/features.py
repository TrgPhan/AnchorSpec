"""Đặc trưng một trục theo các góc nhìn của kế hoạch v1.4.

①biên độ ②phổ trong băng thông ③miền bậc ④bao hình theo băng kurtosis cao nhất
⑤thống kê xung. ⑥(xu hướng) và ⑦(giữa các trục) KHÔNG có ở đây: Paderborn và CWRU
chỉ có một trục dùng được, cửa sổ độc lập nên không có xu hướng.
Không có nhãn nào đi vào hàm: mọi bậc lỗi đều được tính cho mọi cửa sổ.
"""
import numpy as np
from scipy import signal, stats

N_BANDS = 10


def _harm(spec, freq, f0, tol, harmonics=3):
    """Năng lượng tại các hài so với nền trung vị; log để giảm đuôi."""
    floor = np.median(spec, axis=1)+1e-15
    return [np.log(np.maximum(spec[:, np.abs(freq-f0*h) <= tol].max(1), 1e-15)/floor) for h in range(1, harmonics+1)]


def extract(x, fs, fr, orders, max_hz=1000.):
    """x: (n cửa sổ, N mẫu), fr: Hz của bản ghi, max_hz: băng thông thực của cảm biến."""
    x = np.asarray(x, float)
    x = x-x.mean(1, keepdims=True)
    N = x.shape[1]
    rms = np.sqrt(np.mean(x**2, 1))+1e-15
    peak = np.max(np.abs(x), 1)
    # Không có RMS/đỉnh tuyệt đối: giữa các ổ bình thường RMS đã lệch ~3 lần do lắp đặt
    # (Paderborn K001-K004), lớn hơn tác động của lỗi mức 1, nên không chuyển giao được.
    amp = [peak/rms, stats.kurtosis(x, axis=1), stats.skew(x, axis=1), rms/(np.mean(np.abs(x), 1)+1e-15)]
    f, p = signal.welch(x, fs, nperseg=min(1024, N), axis=1)
    inband = f <= max_hz
    total = p[:, inband].sum(1)+1e-15
    edges = np.linspace(0, max_hz, N_BANDS+1)
    bands = [np.log(p[:, (f >= a) & (f < b)].sum(1)/total+1e-15) for a, b in zip(edges[:-1], edges[1:])]
    centroid = (p[:, inband]*f[inband]).sum(1)/total
    spread = np.sqrt((p[:, inband]*(f[inband]-centroid[:, None])**2).sum(1)/total)
    freq = np.fft.rfftfreq(N, 1/fs)
    win = signal.get_window('hann', N)
    spec = np.abs(np.fft.rfft(x*win, axis=1))**2
    tol = max(.02*fr*max(orders.values()), 2*freq[1])  # chịu được trượt ~2%
    targets = {'fr': 1., **orders}
    order_raw = [v for o in targets.values() for v in _harm(spec, freq, o*fr, tol)]
    # ④ Chọn băng theo kurtosis của chính tín hiệu (không nhãn), rồi lấy phổ bao hình.
    envs, kurts = [], []
    for lo, hi in ((10, max_hz), (10, .3*max_hz), (.3*max_hz, .6*max_hz), (.6*max_hz, max_hz)):
        y = signal.sosfiltfilt(signal.butter(4, (lo, hi), 'bandpass', fs=fs, output='sos'), x, axis=1)
        e = np.abs(signal.hilbert(y, axis=1))
        envs.append(e)
        kurts.append(stats.kurtosis(e, axis=1))
    kurts = np.array(kurts)
    best = np.argmax(kurts, axis=0)
    env = np.array(envs)[best, np.arange(len(x))]
    env_spec = np.abs(np.fft.rfft((env-env.mean(1, keepdims=True))*win, axis=1))**2
    order_env = [v for o in targets.values() for v in _harm(env_spec, freq, o*fr, tol)]
    env_stats = [best.astype(float), kurts.max(0)]
    # ⑤ Xung: đỉnh vượt 4 lần độ lệch tuyệt đối trung vị.
    mad = np.median(np.abs(x), 1)+1e-15
    count, cv, ratio = [], [], []
    bpfo_period = fs/(orders['bpfo']*fr)
    for row, m in zip(x, mad):
        peaks, _ = signal.find_peaks(np.abs(row), height=4*m, distance=max(1, int(.002*fs)))
        count.append(len(peaks)/(N/fs))
        if len(peaks) > 2:
            gaps = np.diff(peaks)
            cv.append(gaps.std()/gaps.mean())
            ratio.append(np.median(gaps)/bpfo_period)
        else:
            cv.append(0.)
            ratio.append(0.)
    out = np.column_stack(amp+bands+[centroid, spread]+order_raw+order_env+env_stats+[count, cv, ratio])
    if not np.isfinite(out).all():
        raise ValueError('Non-finite features')
    return out


class HealthyNorm:
    """Chuẩn hóa theo thống kê BÌNH THƯỜNG của từng máy (fit chỉ trên nền của máy đó)."""

    def fit(self, x):
        self.mu = x.mean(0)
        self.sd = x.std(0)+1e-9
        return self

    def __call__(self, x):
        return (x-self.mu)/self.sd
