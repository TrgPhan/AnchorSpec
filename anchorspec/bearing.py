"""Hình học ổ bi và ước lượng tốc độ từ phổ rung (không dùng tachometer)."""
from dataclasses import dataclass
from math import cos, radians

import numpy as np
from scipy import signal


@dataclass(frozen=True)
class Bearing:
    n: int
    d: float
    D: float
    phi_deg: float = 0.

    @property
    def ratio(self):
        return self.d/self.D*cos(radians(self.phi_deg))

    def orders(self):
        """Bậc so với tốc độ trục fr: FTF, BPFO, BPFI (công thức trong handoff)."""
        return {'ftf': .5*(1-self.ratio), 'bpfo': self.n/2*(1-self.ratio), 'bpfi': self.n/2*(1+self.ratio)}


# Lessmeier et al. 2016, bảng factsheet: FAG 6203, 8 bi, d=6.75 mm, D=28.55 mm, góc 0.
PADERBORN_6203 = Bearing(8, 6.75, 28.55, 0.)
# Trang CWRU Bearing Data Center, SKF 6205-2RS drive end (in).
CWRU_6205 = Bearing(9, .3126, 1.537, 0.)


def estimate_rpm(x, fs, nominal_rpm, tol=.1, harmonics=3):
    """Tìm fr trong nominal±tol tối đa tổng biên độ phổ tại các hài của fr.

    CHƯA đạt trên Paderborn (sai số trung vị 2-5% ở K001-K003): đừng dùng cho miền bậc.
    """
    x = np.asarray(x, float)
    n = len(x)
    spec = np.abs(np.fft.rfft((x-x.mean())*signal.get_window('hann', n)))
    freq = np.fft.rfftfreq(n, 1/fs)
    fr0 = nominal_rpm/60
    cands = np.arange(fr0*(1-tol), fr0*(1+tol), .05)
    width = max(freq[1], .1)
    # Chuẩn hóa theo nền cục bộ để hài ở dải năng lượng lớn không lấn át.
    score = [sum(np.interp(c*h, freq, spec)/np.median(spec[(freq > c*h-5) & (freq < c*h+5)]+1e-15)
                 for h in range(1, harmonics+1)) for c in cands]
    return float(cands[int(np.argmax(score))]*60), float(width)
