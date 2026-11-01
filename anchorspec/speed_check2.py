"""Ước lượng tốc độ ở 900 rpm (N09_M07_F10), K001-K004; không dùng ổ hỏng."""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from cheap_sensor import CheapSensor, simulate  # noqa: E402

RAR = ROOT.parent/'data'/'paderborn'/'rar'
S = CheapSensor()


def scan(y, fr0, tol):
    n = len(y)
    sp = np.abs(np.fft.rfft((y-y.mean())*signal.get_window('hann', n)))
    f = np.fft.rfftfreq(n, 1/4000)
    c = np.arange(fr0*(1-tol), fr0*(1+tol), .02)
    sc = [sum(np.interp(v*h, f, sp)/np.median(sp[(f > v*h-5) & (f < v*h+5)]+1e-15) for h in (1, 2, 3)) for v in c]
    return c[int(np.argmax(sc))]


est, true = [], []
for code in ('K001', 'K002', 'K003', 'K004'):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([str(Path(sys.executable).parent/'bsdtar'), '-xf', str(RAR/f'{code}.rar'), '-C', d, f'{code}/N09_M07_F10_{code}_*.mat'], check=True)
        for i, p in enumerate(sorted(Path(d, code).glob('*.mat'))):
            m = loadmat(p, squeeze_me=True, struct_as_record=False)[p.stem]
            ch = {str(y.Name): y for y in m.Y}
            y = simulate(np.asarray(ch['vibration_1'].Data, float)/9.81, 64000, S, np.random.default_rng([i, 2]))
            true.append(float(np.mean(ch['speed'].Data))/60)
            est.append([(scan(y, 15., .03)), scan(y, 15.*1.02, .03)])
est, true = np.array(est), np.array(true)
print('toc do that trung binh Hz', round(true.mean(), 3), 'n', len(true))
for col, label in ((0, 'danh dinh dung'), (1, 'danh dinh lech +2%')):
    for K in (1, 5, 20):
        e = [abs(np.median(est[j:j+K, col])-true[j:j+K].mean())/true[j:j+K].mean()*100 for j in range(0, len(true)-K+1, K) if (j % 20)+K <= 20]
        print(label, f'K={K} n={len(e)} trung vi {np.median(e):.2f}% p90 {np.quantile(e, .9):.2f}% max {max(e):.2f}%')
