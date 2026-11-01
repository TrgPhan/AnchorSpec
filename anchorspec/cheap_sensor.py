"""Mô phỏng cảm biến rung MEMS giá rẻ (giả định kiểu ADXL355, CHƯA xác nhận với DENSO).

Thứ tự mô phỏng theo vật lý: bão hòa ở đầu vào -> chống chồng phổ + hạ mẫu -> nhiễu
-> lọc băng thông (nhiễu cũng bị lọc) -> lượng tử hóa. Đơn vị vào/ra là g.
"""
from dataclasses import dataclass, asdict
from math import gcd

import numpy as np
from scipy import signal


@dataclass(frozen=True)
class CheapSensor:
    fs_out: int = 4000
    bw_hz: float | None = 1000.
    noise_ug_rthz: float = 25.   # ADXL355 ~25 ug/rtHz (theo handoff, datasheet)
    range_g: float | None = 8.
    bits: int | None = 20

    def as_dict(self):
        return asdict(self)


def resample(x, fs_in, fs_out):
    """Hạ mẫu có lọc chống chồng phổ (FIR của resample_poly)."""
    if fs_in == fs_out:
        return np.asarray(x, dtype=float)
    g = gcd(int(fs_in), int(fs_out))
    return signal.resample_poly(np.asarray(x, dtype=float), int(fs_out)//g, int(fs_in)//g, axis=-1)


def lowpass(x, fs, bw_hz):
    if bw_hz is None or bw_hz >= fs/2:
        return x
    return signal.sosfilt(signal.butter(4, bw_hz, fs=fs, output='sos'), x, axis=-1)


def output_stage(x, sensor):
    """Lượng tử hóa + cắt đỉnh đầu ra. Dùng lại khi cộng lỗi cấy vào nền đã số hóa."""
    if sensor.range_g is not None:
        x = np.clip(x, -sensor.range_g, sensor.range_g)
    if sensor.bits is not None:
        if sensor.range_g is None:
            raise ValueError('bits requires range_g')
        lsb = 2*sensor.range_g/2**sensor.bits
        x = np.round(x/lsb)*lsb
    return x


def simulate(x_g, fs_in, sensor, rng=None):
    """Toàn chuỗi cho tín hiệu thật. Hàm thuần: rng None chỉ hợp lệ khi không có nhiễu."""
    x = np.asarray(x_g, dtype=float)
    if not np.isfinite(x).all():
        raise ValueError('Non-finite input')
    if sensor.range_g is not None:
        x = np.clip(x, -sensor.range_g, sensor.range_g)
    x = resample(x, fs_in, sensor.fs_out)
    if sensor.noise_ug_rthz > 0:
        if rng is None:
            raise ValueError('rng required when noise is enabled')
        sigma = sensor.noise_ug_rthz*1e-6*np.sqrt(sensor.fs_out/2)
        x = x+rng.normal(0, sigma, x.shape)
    x = lowpass(x, sensor.fs_out, sensor.bw_hz)
    return output_stage(x, sensor)


def fault_path(x_g, fs_in, sensor):
    """Đường đi của riêng thành phần lỗi: hạ mẫu + lọc, KHÔNG thêm nhiễu lần hai
    (nền thật đã chứa nhiễu cảm biến)."""
    return lowpass(resample(x_g, fs_in, sensor.fs_out), sensor.fs_out, sensor.bw_hz)


def windows(x, n):
    """Cửa sổ không chồng lấn, trừ trung bình từng cửa sổ."""
    x = np.asarray(x, dtype=float)
    out = x[:len(x)//n*n].reshape(-1, n).copy()
    return out-out.mean(1, keepdims=True)
